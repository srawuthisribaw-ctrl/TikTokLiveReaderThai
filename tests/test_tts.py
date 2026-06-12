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

if __name__ == "__main__":
    unittest.main()
