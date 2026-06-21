import unittest
import queue
import time
from tts.audio_queue import AudioQueue

class TestTTSPriorityQueue(unittest.TestCase):
    """
    ชุดการทดสอบการจัดคิวและคำนวณลำดับความสำคัญของเสียงพูด
    """
    def test_priority_queue_sorting(self):
        """ทดสอบลำดับการเรียงของ Priority Queue สำหรับเสียงพูด"""
        # สร้าง Priority Queue เปล่า
        pq = queue.PriorityQueue()
        
        # ป้อนข้อมูลจำลอง: (priority, timestamp, text)
        # 1. คนเข้าห้อง (Level 2) -> priority = 98
        pq.put((100 - 2, time.time(), "สมหญิง เข้าห้อง"))
        
        # 2. ของขวัญใหญ่ (Level 10) -> priority = 90
        pq.put((100 - 10, time.time(), "สมชาย ส่งสิงโต"))
        
        # 3. คอมเมนต์ (Level 5) -> priority = 95
        pq.put((100 - 5, time.time(), "กล้วย พิมพ์สวัสดี"))
        
        # ดึงลำดับข้อมูล: ลำดับที่ถูกต้องต้องดึงของขวัญใหญ่ -> คอมเมนต์ -> คนเข้าห้อง
        first = pq.get()
        second = pq.get()
        third = pq.get()
        
        self.assertEqual(first[2], "สมชาย ส่งสิงโต")
        self.assertEqual(second[2], "กล้วย พิมพ์สวัสดี")
        self.assertEqual(third[2], "สมหญิง เข้าห้อง")

    def test_mute_behavior(self):
        """ทดสอบการส่งผ่านสถานะเงียบเสียง (Mute) ไปยัง TTS Engine และการรีเซ็ตเมื่อเริ่มพูดใหม่"""
        aq = AudioQueue("config.dat")
        try:
            self.assertFalse(aq.muted)
            self.assertFalse(aq.tts.muted)
            
            # เรียกใช้ mute()
            aq.mute()
            
            # ตรวจสอบว่าสถานะ tts.muted ถูกบันทึกเป็น True
            self.assertTrue(aq.tts.muted)
            
            # เมื่อมีการอ่านข้อความครั้งถัดไป สถานะปิดเสียงของ tts จะต้องถูกรีเซ็ตเป็น False
            aq.tts.speak("", "google", "", 0, 0.0)
            self.assertFalse(aq.tts.muted)
        finally:
            pass

if __name__ == "__main__":
    unittest.main()
