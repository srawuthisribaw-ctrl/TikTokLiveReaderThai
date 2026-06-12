import unittest
import os
import json
import tempfile
from services.music_service import MusicService
from tts.audio_queue import AudioQueue

class TestMixerMusic(unittest.TestCase):
    """
    ชุดยูนิตเทสต์สำหรับการตรวจสอบการทำงานของ Mixer และคิวเพลง/เครื่องเล่นเพลง
    """
    def setUp(self):
        # สร้าง config.json จำลองสำหรับการเทสต์
        self.config_fd, self.config_path = tempfile.mkstemp(suffix=".json")
        os.close(self.config_fd)
        
        self.mock_config = {
            "Settings": {
                "last_id": "",
                "blacklist": [],
                "read_comment": True,
                "read_join": False,
                "read_gift": True
            },
            "TTS": {
                "mode": "nvda",
                "speed": 0,
                "volume": 1.0,
                "funny_style": "normal"
            },
            "SFX": {
                "master_volume": 1.0
            },
            "Mixer": {
                "active_profile": "normal",
                "profiles": {
                    "normal": {
                        "music": 0.3,
                        "comment": 1.0,
                        "gift": 1.0,
                        "sfx": 0.8,
                        "tts": 1.0,
                        "ai": 0.9
                    },
                    "game": {
                        "music": 0.1,
                        "comment": 0.8,
                        "gift": 1.0,
                        "sfx": 0.5,
                        "tts": 1.0,
                        "ai": 0.7
                    }
                }
            }
        }
        
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.mock_config, f, indent=2)

        # จำลองฟังก์ชัน speak
        self.speeches = []
        self.speak_fn = lambda text, lvl=5: self.speeches.append(text)
        
        self.music_service = MusicService(self.config_path, self.speak_fn)

    def tearDown(self):
        try:
            os.remove(self.config_path)
        except Exception:
            pass

    def test_mixer_volume_loading(self):
        """ตรวจสอบว่า MusicService โหลดระดับความดังของเพลงตาม Mixer Profile ถูกต้อง"""
        self.assertEqual(self.music_service.music_volume, 0.3)
        
        # เปลี่ยนโปรไฟล์เป็น game แล้วรีโหลด
        self.mock_config["Mixer"]["active_profile"] = "game"
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.mock_config, f, indent=2)
            
        self.music_service._load_mixer_volume()
        self.assertEqual(self.music_service.music_volume, 0.1)

    def test_viewer_song_request_flow(self):
        """ตรวจสอบระบบคิวขอเพลงจากผู้ชม: เพิ่มคิว อนุมัติ และปฏิเสธ"""
        # เริ่มต้นไม่มีคิว
        self.assertEqual(len(self.music_service.get_pending_requests()), 0)
        
        # 1. แฟนคลับขอเพลง
        res_msg = self.music_service.add_viewer_request("นายสมเกียรติ", "เพลงฝนตกไหม")
        self.assertIn("ฝนตกไหม", res_msg)
        self.assertIn("นายสมเกียรติ", res_msg)
        
        pending = self.music_service.get_pending_requests()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["song"], "เพลงฝนตกไหม")
        self.assertEqual(pending[0]["user"], "นายสมเกียรติ")
        
        req_id = pending[0]["id"]
        
        # 2. กดอนุมัติเพลง
        success, msg = self.music_service.approve_viewer_request(req_id)
        self.assertTrue(success)
        self.assertIn("อนุมัติเพลงคำขอ", msg)
        
        # คิว pending ต้องเป็น 0
        self.assertEqual(len(self.music_service.get_pending_requests()), 0)
        
        # 3. แฟนคลับอีกคนขอเพลงใหม่ แล้วถูกปฏิเสธ
        self.music_service.add_viewer_request("นางสาววรรณ", "เพลงขอมือเธอหน่อย")
        pending = self.music_service.get_pending_requests()
        self.assertEqual(len(pending), 1)
        req_id2 = pending[0]["id"]
        
        success2, msg2 = self.music_service.reject_viewer_request(req_id2)
        self.assertTrue(success2)
        self.assertIn("ปฏิเสธเพลง", msg2)
        self.assertEqual(len(self.music_service.get_pending_requests()), 0)

    def test_audio_queue_mixer_volume_calculation(self):
        """ตรวจสอบว่า AudioQueue ดึงโปรไฟล์ Mixer มาประมวลผลระดับความดังสุทธิถูกต้อง"""
        audio_queue = AudioQueue(self.config_path)
        
        # ดึงความดังช่องคอมเมนต์ในโปรไฟล์ normal
        audio_queue._load_config_settings()
        self.assertEqual(audio_queue.mixer_volumes.get("comment"), 1.0)
        self.assertEqual(audio_queue.mixer_volumes.get("music"), 0.3)
        
        # สลับเป็นโปรไฟล์ game
        self.mock_config["Mixer"]["active_profile"] = "game"
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.mock_config, f, indent=2)
            
        audio_queue._load_config_settings()
        self.assertEqual(audio_queue.mixer_volumes.get("comment"), 0.8)
        self.assertEqual(audio_queue.mixer_volumes.get("music"), 0.1)

if __name__ == "__main__":
    unittest.main()
