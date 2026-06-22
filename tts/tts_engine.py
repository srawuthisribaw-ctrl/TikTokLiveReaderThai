import os
import sys
import ctypes
import winreg
import tempfile
import asyncio
import threading
import pythoncom
import win32com.client as win32com
from gtts import gTTS
import edge_tts
import pygame
from typing import List, Dict, Any, Tuple, Optional

# ค้นหาพาธของไฟล์ DLL สำหรับ NVDA
if getattr(sys, 'frozen', False):
    DLL_X64 = os.path.join(os.path.dirname(sys.executable), "_internal", "nvdaControllerClient_x64.dll")
    if not os.path.exists(DLL_X64):
        DLL_X64 = os.path.join(os.path.dirname(sys.executable), "nvdaControllerClient_x64.dll")
else:
    DLL_X64 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nvdaControllerClient_x64.dll")

class TTSEngine:
    """
    คลาสหลักในการจัดการระบบ Text-To-Speech (TTS) ทั้งหมด
    รองรับ NVDA, JAWS, SAPI5, OneCore, Google TTS และ Edge TTS
    พร้อมโหมดเสียงตลก (Funny XML Speech Styles)
    """
    def __init__(self):
        self.nvda = None
        self._init_nvda()
        self.jaws = None
        self._init_jaws()
        self.speaker = None
        self.edge_loop = None
        self.edge_thread = None
        self._init_edge_thread()
        self.muted = False

    def _init_nvda(self):
        """โหลดไลบรารี NVDA Controller DLL"""
        try:
            if os.path.exists(DLL_X64):
                self.nvda = ctypes.windll.LoadLibrary(DLL_X64)
            else:
                self.nvda = ctypes.windll.nvdaControllerClient64
        except Exception:
            try:
                self.nvda = ctypes.windll.nvdaControllerClient32
            except Exception:
                self.nvda = None

    def _init_jaws(self):
        """เชื่อมต่อคอมโพเนนต์ Freedom Scientific JAWS API"""
        try:
            pythoncom.CoInitialize()
            self.jaws = win32com.Dispatch("FreedomScientific.JawsApi")
        except Exception:
            self.jaws = None

    def _init_edge_thread(self):
        """สร้าง Thread สำหรับรัน Event Loop ของ Edge TTS"""
        def run_loop():
            self.edge_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.edge_loop)
            self.edge_loop.run_forever()

        self.edge_thread = threading.Thread(target=run_loop, daemon=True)
        self.edge_thread.start()

    def get_available_voices(self) -> List[Dict[str, Any]]:
        """ดึงรายการเสียงทั้งหมดในระบบ (แบ่งเป็น SAPI5, OneCore, Edge)"""
        voices = []

        # 1. ดึง SAPI5 Voices
        sapi_voices = self._list_registry_voices(r"SOFTWARE\Microsoft\Speech\Voices\Tokens")
        for v in sapi_voices:
            voices.append({"name": f"SAPI5: {v['name']}", "id": v["id"], "type": "sapi5"})

        # 2. ดึง OneCore Voices
        onecore_voices = self._list_registry_voices(r"SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens")
        for v in onecore_voices:
            voices.append({"name": f"OneCore: {v['name']}", "id": v["id"], "type": "onecore"})

        # 3. ดึงเสียงออนไลน์ (Edge TTS) ภาษาไทยเป็นหลัก
        voices.append({"name": "Edge: Premwadee (หญิง)", "id": "th-TH-PremwadeeNeural", "type": "edge"})
        voices.append({"name": "Edge: Niwat (ชาย)", "id": "th-TH-NiwatNeural", "type": "edge"})
        voices.append({"name": "Google Translate TTS (ไทย)", "id": "google_th", "type": "google"})

        return voices

    def _list_registry_voices(self, reg_path: str) -> List[Dict[str, str]]:
        voices = []
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
            for i in range(winreg.QueryInfoKey(key)[0]):
                sub_key_name = winreg.EnumKey(key, i)
                sub_key = winreg.OpenKey(key, sub_key_name)
                try:
                    desc, _ = winreg.QueryValueEx(sub_key, "")
                    token_id = f"HKEY_LOCAL_MACHINE\\{reg_path}\\{sub_key_name}"
                    voices.append({"name": desc, "id": token_id})
                except Exception:
                    pass
                winreg.CloseKey(sub_key)
            winreg.CloseKey(key)
        except Exception:
            pass
        return voices

    def wrap_sapi_xml(self, text: str, style: str) -> str:
        """ห่อหุ้มข้อความด้วย SAPI XML tags เพื่อจำลองรูปแบบเสียงพูดชนิดพิเศษ"""
        # ล้างสัญลักษณ์หลุดผังป้องกันการพังของ XML parser
        clean = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        if style == "robot":
            return f'<pitch middle="-10"><rate speed="-2">{clean}</rate></pitch>'
        elif style == "child":
            return f'<pitch middle="10"><rate speed="3">{clean}</rate></pitch>'
        elif style == "old":
            return f'<pitch middle="-5"><rate speed="-3">{clean}</rate></pitch>'
        elif style == "fast":
            return f'<rate speed="7">{clean}</rate>'
        elif style == "slow":
            return f'<rate speed="-6">{clean}</rate>'
        elif style == "funny":
            return f'<pitch middle="7"><rate speed="4">{clean}</rate></pitch>'
            
        return clean

    def get_edge_speed_and_voice(self, voice_id: str, speed: int, style: str) -> Tuple[str, str]:
        """ประมวลผลความเร็วและชนิดเสียงออนไลน์สำหรับ Edge TTS"""
        base_speed = speed
        if style == "child":
            base_speed += 3
            voice_id = "th-TH-PremwadeeNeural"
        elif style == "old":
            base_speed -= 3
            voice_id = "th-TH-NiwatNeural"
        elif style == "fast":
            base_speed += 5
        elif style == "slow":
            base_speed -= 5
        elif style == "funny":
            base_speed += 4
            voice_id = "th-TH-PremwadeeNeural"
            
        speed_percent = base_speed * 10
        speed_percent = max(-50, min(150, speed_percent))
        speed_str = f"{'+' if speed_percent >= 0 else ''}{speed_percent}%"
        return voice_id, speed_str

    def speak(self, text: str, mode: str, voice_id: str, speed: int, volume: float, funny_style: str = "normal"):
        """
        สั่งให้อ่านออกเสียงข้อความตามระบบที่ระบุ
        funny_style: 'normal', 'robot', 'child', 'old', 'fast', 'slow', 'funny'
        """
        self.muted = False
        if not text.strip():
            return

        # 1. โหมด NVDA
        if mode == "nvda":
            if self.nvda and self.nvda.nvdaController_testIfRunning() == 0:
                self.nvda.nvdaController_speakText(text)
            else:
                self._speak_sapi5(text, "", speed, volume, funny_style)

        # 2. โหมด JAWS
        elif mode == "jaws":
            if self.jaws:
                self.jaws.SayString(text, False)
            else:
                self._speak_sapi5(text, "", speed, volume, funny_style)

        # 3. โหมด SAPI5 และ Windows OneCore
        elif mode in ("sapi5", "onecore"):
            self._speak_sapi5(text, voice_id, speed, volume, funny_style)

        # 4. โหมด Google TTS (ปรับความเร็วช้าผ่านสไตล์ตลก)
        elif mode == "google":
            self._speak_google(text, volume, funny_style)

        # 5. โหมด Edge TTS
        elif mode == "edge":
            self._speak_edge(text, voice_id, speed, volume, funny_style)

    def stop(self, mode: str):
        """หยุดการพูดปัจจุบันของระบบเสียง"""
        if mode == "nvda" and self.nvda:
            try:
                self.nvda.nvdaController_cancelSpeech()
            except Exception:
                pass
        elif mode == "jaws" and self.jaws:
            try:
                self.jaws.RunFunction("StopSpeech")
            except Exception:
                pass
        elif mode in ("sapi5", "onecore") and self.speaker:
            try:
                self.speaker.Speak("", 2)
            except Exception:
                pass
        elif mode in ("google", "edge"):
            try:
                pygame.mixer.stop()  # หยุดเฉพาะเสียงพูด ไม่หยุดเสียงดนตรีหลัก
            except Exception:
                pass

    def _speak_sapi5(self, text: str, voice_id: str, speed: int, volume: float, funny_style: str):
        pythoncom.CoInitialize()
        try:
            if self.speaker is None:
                self.speaker = win32com.Dispatch("SAPI.SpVoice")
            
            if voice_id and voice_id.startswith("HKEY_"):
                try:
                    token = win32com.Dispatch("SAPI.SpObjectToken")
                    sapi_voice_id = voice_id.replace("Speech_OneCore", "Speech")
                    token.SetId(sapi_voice_id)
                    self.speaker.Voice = token
                except Exception as e:
                    print(f"Error setting voice token: {e}")
            
            # ปรับแต่งความเร็วตามสไตล์ตลกเพิ่มเติมสำหรับเสียงระบบ (เช่น OneCore ที่ไม่รองรับ XML Pitch)
            adjusted_speed = speed
            if funny_style == "robot":
                adjusted_speed -= 2
            elif funny_style == "child":
                adjusted_speed += 3
            elif funny_style == "old":
                adjusted_speed -= 3
            elif funny_style == "fast":
                adjusted_speed += 5
            elif funny_style == "slow":
                adjusted_speed -= 5
            elif funny_style == "funny":
                adjusted_speed += 4

            # ปรับแต่งความเร็วและความดังพื้นฐาน
            self.speaker.Rate = max(-10, min(10, adjusted_speed))
            self.speaker.Volume = int(max(0.0, min(1.0, volume)) * 100)
            
            # ห่อหุ้ม XML ข้อความกรณีเลือกรูปแบบตลก (สำหรับ SAPI5 ดั้งเดิมที่รองรับ XML Pitch)
            processed_text = self.wrap_sapi_xml(text, funny_style)
            
            # สั่ง Speak (ใช้ Flag 9 เพื่อเปิดใช้งาน XML และรันแบบ Asynchronous)
            # SVSFlagsAsync = 1, SVSFIsXML = 8
            self.speaker.Speak(processed_text, 9)
            
            # วนลูปตรวจสอบสถานะการพูด โดยสามารถสั่งหยุดได้ทันทีเมื่อมีการกดคีย์ลัด Mute
            while not self.speaker.WaitUntilDone(50):
                if getattr(self, "muted", False):
                    self.speaker.Speak("", 2)  # SVSFPurgeBeforeSpeak = 2
                    break
        except Exception as e:
            print(f"SAPI5 Error: {e}")
            self.speaker = None

    def _speak_google(self, text: str, volume: float, funny_style: str = "normal"):
        temp_path = None
        try:
            # ปรับความเร็วช้าจำลองสำหรับ Google TTS
            is_slow = funny_style in ("slow", "robot", "old")
            tts = gTTS(text, lang="th", slow=is_slow)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_path = fp.name
            
            tts.save(temp_path)
            self._play_file_and_wait(temp_path, volume)
        except Exception as e:
            print(f"Google TTS Error: {e}")
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def _speak_edge(self, text: str, voice_id: str, speed: int, volume: float, funny_style: str):
        if not voice_id or not voice_id.startswith("th-TH"):
            voice_id = "th-TH-PremwadeeNeural"
        
        # ดึงเสียงและความเร็วที่ผ่านการปรับแต่งจาก funny_style
        target_voice, rate_str = self.get_edge_speed_and_voice(voice_id, speed, funny_style)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_path = fp.name

        async def run_edge():
            communicate = edge_tts.Communicate(text, target_voice, rate=rate_str)
            await communicate.save(temp_path)

        future = asyncio.run_coroutine_threadsafe(run_edge(), self.edge_loop)
        try:
            future.result(timeout=8.0)
            self._play_file_and_wait(temp_path, volume)
        except Exception as e:
            print(f"Edge TTS future error: {e}")
        finally:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass

    def _play_file_and_wait(self, filepath: str, volume: float):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            
            try:
                # Try playing using Sound object (allows concurrent play with background music)
                sound = pygame.mixer.Sound(filepath)
                sound.set_volume(max(0.0, min(1.0, volume)))
                channel = sound.play()
                while channel and channel.get_busy():
                    if getattr(self, "muted", False):
                        pygame.mixer.stop()
                        break
                    pygame.time.wait(50)
                del sound
            except Exception as sound_err:
                print(f"Sound playback fallback to music due to error: {sound_err}")
                # Fallback to legacy music player if Sound fails
                pygame.mixer.music.load(filepath)
                pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    if getattr(self, "muted", False):
                        pygame.mixer.music.stop()
                        break
                    pygame.time.wait(50)
                pygame.mixer.music.unload()
        except Exception as e:
            print(f"Pygame Audio Play Error: {e}")

    def check_thai_offline_status(self) -> str:
        """ตรวจสอบสถานะของเสียงภาษาไทยแบบออฟไลน์ (Microsoft Pattara) ในระบบ"""
        sapi_voices = self._list_registry_voices(r"SOFTWARE\Microsoft\Speech\Voices\Tokens")
        has_sapi_thai = any("thTH" in v["id"] or "Pattara" in v["name"] for v in sapi_voices)
        if has_sapi_thai:
            return "ok"

        onecore_voices = self._list_registry_voices(r"SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens")
        has_onecore_thai = any("thTH" in v["id"] or "Pattara" in v["name"] for v in onecore_voices)
        if has_onecore_thai:
            return "can_install"

        return "not_supported"

    def install_thai_offline(self) -> bool:
        """คัดลอกเสียงภาษาไทยจาก Speech_OneCore ไปยัง SAPI5 (ต้องใช้สิทธิ์แอดมิน)"""
        import subprocess
        cmd = "reg copy HKLM\\SOFTWARE\\Microsoft\\Speech_OneCore\\Voices\\Tokens HKLM\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens /s /f"
        # Check if the system is 64-bit (has SysWOW64 directory)
        sys_root = os.environ.get("SystemRoot", "C:\\Windows")
        if os.path.exists(os.path.join(sys_root, "SysWOW64")):
            cmd += " & reg copy HKLM\\SOFTWARE\\Microsoft\\Speech_OneCore\\Voices\\Tokens HKLM\\SOFTWARE\\Wow6432Node\\Microsoft\\Speech\\Voices\\Tokens /s /f"
        
        full_cmd = f"Start-Process cmd -ArgumentList '/c {cmd}' -Verb RunAs -Wait"
        try:
            subprocess.run(["powershell", "-Command", full_cmd], check=True)
            return True
        except Exception as e:
            print(f"Error copying registry: {e}")
            return False

