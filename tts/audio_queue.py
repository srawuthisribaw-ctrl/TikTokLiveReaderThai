import queue
import time
import threading
import pygame
import os
import json
from typing import Optional, Dict, Any
from tts.tts_engine import TTSEngine

import sys

# โฟลเดอร์เก็บไฟล์เสียงประกอบ
if getattr(sys, 'frozen', False):
    SOUNDS_DIR = os.path.join(os.path.dirname(sys.executable), "_internal", "sounds")
    if not os.path.exists(SOUNDS_DIR):
        SOUNDS_DIR = os.path.join(os.path.dirname(sys.executable), "sounds")
else:
    SOUNDS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sounds")

class AudioQueue:
    """
    คลาสสำหรับจัดการคิวเสียงและความสำคัญของแต่ละเหตุการณ์ (Priority Queue)
    ระบบเครื่องเล่นเสียงได้รับการปรับปรุงให้รองรับระดับความดังมิกเซอร์แยกช่อง (Mixer volume)
    และระบบเสียงตลก (Funny TTS)
    """
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.queue = queue.PriorityQueue()
        self.tts = TTSEngine()
        self.sfx_cache: Dict[str, pygame.mixer.Sound] = {}
        self.master_volume = 1.0
        self.tts_volume = 1.0
        self.mixer_volumes = {
            "music": 0.3,
            "comment": 1.0,
            "gift": 1.0,
            "sfx": 0.8,
            "tts": 1.0,
            "ai": 0.9
        }
        self.muted = False
        
        self._load_config_settings()
        self._init_sfx()
        
        # เริ่มเธรดวนลูปคิว
        self.worker_thread = threading.Thread(target=self._queue_worker, daemon=True)
        self.worker_thread.start()

    def _load_config_settings(self):
        """โหลดข้อมูลมิกเซอร์เสียงและการตั้งค่าความดังจากไฟล์คอนฟิก"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            self.master_volume = config.get("SFX", {}).get("master_volume", 1.0)
            self.tts_volume = config.get("TTS", {}).get("volume", 1.0)
            
            # โหลดโปรไฟล์มิกเซอร์เสียง
            mixer_cfg = config.get("Mixer", {})
            active_profile = mixer_cfg.get("active_profile", "normal")
            self.mixer_volumes = mixer_cfg.get("profiles", {}).get(active_profile, {
                "music": 0.3,
                "comment": 1.0,
                "gift": 1.0,
                "sfx": 0.8,
                "tts": 1.0,
                "ai": 0.9
            })
        except Exception:
            self.master_volume = 1.0
            self.tts_volume = 1.0

    def _init_sfx(self):
        """โหลดและเตรียมพร้อมไฟล์เสียงประกอบ (SFX) ทั้งหมด"""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.set_num_channels(32)
        except Exception as e:
            print(f"Failed to initialize pygame mixer: {e}")
            return

        defaults = {
            "sfx_join": "welcome.wav",
            "sfx_gift": "gift.wav",
            "sfx_comment": "comment.wav",
            "sfx_like": "like.wav",
            "sfx_share": "share.wav",
            "sfx_update": "update.wav"
        }

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            sfx_config = config.get("SFX", {})
        except Exception:
            sfx_config = {}

        for key, default_name in defaults.items():
            fname = sfx_config.get(key, default_name)
            path = os.path.join(SOUNDS_DIR, fname)
            if not os.path.exists(path):
                path = os.path.join(SOUNDS_DIR, default_name)
            
            if os.path.exists(path):
                try:
                    self.sfx_cache[key] = pygame.mixer.Sound(path)
                except Exception as e:
                    print(f"Error loading SFX {key}: {e}")

    def add_to_queue(self, text: str, level: int = 5, sfx_key: Optional[str] = None, channel: str = "tts"):
        """
        เพิ่มข้อความและระดับความสำคัญลงในคิวเสียง
        channel: 'comment', 'gift', 'sfx', 'tts', 'ai' สำหรับมิกเซอร์เสียง
        """
        priority = 100 - level
        timestamp = time.time()
        self.queue.put((priority, timestamp, text, sfx_key, channel))

    def play_sfx(self, sfx_key: str):
        """เล่นเสียงเอฟเฟกต์ตามคีย์ที่ระบุ โดยใช้ความดังมิกเซอร์ของช่อง sfx"""
        if sfx_key in self.sfx_cache:
            try:
                sound = self.sfx_cache[sfx_key]
                sfx_vol = self.mixer_volumes.get("sfx", 0.8)
                # ความดังรวม = Master Volume * ช่องเอฟเฟกต์
                sound.set_volume(0.5 * self.master_volume * sfx_vol)
                sound.play()
            except Exception as e:
                print(f"Error playing SFX: {e}")

    def mute(self):
        """เงียบเสียงพูดและเคลียร์คิวเสียงสะสมทั้งหมด"""
        self.muted = True
        self.tts.muted = True
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            mode = config.get("TTS", {}).get("mode", "nvda")
            self.tts.stop(mode)
        except Exception:
            pass
        self.muted = False

    def reload_settings(self):
        """โหลดการตั้งค่าเสียงและระดับความดังใหม่"""
        self._load_config_settings()
        self._init_sfx()

    def _queue_worker(self):
        import pythoncom
        pythoncom.CoInitialize()

        while True:
            try:
                # ดึงงานออกจากคิว
                priority, timestamp, text, sfx_key, channel = self.queue.get()
                
                if self.muted:
                    self.queue.task_done()
                    continue
                
                # 1. เล่นเสียงประกอบ (SFX)
                if sfx_key:
                    self.play_sfx(sfx_key)
                    time.sleep(0.15)
                
                # 2. โหลดคอนฟิกเพื่อแปรค่าการปรับระดับเสียงมิกเซอร์สด
                try:
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    tts_config = config.get("TTS", {})
                    mode = tts_config.get("mode", "nvda")
                    voice_id = tts_config.get("voice_id", "")
                    speed = tts_config.get("speed", 0)
                    global_tts_volume = tts_config.get("volume", 1.0)
                    funny_style = tts_config.get("funny_style", "normal")
                    
                    # หามิกเซอร์ของช่องปัจจุบัน
                    mixer_cfg = config.get("Mixer", {})
                    active_profile = mixer_cfg.get("active_profile", "normal")
                    volumes = mixer_cfg.get("profiles", {}).get(active_profile, {})
                    channel_vol = volumes.get(channel, 1.0)
                    master_vol = config.get("SFX", {}).get("master_volume", 1.0)
                except Exception:
                    mode = "nvda"
                    voice_id = ""
                    speed = 0
                    global_tts_volume = 1.0
                    channel_vol = 1.0
                    master_vol = 1.0
                    funny_style = "normal"

                # ระดับเสียงคำนวณ = ระดับเสียงของตัวอ่าน * มิกเซอร์ระดับช่องเสียง * ระดับเสียงหลัก
                calculated_volume = global_tts_volume * channel_vol * master_vol

                # 3. สั่งพูดผ่านเอนจิน TTS
                if not self.muted:
                    self.tts.speak(text, mode, voice_id, speed, calculated_volume, funny_style)
                
                self.queue.task_done()
            except Exception as e:
                print(f"Audio queue worker error: {e}")
                time.sleep(0.1)
