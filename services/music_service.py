import os
import random
import json
import pygame
from typing import Dict, Any, List, Optional, Tuple
import sys

if getattr(sys, 'frozen', False):
    PLAYLISTS_DIR = os.path.join(os.path.dirname(sys.executable), "playlists")
else:
    PLAYLISTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "playlists")

class MusicService:
    """
    บริการเครื่องเล่นเพลงของผู้จัดไลฟ์ (Streamer Music Player) และจัดคิวคำขอเพลงจากผู้ชม
    รองรับการจัดการเพลย์ลิสต์ คิวจองเพลง และการควบคุมระดับเสียงแยกช่อง
    """
    def __init__(self, config_path: str, speak_fn: Any):
        self.config_path = config_path
        self.speak_fn = speak_fn
        
        self.current_playlist_name = "เพลงสำหรับไลฟ์"
        self.playlists: Dict[str, List[str]] = {} # {"ชื่อเพลย์ลิสต์": ["พาธไฟล์1", "พาธไฟล์2"]}
        self.current_song_idx = 0
        self.is_playing = False
        self.is_paused = False
        self.shuffle = False
        self.repeat_mode = "none" # "none" | "one" | "all"
        self.channel_volume = 0.3
        self.music_volume = 0.3
        
        # คิวคำขอเพลงของผู้ชม
        self.request_queue: List[Dict[str, Any]] = []
        self.request_counter = 0

        self.ensure_directories()
        self.load_all_playlists()
        self._load_mixer_volume()

    def ensure_directories(self):
        if not os.path.exists(PLAYLISTS_DIR):
            os.makedirs(PLAYLISTS_DIR)

    def _load_mixer_volume(self):
        """โหลดระดับความดังของเพลงจากมิกเซอร์โปรไฟล์"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            master_vol = config.get("SFX", {}).get("master_volume", 1.0)
            mixer_cfg = config.get("Mixer", {})
            active_profile = mixer_cfg.get("active_profile", "normal")
            volumes = mixer_cfg.get("profiles", {}).get(active_profile, {})
            self.channel_volume = volumes.get("music", 0.3)
            self.music_volume = self.channel_volume * master_vol
        except Exception:
            self.channel_volume = 0.3
            self.music_volume = 0.3

    def load_all_playlists(self):
        """โหลดไฟล์เพลย์ลิสต์ทั้งหมด หรือสร้างค่าเริ่มต้นขึ้นมา"""
        # สร้างพรีเซ็ตเพลย์ลิสต์เริ่มต้น
        presets = {
            "เพลงลูกทุ่ง": [],
            "เพลงสตริง": [],
            "เพลงแดนซ์": [],
            "เพลงสำหรับไลฟ์": []
        }
        
        # ตรวจสอบเพลย์ลิสต์ในเครื่อง
        has_playlists = False
        for fname in os.listdir(PLAYLISTS_DIR):
            if fname.endswith(".json"):
                name = fname[:-5]
                path = os.path.join(PLAYLISTS_DIR, fname)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self.playlists[name] = json.load(f)
                        has_playlists = True
                except Exception:
                    pass

        # หากไม่มี ให้ดึงจากพรีเซ็ต
        if not has_playlists:
            self.playlists = presets
            self.save_all_playlists()

    def save_all_playlists(self):
        """บันทึกเพลย์ลิสต์ทั้งหมดลงโฟลเดอร์เพลย์ลิสต์"""
        for name, tracks in self.playlists.items():
            path = os.path.join(PLAYLISTS_DIR, f"{name}.json")
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(tracks, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Error saving playlist {name}: {e}")

    # --- ฟังก์ชันควบคุมสิทธิ์เครื่องเล่น ---
    def play_song(self) -> str:
        """เริ่มเล่นเพลง ณ ดัชนีปัจจุบัน"""
        tracks = self.playlists.get(self.current_playlist_name, [])
        if not tracks:
            msg = f"ไม่พบไฟล์เพลงในเพลย์ลิสต์ {self.current_playlist_name} กรุณาเพิ่มเพลงก่อนค่ะ"
            self.speak_fn(msg, 8)
            return msg

        if self.current_song_idx >= len(tracks):
            self.current_song_idx = 0

        song_path = tracks[self.current_song_idx]
        song_name = os.path.basename(song_path)
        
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            # สั่งรีโหลดระดับความดังมิกเซอร์แชนแนล
            self._load_mixer_volume()
            
            # โหลดเพลงเข้าคิว
            pygame.mixer.music.load(song_path)
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play()
            
            self.is_playing = True
            self.is_paused = False
            
            # สั่ง TTS อ่านชื่อเพลง
            announce_text = f"กำลังเล่นเพลง {song_name[:-4] if '.' in song_name else song_name} หมายเลข {self.current_song_idx + 1}"
            self.speak_fn(announce_text, 8)
            return announce_text
        except Exception as e:
            msg = f"ไม่สามารถเล่นไฟล์ {song_name} ได้ในขณะนี้เนื่องจากปัญหาตัวถอดรหัส"
            self.speak_fn(msg, 8)
            return msg

    def pause_or_resume(self) -> str:
        """หยุดเพลงชั่วคราวหรือเล่นต่อ"""
        if not self.is_playing:
            return self.play_song()

        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.speak_fn("เล่นเพลงต่อค่ะ", 5)
            return "เล่นเพลงต่อ"
        else:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.speak_fn("หยุดเพลงชั่วคราวค่ะ", 5)
            return "หยุดเพลงชั่วคราว"

    def stop_music(self):
        """หยุดและเคลียร์การเล่นเพลงหลัก"""
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        except Exception:
            pass
        self.is_playing = False
        self.is_paused = False
        self.speak_fn("ปิดระบบเครื่องเล่นเพลงแล้วค่ะ", 5)

    def next_track(self) -> str:
        """ข้ามเพลงไปเพลงถัดไป"""
        tracks = self.playlists.get(self.current_playlist_name, [])
        if not tracks:
            return "ไม่มีเพลงในเพลย์ลิสต์"

        if self.shuffle:
            self.current_song_idx = random.randint(0, len(tracks) - 1)
        else:
            self.current_song_idx = (self.current_song_idx + 1) % len(tracks)

        return self.play_song()

    def prev_track(self) -> str:
        """ย้อนกลับไปเพลงก่อนหน้า"""
        tracks = self.playlists.get(self.current_playlist_name, [])
        if not tracks:
            return "ไม่มีเพลงในเพลย์ลิสต์"

        self.current_song_idx = (self.current_song_idx - 1 + len(tracks)) % len(tracks)
        return self.play_song()

    def set_volume(self, volume: float):
        """ปรับความดังเพลงโดยตรง และบันทึกค่าลง config.json เพื่อให้คงอยู่ถาวร"""
        self.channel_volume = max(0.0, min(1.0, volume))
        
        # โหลดระดับเสียงหลักล่าสุดเพื่อคูณเป็นระดับเสียงจริงที่จะตั้งให้ Pygame
        master_vol = 1.0
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            master_vol = config.get("SFX", {}).get("master_volume", 1.0)
        except Exception:
            pass
            
        self.music_volume = self.channel_volume * master_vol
        
        if self.is_playing:
            try:
                pygame.mixer.music.set_volume(self.music_volume)
            except Exception:
                pass
                
        # บันทึกค่าระดับความดังลงไฟล์คอนฟิกตามโปรไฟล์มิกเซอร์ที่ใช้งานอยู่
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            mixer_cfg = config.get("Mixer", {})
            active_profile = mixer_cfg.get("active_profile", "normal")
            if "profiles" in mixer_cfg and active_profile in mixer_cfg["profiles"]:
                mixer_cfg["profiles"][active_profile]["music"] = self.channel_volume
                
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving music volume to config: {e}")


    def check_music_tick(self):
        """คอยตรวจความยาวเพลงเพื่อสลับเพลงถัดไปเมื่อจบลงอัตโนมัติ (ขยายผ่าน Window ticker)"""
        if self.is_playing and not self.is_paused:
            try:
                if not pygame.mixer.music.get_busy():
                    # ตรวจคิวเล่นซ้ำ
                    if self.repeat_mode == "one":
                        self.play_song()
                    else:
                        self.next_track()
            except Exception:
                pass

    # --- ฟังก์ชันจัดการเพลย์ลิสต์ ---
    def create_playlist(self, name: str) -> bool:
        if name in self.playlists:
            return False
        self.playlists[name] = []
        self.save_all_playlists()
        return True

    def delete_playlist(self, name: str) -> bool:
        if name not in self.playlists or name in ("เพลงสำหรับไลฟ์"):
            return False
        del self.playlists[name]
        
        path = os.path.join(PLAYLISTS_DIR, f"{name}.json")
        if os.path.exists(path):
            os.remove(path)
            
        self.current_playlist_name = "เพลงสำหรับไลฟ์"
        return True

    def add_track_to_playlist(self, playlist_name: str, file_path: str):
        if playlist_name in self.playlists:
            self.playlists[playlist_name].append(file_path)
            self.save_all_playlists()

    def import_playlist_data(self, name: str, tracks: List[str]):
        """นำเข้าเพลย์ลิสต์"""
        self.playlists[name] = tracks
        self.save_all_playlists()

    def export_playlist_data(self, name: str) -> str:
        """ส่งออกเพลย์ลิสต์ออกมาในแบบรูปแบบ JSON"""
        tracks = self.playlists.get(name, [])
        return json.dumps(tracks, indent=2, ensure_ascii=False)

    # --- ฟังก์ชันคิวคำขอเพลงจากผู้ชม ---
    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """ดึงรายการเพลงคำขอทั้งหมดที่มีสถานะค้างรอ (pending)"""
        return [req for req in self.request_queue if req["status"] == "pending"]

    def add_viewer_request(self, nickname: str, song_name: str) -> str:
        """ผู้ชมแชท !ขอเพลง หรือ !เพลง เพื่อนำคิวจองเข้าห้อง"""
        self.request_counter += 1
        req = {
            "id": self.request_counter,
            "user": nickname,
            "song": song_name,
            "status": "pending"
        }
        self.request_queue.append(req)
        return f"เพิ่มเพลง {song_name} ที่ขอโดยคุณ {nickname} เข้าสู่คิวเรียบร้อยแล้วค่ะ"

    def approve_viewer_request(self, request_id: int) -> Tuple[bool, str]:
        """สตรีมเมอร์กดอนุมัติเพลงและสั่งพูดประกาศชื่อเพื่อเล่น"""
        for req in self.request_queue:
            if req["id"] == request_id and req["status"] == "pending":
                req["status"] = "approved"
                
                # ประกาศออกลำโพง
                msg = f"อนุมัติเพลงคำขอ {req['song']} เรียบร้อยแล้วค่ะ"
                self.speak_fn(msg, 8)
                return True, msg
        return False, "ไม่พบรหัสคิวขอเพลงดังกล่าว"

    def reject_viewer_request(self, request_id: int) -> Tuple[bool, str]:
        for req in self.request_queue:
            if req["id"] == request_id and req["status"] == "pending":
                req["status"] = "rejected"
                msg = f"ปฏิเสธเพลง {req['song']} เรียบร้อยแล้วค่ะ"
                self.speak_fn(msg, 8)
                return True, msg
        return False, "ไม่พบรหัสคิวขอเพลงดังกล่าว"

    def request_song(self, nickname: str, song_name: str) -> str:
        """คีย์เสริมเชื่อมต่อเข้ากับ command_handler"""
        return self.add_viewer_request(nickname, song_name)
