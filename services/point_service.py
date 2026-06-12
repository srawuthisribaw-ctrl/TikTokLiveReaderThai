from database.db_helper import DatabaseHelper
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

class PointService:
    """
    บริการจัดการคะแนนสะสม ระดับเลเวล และภารกิจประจำวันของผู้ชม
    เชื่อมโยงโดยตรงกับฐานข้อมูล SQLite
    """
    def __init__(self):
        self.db = DatabaseHelper()
        # คำจำกัดความเลเวลผู้ใช้
        self.level_titles = [
            (100, "ตำนานประจำช่อง"),
            (50, "VIP"),
            (20, "ผู้สนับสนุน"),
            (10, "แฟนคลับ"),
            (1, "ผู้ชมใหม่")
        ]
        # รายการสินค้าในร้านค้าคะแนน
        self.shop_items = {
            "สิทธิพิเศษ": 1000,
            "ขอเพลง": 200,
            "หมุนวงล้อ": 100,
            "เสียงเอฟเฟกต์": 300,
            "เปิดเกม": 500
        }

    def get_level_title(self, level: int) -> str:
        """แปลงเลเวลเป็นฉายาผู้ใช้"""
        for req_level, title in self.level_titles:
            if level >= req_level:
                return title
        return "ผู้ใช้งาน"

    def process_viewer_interaction(self, user_id: str, nickname: str, action: str, gift_diamonds: int = 0) -> Tuple[str, bool, bool]:
        """
        ประมวลผลการปฏิสัมพันธ์ของผู้ชม เพิ่มคะแนน อัปเดตเลเวล และตรวจสอบภารกิจ
        action: 'join', 'comment', 'like', 'share', 'gift'
        
        คืนค่า: (ข้อความประกาศ, เลเวลอัปหรือไม่, ภารกิจสำเร็จหรือไม่)
        """
        # 1. กำหนดคะแนนที่จะได้รับตามคอนฟิกหลัก
        points_gained = 0
        if action == "join":
            points_gained = 5
        elif action == "comment":
            points_gained = 1
        elif action == "like":
            points_gained = 2
        elif action == "share":
            points_gained = 10
        elif action == "gift":
            # 1 Diamond = 50 คะแนน
            points_gained = gift_diamonds * 50
            if points_gained == 0:
                points_gained = 50  # คะแนนขั้นต่ำสำหรับการให้ของขวัญฟรี/มูลค่าต่ำ
        
        # 2. บันทึกและคำนวณเลเวลอัปเกรดในฐานข้อมูล
        new_level = self.db.add_points(user_id, nickname, points_gained)
        
        announce_msg = ""
        level_up = False
        mission_completed = False
        
        # มีการเลื่อนระดับเลเวล
        if new_level > 0:
            title = self.get_level_title(new_level)
            announce_msg += f"{nickname} เลื่อนระดับเป็นเลเวล {new_level} ({title}) แล้ว! "
            level_up = True
            
        # 3. ตรวจสอบและอัปเดตภารกิจประจำวัน
        if action in ("comment", "like", "share"):
            # อัปเดตความคืบหน้าและเช็คว่าสำเร็จในแชทนี้หรือไม่
            completed = self.db.increment_mission_progress(user_id, action)
            if completed:
                announce_msg += f"ภารกิจประจำวันสำเร็จ! ยินดีด้วยกับคุณ {nickname}"
                mission_completed = True
                # รางวัลภารกิจสำเร็จ: เพิ่ม 200 คะแนน
                self.db.add_points(user_id, nickname, 200)

        return announce_msg, level_up, mission_completed

    def get_points_status(self, user_id: str, nickname: str) -> str:
        """สร้างข้อความสำหรับคำสั่ง !คะแนน"""
        profile = self.db.get_or_create_profile(user_id, nickname)
        points = profile["points"]
        level = profile["level"]
        title = self.get_level_title(level)
        xp = profile["xp"]
        xp_needed = level * 100
        
        return f"{nickname} มีคะแนนสะสม {points} คะแนน ปัจจุบันเลเวล {level} ({title}) ค่าประสบการณ์ {xp}/{xp_needed} เอ็กซ์พี"

    def get_mission_status(self, user_id: str, nickname: str) -> str:
        """สร้างข้อความสรุปความคืบหน้าภารกิจรายวัน"""
        mission = self.db.get_or_create_daily_mission(user_id)
        # เป้าหมายภารกิจ: คอมเมนต์ 20 ครั้ง, ไลก์ 100 ครั้ง, แชร์ 1 ครั้ง
        c_p = min(mission["comment_count"], 20)
        l_p = min(mission["like_count"], 100)
        s_p = min(mission["share_count"], 1)
        
        status_text = f"ภารกิจวันนี้ของ {nickname}: คอมเมนต์ {c_p}/20, ไลก์ {l_p}/100, แชร์ {s_p}/1"
        if mission["completed"] == 1:
            status_text += " (สำเร็จแล้ว)"
        else:
            status_text += " (กำลังดำเนินการ)"
        return status_text

    def get_shop_list(self) -> str:
        """สร้างข้อความแสดงรายการสินค้าในร้านค้าคะแนน"""
        items_str = []
        for item, price in self.shop_items.items():
            items_str.append(f"{item} ใช้ {price} คะแนน")
        return "ร้านค้าคะแนน: " + ", ".join(items_str) + " พิมพ์ !ซื้อ ตามด้วยชื่อสินค้าเพื่อแลกรับ"

    def buy_item(self, user_id: str, nickname: str, item_name: str) -> str:
        """ประมวลผลคำสั่งแลกซื้อสินค้า"""
        # หาคู่เทียบสินค้าโดยไม่สนช่องว่าง/พิมพ์เล็กใหญ่
        matched_item = None
        for item in self.shop_items:
            if item.strip() == item_name.strip():
                matched_item = item
                break
                
        if not matched_item:
            return f"ขออภัย ไม่มีสินค้าชื่อ {item_name} ในร้านค้า พิมพ์ !ร้านค้า เพื่อดูรายการทั้งหมด"
            
        price = self.shop_items[matched_item]
        success = self.db.record_purchase(user_id, matched_item, price)
        
        if success:
            return f"{nickname} แลกซื้อ {matched_item} สำเร็จแล้ว! หัก {price} คะแนน"
        else:
            profile = self.db.get_or_create_profile(user_id, nickname)
            curr_points = profile["points"]
            return f"{nickname} มีคะแนนไม่เพียงพอในการแลกซื้อ {matched_item} (ต้องการ {price} มีอยู่ {curr_points} คะแนน)"

    def get_leaderboard_status(self, limit: int = 3) -> str:
        """สร้างข้อความแสดงผู้สนับสนุนสูงสุดสำหรับ !อันดับ"""
        top_users = self.db.get_top_viewers(limit)
        if not top_users:
            return "ยังไม่มีข้อมูลการจัดอันดับผู้ชม"
            
        ranking_texts = []
        thai_numbers = ["หนึ่ง", "สอง", "สาม", "สี่", "ห้า"]
        
        for idx, user in enumerate(top_users):
            num_str = thai_numbers[idx] if idx < len(thai_numbers) else str(idx + 1)
            title = self.get_level_title(user["level"])
            ranking_texts.append(f"อันดับ{num_str} {user['nickname']} มี {user['points']} คะแนน เลเวล {user['level']}")
            
        return ", ".join(ranking_texts)

    def generate_fanbase_report(self) -> str:
        """สร้างรายงานชุมชนผู้สนับสนุนในแบบเสียงรายงาน"""
        stats = self.db.get_summary_statistics()
        top_viewers = self.db.get_top_viewers(1)
        top_gifter = self.db.execute_query(
            "SELECT nickname, SUM(diamonds * count) as total_d FROM gifts GROUP BY user_id ORDER BY total_d DESC LIMIT 1"
        )
        
        report = f"รายงานแฟนคลับ: ผู้ชมสะสมรวม {stats['total_viewers']} ท่าน. "
        if top_viewers:
            report += f"ผู้สนับสนุนอันดับหนึ่งคือ {top_viewers[0]['nickname']} สะสม {top_viewers[0]['points']} คะแนน. "
        if top_gifter and top_gifter[0]["total_d"] > 0:
            report += f"ผู้ส่งของขวัญสูงสุดคือคุณ {top_gifter[0]['nickname']} ยอดสะสม {top_gifter[0]['total_d']} เพชร"
        return report
