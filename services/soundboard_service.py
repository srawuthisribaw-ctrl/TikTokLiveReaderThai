import os
import wave
import math
import struct
import random
import json
import pygame
from typing import Dict, Any, List, Optional
import sys

if getattr(sys, 'frozen', False):
    SOUNDS_DIR = os.path.join(os.path.dirname(sys.executable), "sounds")
else:
    SOUNDS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sounds")

class SoundboardService:
    """
    บริการจัดการ Soundboard เอฟเฟกต์เสียงตลก ระบบเสียงแจ้งเตือนอัตโนมัติ
    และระบบข้อความเสียงตลกจำลองสำหรับช่องแชท
    """
    def __init__(self, config_path: str, speak_fn: Any):
        self.config_path = config_path
        self.speak_fn = speak_fn
        self.sfx_cache: Dict[str, pygame.mixer.Sound] = {}
        
        self.sound_mappings = {
            "laugh": "laugh.wav",
            "rimshot": "rimshot.wav",
            "drumroll": "drumroll.wav",
            "applause": "applause.wav",
            "cheer": "cheer.wav",
            "wow": "wow.wav",
            "shock": "shock.wav",
            "cat": "cat.wav",
            "dog": "dog.wav",
            "rooster": "rooster.wav",
            "duck": "duck.wav",
            "gameshow": "gameshow.wav",
            "win": "win.wav",
            "lose": "lose.wav",
            "explosion": "explosion.wav",
            "slide": "slide.wav",
            "baby_laugh": "baby_laugh.wav",
            "cheer2": "cheer2.wav"
        }
        
        self.ensure_sound_files_exist()
        self.load_soundboard_cache()

    def ensure_sound_files_exist(self):
        """ตรวจสอบและสร้างไฟล์เสียงแจ้งเตือนสังเคราะห์ (.wav) หากไม่มีอยู่ในโฟลเดอร์ sounds"""
        if not os.path.exists(SOUNDS_DIR):
            os.makedirs(SOUNDS_DIR)

        # ผลิตบี๊บสังเคราะห์แตกต่างกันสำหรับความบันเทิงแต่ละปุ่ม
        frequencies = {
            "laugh": [440, 550, 660],
            "rimshot": [800, 200],
            "drumroll": [150, 160, 150],
            "applause": [600, 700, 800, 900],
            "cheer": [500, 600, 700],
            "wow": [400, 800],
            "shock": [900, 100],
            "cat": [700, 800],
            "dog": [200, 150],
            "rooster": [600, 900, 700],
            "duck": [300, 310],
            "gameshow": [500, 600, 500],
            "win": [523, 659, 784, 1046],
            "lose": [392, 349, 311, 261],
            "explosion": [100, 80, 50],
            "slide": [300, 600, 300],
            "baby_laugh": [800, 1000],
            "cheer2": [440, 880]
        }

        for key, fname in self.sound_mappings.items():
            path = os.path.join(SOUNDS_DIR, fname)
            if not os.path.exists(path):
                freqs = frequencies.get(key, [440])
                self.generate_synthesized_wav(path, freqs)

    def generate_synthesized_wav(self, path: str, frequencies: List[int]):
        """สร้างไฟล์เสียง .wav พื้นฐานอย่างรวดเร็วเพื่อกันความผิดพลาด File Not Found"""
        try:
            with wave.open(path, 'w') as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(44100)
                
                data = []
                # วนเล่นคลื่นเสียงตามระดับความถี่พารามิเตอร์
                samples_per_freq = 3000
                for freq in frequencies:
                    for i in range(samples_per_freq):
                        # สร้างคลื่นไซน์ (Sine wave)
                        value = int(32767.0 * math.sin(2.0 * math.pi * freq * i / 44100.0))
                        data.append(struct.pack('<h', value))
                        
                f.writeframes(b''.join(data))
        except Exception as e:
            print(f"Error generating WAV {path}: {e}")

    def load_soundboard_cache(self):
        """โหลดไฟล์เสียงขึ้นสู่แคชของ pygame"""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except:
            return

        for key, fname in self.sound_mappings.items():
            path = os.path.join(SOUNDS_DIR, fname)
            if os.path.exists(path):
                try:
                    self.sfx_cache[key] = pygame.mixer.Sound(path)
                except Exception as e:
                    print(f"Error loading soundboard sound {key}: {e}")

    def play_sound(self, key: str):
        """สั่งเล่นเสียงตามคีย์เอฟเฟกต์"""
        if key in self.sfx_cache:
            try:
                # โหลดระดับความดังมิกเซอร์แชนแนลเอฟเฟกต์
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                master_vol = config.get("SFX", {}).get("master_volume", 1.0)
                
                mixer_cfg = config.get("Mixer", {})
                active_profile = mixer_cfg.get("active_profile", "normal")
                volumes = mixer_cfg.get("profiles", {}).get(active_profile, {})
                sfx_channel_vol = volumes.get("sfx", 0.8)
                
                sound = self.sfx_cache[key]
                # ตั้งความดังสุทธิ
                sound.set_volume(0.5 * master_vol * sfx_channel_vol)
                sound.play()
            except Exception as e:
                print(f"Error playing soundboard sfx: {e}")

    def play_random_effect(self):
        """สุ่มเล่นหนึ่งในเสียงเอฟเฟกต์ในซาวด์บอร์ดเพื่อความตลก"""
        keys = list(self.sound_mappings.keys())
        chosen = random.choice(keys)
        self.play_sound(chosen)

    # --- ระบบเสียงตอบกลับอัตโนมัติตามกิจกรรม ---
    def trigger_event_effect(self, event_type: str, nickname: str = "ผู้ชม"):
        """
        เล่นเสียงประกอบและประกาศคำพูดตลกอัตโนมัติเมื่อผู้ชมทำกิจกรรมสำเร็จ
        event_type: 'new_follower', 'gift', 'large_gift', 'level_up', 'win_game'
        """
        if event_type == "new_follower":
            # เล่นเอฟเฟกต์เชียร์
            self.play_sound("cheer")
            self.speak_fn(f"เย้ มีผู้ติดตามใหม่! ขอบคุณคุณ {nickname} ที่กดติดตามช่องนะคะ", 8)
            
        elif event_type == "gift":
            self.play_sound("wow")
            self.speak_fn(f"ขอบคุณสำหรับของขวัญนะคะคุณ {nickname} ขอให้เฮงเฮงรวยรวยค่ะ", 10)
            
        elif event_type == "large_gift":
            self.play_sound("cheer2")
            self.speak_fn(f"ว้าว! คุณได้รับของขวัญมูลค่าสูงจากคุณ {nickname}! ปรบมือฉลองเจ้าสัวใหญ่สตรีมเรากันหน่อยค่ะ", 10)
            self.play_sound("applause")
            
        elif event_type == "level_up":
            self.play_sound("win")
            
        elif event_type == "win_game":
            self.play_sound("gameshow")

    # --- ฟังก์ชันรายงานเสียงตลกอัตโนมัติ (Auto announcements) ---
    def get_random_funny_announcement(self) -> str:
        """ดึงข้อความตลกอัตโนมัติแบบสุ่มจากคอนฟิก"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            messages = config.get("AutoAnnouncements", {}).get("messages", [
                "ยินดีต้อนรับสมาชิกใหม่ครับ",
                "เข้ามาแล้วอย่าลืมกดไลก์นะครับ",
                "วันนี้เจ้าของไลฟ์อารมณ์ดีเป็นพิเศษ",
                "ใครกดแชร์ขอให้โชคดีทั้งวัน"
            ])
            return random.choice(messages)
        except Exception:
            return "ยินดีต้อนรับทุกท่านเข้ารับชมไลฟ์สดค่ะ"
