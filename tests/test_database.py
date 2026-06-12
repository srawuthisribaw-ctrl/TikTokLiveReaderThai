import unittest
import os
import tempfile
from database.db_helper import DatabaseHelper

class TestDatabaseHelper(unittest.TestCase):
    """
    ชุดการทดสอบการทำงานของระบบฐานข้อมูล SQLite (SQLite Unit Tests)
    """
    def setUp(self):
        # สร้างฐานข้อมูลจำลองแยกเฉพาะสำหรับการทดสอบ
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.db = DatabaseHelper(self.db_path)

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except Exception:
            pass

    def test_database_tables_initialization(self):
        """ทดสอบการสร้างตารางหลังบูตฐานข้อมูล"""
        # ตรวจสอบการดึงข้อมูลสถิติตารางหลัก
        stats = self.db.get_summary_statistics()
        self.assertEqual(stats["total_comments"], 0)
        self.assertEqual(stats["total_gifts"], 0)
        self.assertEqual(stats["total_followers"], 0)

    def test_add_comment_and_profile_creation(self):
        """ทดสอบการบันทึกคอมเมนต์และการสร้างโปรไฟล์ผู้ชมสะสม"""
        self.db.add_comment("user_123", "สมชาย", "สวัสดีครับ")
        
        # ตรวจสอบการบันทึกในตาราง comments
        rows = self.db.execute_query("SELECT * FROM comments")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["nickname"], "สมชาย")
        self.assertEqual(rows[0]["comment"], "สวัสดีครับ")
        
        # ตรวจสอบโปรไฟล์ผู้ชมสะสม
        profile = self.db.get_or_create_profile("user_123", "สมชาย")
        self.assertEqual(profile["comments_count"], 1)

    def test_points_accumulation_and_level_up(self):
        """ทดสอบระบบคำนวณคะแนนสะสมและการเลื่อนเลเวล"""
        # สร้างโปรไฟล์
        self.db.get_or_create_profile("user_456", "สมหญิง")
        
        # เพิ่ม 10 คะแนน เลเวลยังเป็น 1 (XP 100 จะอัปเลเวล)
        lvl_up = self.db.add_points("user_456", "สมหญิง", 9)
        self.assertEqual(lvl_up, 0)
        
        # เพิ่มอีก 2 คะแนน ทำให้เกิน 100 XP -> เลื่อนระดับเป็น 2
        lvl_up = self.db.add_points("user_456", "สมหญิง", 2)
        self.assertEqual(lvl_up, 2)
        
        # ตรวจสอบเลเวลและคะแนนสะสมในโปรไฟล์
        profile = self.db.get_or_create_profile("user_456", "สมหญิง")
        self.assertEqual(profile["points"], 11)
        self.assertEqual(profile["level"], 2)

    def test_daily_missions(self):
        """ทดสอบการบันทึกและตรวจสอบเควสประจำวัน"""
        user_id = "user_789"
        
        # อัปเดตคอมเมนต์ 20 ครั้ง, ไลก์ 100 ครั้ง, แชร์ 1 ครั้ง เพื่อทำภารกิจสำเร็จ
        for _ in range(20):
            self.db.increment_mission_progress(user_id, "comment")
        for _ in range(100):
            self.db.increment_mission_progress(user_id, "like")
            
        # เควสยังไม่สำเร็จเนื่องจากไม่ได้กดแชร์
        mission = self.db.get_or_create_daily_mission(user_id)
        self.assertEqual(mission["completed"], 0)
        
        # กดแชร์ 1 ครั้ง
        completed = self.db.increment_mission_progress(user_id, "share")
        self.assertTrue(completed)
        
        # ตรวจสอบหลังสำเร็จ
        mission = self.db.get_or_create_daily_mission(user_id)
        self.assertEqual(mission["completed"], 1)

if __name__ == "__main__":
    unittest.main()
