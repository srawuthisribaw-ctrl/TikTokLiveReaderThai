import sqlite3
import os
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys

if getattr(sys, 'frozen', False):
    DB_FILE = os.path.join(os.path.dirname(sys.executable), "_internal", "tiktok_live_reader.db")
else:
    DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tiktok_live_reader.db")

class DatabaseHelper:
    """
    คลาสสำหรับจัดการระบบฐานข้อมูล SQLite
    ใช้ล็อกล็อกอินเตอร์เซชันเพื่อป้องกันปัญหาเธรดชนกัน (Thread-safety)
    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseHelper, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db_path: str = DB_FILE):
        with self._lock:
            if getattr(self, "_initialized", False) and getattr(self, "db_path", None) == db_path:
                return
            self.db_path = db_path
            self._init_db()
            self._initialized = True

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """สร้างตารางที่จำเป็นทั้งหมดหากยังไม่มีในระบบ"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Enable WAL mode for better concurrency and avoiding database lockups
            try:
                cursor.execute("PRAGMA journal_mode=WAL;")
            except Exception as e:
                print(f"Error setting WAL mode: {e}")
            
            # 1. ตารางคอมเมนต์
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    nickname TEXT,
                    comment TEXT,
                    timestamp TEXT
                )
            """)

            # 2. ตารางของขวัญ
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gifts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    nickname TEXT,
                    gift_name TEXT,
                    count INTEGER,
                    diamonds INTEGER,
                    timestamp TEXT
                )
            """)

            # 3. ตารางผู้ติดตามใหม่
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS followers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    nickname TEXT,
                    timestamp TEXT
                )
            """)

            # 4. ตารางประวัติผู้ชมเข้าห้อง
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS viewers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    nickname TEXT,
                    timestamp TEXT
                )
            """)

            # 5. ตารางโปรไฟล์ผู้โต้ตอบ (คะแนนสะสม และ เลเวล)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS viewer_profiles (
                    user_id TEXT PRIMARY KEY,
                    nickname TEXT,
                    points INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    xp INTEGER DEFAULT 0,
                    join_count INTEGER DEFAULT 0,
                    comments_count INTEGER DEFAULT 0,
                    likes_count INTEGER DEFAULT 0,
                    shares_count INTEGER DEFAULT 0,
                    gifts_count INTEGER DEFAULT 0,
                    diamonds_count INTEGER DEFAULT 0,
                    last_active TEXT
                )
            """)

            # 6. ตารางภารกิจประจำวัน
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_missions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    date TEXT,
                    comment_count INTEGER DEFAULT 0,
                    like_count INTEGER DEFAULT 0,
                    share_count INTEGER DEFAULT 0,
                    completed INTEGER DEFAULT 0
                )
            """)

            # 7. ตารางประวัติการซื้อของจากร้านค้าคะแนน
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS shop_purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    item_name TEXT,
                    points_spent INTEGER,
                    timestamp TEXT
                )
            """)

            # 8. ตารางสถิติไลฟ์
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT,
                    value TEXT,
                    timestamp TEXT
                )
            """)

            conn.commit()
            conn.close()

    def execute_non_query(self, query: str, params: tuple = ()) -> int:
        """รันคำสั่ง SQL ที่ไม่ต้องการคืนค่า (INSERT, UPDATE, DELETE)"""
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                last_row_id = cursor.lastrowid or 0
                conn.close()
                return last_row_id
            except Exception as e:
                print(f"Database Execute Error: {e}")
                return -1

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """รันคำสั่ง SQL ที่ต้องการคืนค่าแถวข้อมูล"""
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                result = [dict(row) for row in rows]
                conn.close()
                return result
            except Exception as e:
                print(f"Database Query Error: {e}")
                return []

    # --- ฟังก์ชันคอมเมนต์ ---
    def add_comment(self, user_id: str, nickname: str, comment: str):
        now = datetime.now().isoformat()
        self.execute_non_query(
            "INSERT INTO comments (user_id, nickname, comment, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, nickname, comment, now)
        )
        self.update_activity_count(user_id, nickname, "comments_count")

    # --- ฟังก์ชันของขวัญ ---
    def add_gift(self, user_id: str, nickname: str, gift_name: str, count: int, diamonds: int):
        now = datetime.now().isoformat()
        self.execute_non_query(
            "INSERT INTO gifts (user_id, nickname, gift_name, count, diamonds, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, nickname, gift_name, count, diamonds, now)
        )
        self.update_activity_count(user_id, nickname, "gifts_count", count)
        if diamonds > 0:
            self.update_activity_count(user_id, nickname, "diamonds_count", diamonds * count)

    # --- ฟังก์ชันผู้ติดตาม ---
    def add_follower(self, user_id: str, nickname: str):
        now = datetime.now().isoformat()
        self.execute_non_query(
            "INSERT INTO followers (user_id, nickname, timestamp) VALUES (?, ?, ?)",
            (user_id, nickname, now)
        )
        self.update_activity_count(user_id, nickname, "shares_count")  # หรือกิจกรรมอื่น

    # --- ฟังก์ชันผู้เข้าชม ---
    def add_viewer_log(self, user_id: str, nickname: str):
        now = datetime.now().isoformat()
        self.execute_non_query(
            "INSERT INTO viewers (user_id, nickname, timestamp) VALUES (?, ?, ?)",
            (user_id, nickname, now)
        )
        self.update_activity_count(user_id, nickname, "join_count")

    # --- ระบบคะแนนและระดับเลเวล ---
    def get_or_create_profile(self, user_id: str, nickname: str) -> Dict[str, Any]:
        """ดึงข้อมูลโปรไฟล์ผู้ใช้ หากไม่มีให้สร้างใหม่"""
        with self._lock:
            rows = self.execute_query("SELECT * FROM viewer_profiles WHERE user_id = ?", (user_id,))
            if rows:
                return rows[0]
            
            now = datetime.now().isoformat()
            self.execute_non_query(
                "INSERT OR IGNORE INTO viewer_profiles (user_id, nickname, points, level, xp, last_active) VALUES (?, ?, 0, 1, 0, ?)",
                (user_id, nickname, now)
            )
            rows = self.execute_query("SELECT * FROM viewer_profiles WHERE user_id = ?", (user_id,))
            return rows[0] if rows else {}

    def add_points(self, user_id: str, nickname: str, points: int) -> int:
        """เพิ่มคะแนนสะสมและคำนวณเลเวลอัปเกรด"""
        with self._lock:
            self.get_or_create_profile(user_id, nickname)
            now = datetime.now().isoformat()
            
            # เพิ่มค่าประสบการณ์ตามคะแนน (1 คะแนน = 10 XP)
            xp_gained = points * 10
            
            rows = self.execute_query("SELECT points, level, xp FROM viewer_profiles WHERE user_id = ?", (user_id,))
            if not rows:
                return 0
            
            current_points = rows[0]["points"] + points
            current_level = rows[0]["level"]
            current_xp = rows[0]["xp"] + xp_gained
            
            # สูตรการเลื่อนระดับเลเวล: xp_needed = level * 100
            leveled_up = False
            while True:
                xp_needed = current_level * 100
                if current_xp >= xp_needed and current_level < 100:
                    current_xp -= xp_needed
                    current_level += 1
                    leveled_up = True
                else:
                    break
                    
            self.execute_non_query(
                "UPDATE viewer_profiles SET points = ?, level = ?, xp = ?, nickname = ?, last_active = ? WHERE user_id = ?",
                (current_points, current_level, current_xp, nickname, now, user_id)
            )
            
            return current_level if leveled_up else 0

    def update_activity_count(self, user_id: str, nickname: str, column_name: str, add_value: int = 1):
        """อัปเดตสถิติกิจกรรมรายบุคคล"""
        with self._lock:
            self.get_or_create_profile(user_id, nickname)
            self.execute_non_query(
                f"UPDATE viewer_profiles SET {column_name} = {column_name} + ?, nickname = ?, last_active = ? WHERE user_id = ?",
                (add_value, nickname, datetime.now().isoformat(), user_id)
            )

    # --- ภารกิจประจำวัน (Daily Missions) ---
    def get_or_create_daily_mission(self, user_id: str) -> Dict[str, Any]:
        with self._lock:
            today = datetime.now().strftime("%Y-%m-%d")
            rows = self.execute_query("SELECT * FROM daily_missions WHERE user_id = ? AND date = ?", (user_id, today))
            if rows:
                return rows[0]
            
            self.execute_non_query(
                "INSERT INTO daily_missions (user_id, date, comment_count, like_count, share_count, completed) VALUES (?, ?, 0, 0, 0, 0)",
                (user_id, today)
            )
            rows = self.execute_query("SELECT * FROM daily_missions WHERE user_id = ? AND date = ?", (user_id, today))
            return rows[0]

    def increment_mission_progress(self, user_id: str, activity: str) -> bool:
        """
        อัปเดตภารกิจรายวันตามประเภทกิจกรรม
        activity: 'comment', 'like', 'share'
        คืนค่า True หากภารกิจสำเร็จในการกดครั้งนี้
        """
        with self._lock:
            self.get_or_create_daily_mission(user_id)
            today = datetime.now().strftime("%Y-%m-%d")
            
            col_map = {
                "comment": "comment_count",
                "like": "like_count",
                "share": "share_count"
            }
            
            if activity not in col_map:
                return False
                
            col = col_map[activity]
            self.execute_non_query(
                f"UPDATE daily_missions SET {col} = {col} + 1 WHERE user_id = ? AND date = ?",
                (user_id, today)
            )
            
            # ตรวจสอบการทำภารกิจสำเร็จ
            # เป้าหมายภารกิจ: คอมเมนต์ 20 ครั้ง, ไลก์ 100 ครั้ง, แชร์ 1 ครั้ง
            mission = self.execute_query("SELECT * FROM daily_missions WHERE user_id = ? AND date = ?", (user_id, today))[0]
            
            if mission["completed"] == 0:
                if mission["comment_count"] >= 20 and mission["like_count"] >= 100 and mission["share_count"] >= 1:
                    self.execute_non_query(
                        "UPDATE daily_missions SET completed = 1 WHERE user_id = ? AND date = ?",
                        (user_id, today)
                    )
                    return True
            return False

    # --- ฟังก์ชันร้านค้าคะแนน ---
    def record_purchase(self, user_id: str, item_name: str, points: int) -> bool:
        """บันทึกการซื้อของและหักคะแนน"""
        with self._lock:
            rows = self.execute_query("SELECT points FROM viewer_profiles WHERE user_id = ?", (user_id,))
            if not rows or rows[0]["points"] < points:
                return False
                
            now = datetime.now().isoformat()
            # หักคะแนน
            self.execute_non_query(
                "UPDATE viewer_profiles SET points = points - ? WHERE user_id = ?",
                (points, user_id)
            )
            # บันทึกประวัติ
            self.execute_non_query(
                "INSERT INTO shop_purchases (user_id, item_name, points_spent, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, item_name, points, now)
            )
            return True

    # --- ระบบสรุปและสถิติภาพรวม ---
    def get_top_viewers(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self.execute_query(
            "SELECT nickname, points, level FROM viewer_profiles ORDER BY points DESC LIMIT ?",
            (limit,)
        )

    def get_summary_statistics(self) -> Dict[str, Any]:
        """สรุปตัวเลขสถิติทั้งหมดในระบบ"""
        comments = self.execute_query("SELECT COUNT(*) as cnt FROM comments")[0]["cnt"]
        gifts = self.execute_query("SELECT COUNT(*) as cnt, SUM(diamonds * count) as coins FROM gifts")[0]
        followers = self.execute_query("SELECT COUNT(*) as cnt FROM followers")[0]["cnt"]
        viewers = self.execute_query("SELECT COUNT(*) as cnt FROM viewers")[0]["cnt"]
        
        return {
            "total_comments": comments,
            "total_gifts": gifts["cnt"] or 0,
            "total_diamonds": gifts["coins"] or 0,
            "total_followers": followers,
            "total_viewers": viewers,
            "estimated_earnings_thb": (gifts["coins"] or 0) * 0.15  # สมมติ 1 เพชร = 0.15 บาท
        }

    def save_live_metric(self, metric: str, value: str):
        now = datetime.now().isoformat()
        self.execute_non_query(
            "INSERT INTO statistics (metric_name, value, timestamp) VALUES (?, ?, ?)",
            (metric, value, now)
        )
