import pygame
import json
from typing import Dict, Any, List, Optional, Tuple

class RadioService:
    """
    บริการเปิดวิทยุออนไลน์ระหว่างไลฟ์สด และจัดการคิวเพลงตามคำขอ (!เพลง)
    """
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.stations: List[Dict[str, str]] = []
        self.current_idx = 0
        self.is_playing = False
        self.player = None
        self.volume_pct = 30
        
        # คิวคำขอเพลง: [{"id": int, "user": str, "song": str, "status": "pending" | "approved" | "rejected"}]
        self.song_requests: List[Dict[str, Any]] = []
        self.request_counter = 0
        
        self.load_stations()

    def load_stations(self):
        """โหลดรายการสถานีวิทยุจากไฟล์คอนฟิก"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            radio_config = config.get("Radio", {})
            self.stations = radio_config.get("stations", [
                {"name": "วิทยุไทยลูกทุ่ง", "url": "http://radio11.plathong.net:8896/;stream.mp3"},
                {"name": "วิทยุเพลงป็อป", "url": "https://coolism-web3rd.cdn.byteark.com/stream/1/"},
                {"name": "วิทยุสากลฮิต", "url": "https://fabulous.thailandstreaming.net/fabulous.mp3"}
            ])
            self.current_idx = radio_config.get("current_station_idx", 0)
        except Exception:
            self.stations = [
                {"name": "วิทยุไทยลูกทุ่ง", "url": "http://radio11.plathong.net:8896/;stream.mp3"},
                {"name": "วิทยุเพลงป็อป", "url": "https://coolism-web3rd.cdn.byteark.com/stream/1/"},
                {"name": "วิทยุสากลฮิต", "url": "https://fabulous.thailandstreaming.net/fabulous.mp3"}
            ]
            self.current_idx = 0

    def play_current_station(self) -> str:
        """เริ่มเล่นสถานีวิทยุปัจจุบัน"""
        if not self.stations:
            return "ไม่พบข้อมูลสถานีวิทยุในระบบ"
            
        station = self.stations[self.current_idx]
        try:
            import win32com.client
            if not self.player:
                self.player = win32com.client.Dispatch("WMPlayer.OCX")
            
            # โหลดระดับความดังมิกเซอร์แชนแนลเป็นค่าเริ่มต้นหากเท่ากับ 30
            if self.volume_pct == 30:
                try:
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    master_vol = config.get("SFX", {}).get("master_volume", 1.0)
                    mixer_cfg = config.get("Mixer", {})
                    active_profile = mixer_cfg.get("active_profile", "normal")
                    volumes = mixer_cfg.get("profiles", {}).get(active_profile, {})
                    self.volume_pct = int(volumes.get("music", 0.3) * master_vol * 100)
                except Exception:
                    pass
            
            self.player.settings.volume = max(0, min(100, self.volume_pct))
            self.player.URL = station["url"]
            self.player.controls.play()
            self.is_playing = True
            return f"กำลังเปิดวิทยุสถานี {station['name']}"
        except Exception as e:
            print(f"Radio streaming error: {e}")
            return f"ไม่สามารถเปิดวิทยุสถานี {station['name']} ได้ในขณะนี้"

    def stop_radio(self) -> str:
        """หยุดเล่นวิทยุ"""
        if self.is_playing:
            try:
                if self.player:
                    self.player.controls.stop()
            except Exception:
                pass
            self.is_playing = False
            return "หยุดการทำงานวิทยุออนไลน์แล้ว"
        return "วิทยุออนไลน์ไม่ได้เปิดอยู่"

    def set_volume(self, volume_pct: int):
        """ปรับความดังของวิทยุ (0-100)"""
        self.volume_pct = max(0, min(100, volume_pct))
        if self.player:
            try:
                self.player.settings.volume = self.volume_pct
            except Exception:
                pass

    def next_station(self) -> str:
        """สลับเป็นสถานีถัดไป"""
        if not self.stations:
            return "ไม่มีสถานีวิทยุในระบบ"
        
        self.current_idx = (self.current_idx + 1) % len(self.stations)
        
        # บันทึกลงคอนฟิก
        self._save_current_station_index()
        
        if self.is_playing:
            self.stop_radio()
            return self.play_current_station()
        else:
            return f"สลับสถานีเป็น {self.stations[self.current_idx]['name']}"

    def prev_station(self) -> str:
        """สลับเป็นสถานีก่อนหน้า"""
        if not self.stations:
            return "ไม่มีสถานีวิทยุในระบบ"
            
        self.current_idx = (self.current_idx - 1 + len(self.stations)) % len(self.stations)
        self._save_current_station_index()
        
        if self.is_playing:
            self.stop_radio()
            return self.play_current_station()
        else:
            return f"สลับสถานีเป็น {self.stations[self.current_idx]['name']}"

    def _save_current_station_index(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            if "Radio" not in config:
                config["Radio"] = {}
            config["Radio"]["current_station_idx"] = self.current_idx
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass

    # --- ระบบเพลงคำขอ (Song requests) ---
    def request_song(self, nickname: str, song_name: str) -> str:
        """ผู้ชมขอเพลงผ่านช่องแชท พิมพ์ !เพลง <ชื่อเพลง>"""
        self.request_counter += 1
        req = {
            "id": self.request_counter,
            "user": nickname,
            "song": song_name,
            "status": "pending"
        }
        self.song_requests.append(req)
        return f"บันทึกเพลง {song_name} ขอโดย {nickname} ลงคิวขอเพลงสำเร็จ (คิวที่ {self.request_counter})"

    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """ดึงรายการเพลงที่รอดำเนินการอนุมัติ"""
        return [r for r in self.song_requests if r["status"] == "pending"]

    def approve_request(self, request_id: int) -> Tuple[bool, str]:
        """สตรีมเมอร์อนุมัติเพลงตาม ID"""
        for req in self.song_requests:
            if req["id"] == request_id and req["status"] == "pending":
                req["status"] = "approved"
                return True, f"อนุมัติเพลง {req['song']} ที่ขอโดยคุณ {req['user']} เรียบร้อยแล้ว"
        return False, "ไม่พบคิวเพลงดังกล่าว หรือเพลงนี้ได้รับการอนุมัติไปแล้ว"

    def reject_request(self, request_id: int) -> Tuple[bool, str]:
        """สตรีมเมอร์ปฏิเสธเพลงตาม ID"""
        for req in self.song_requests:
            if req["id"] == request_id and req["status"] == "pending":
                req["status"] = "rejected"
                return True, f"ปฏิเสธคิวเพลง {req['song']} เรียบร้อยแล้ว"
        return False, "ไม่พบคิวเพลงดังกล่าว หรือเพลงนี้ได้รับการประมวลผลไปแล้ว"

    def clear_request_queue(self):
        """เคลียร์คิวเพลงคำขอทั้งหมด"""
        self.song_requests.clear()
        self.request_counter = 0
