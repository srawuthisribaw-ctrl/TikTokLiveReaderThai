from typing import Dict, Any, Optional, Tuple
from services.point_service import PointService
from services.game_service import GameService
from services.radio_service import RadioService
from services.ai_service import AIService
from datetime import datetime

class CommandHandler:
    """
    คลาสตัวประมวลผลและกระจายคำสั่งจากผู้ชมในช่องแชท (!คำสั่งแชท)
    ทำหน้าที่เชื่อมประสานโมดูลบริการหลักเข้าด้วยกัน
    """
    def __init__(self, config_path: str, point_service: PointService, game_service: GameService, radio_service: RadioService, ai_service: AIService):
        self.config_path = config_path
        self.points = point_service
        self.games = game_service
        self.radio = radio_service
        self.ai = ai_service

    def handle_chat_command(self, user_id: str, nickname: str, message: str) -> Optional[Tuple[str, str, int]]:
        """
        วิเคราะห์แชทของผู้ชม หากพบคำสั่งที่ขึ้นต้นด้วย '!' จะทำการประมวลผลทันที
        คืนค่า: Tuple(ข้อความเสียงสำหรับอ่านออกอากาศ, คีย์เสียงเอฟเฟกต์, ระดับความสำคัญของเสียง) หรือ None
        """
        msg = message.strip()
        if not msg:
            return None

        # 1. จัดการคำทายหรือการโต้ตอบเกมที่กำลังทำงานอยู่เป็นลำดับแรก
        game_res = self.games.handle_viewer_attempt(user_id, nickname, msg)
        if game_res:
            # game_res คืนค่า (ข้อความประกาศ, คีย์ sfx)
            # เราให้ระดับความสำคัญของเกมคีย์เสียง = 5 (คอมเมนต์/คำสั่ง)
            return game_res[0], game_res[1], 5

        # ตรวจสอบว่าแชทขึ้นต้นด้วย ! หรือไม่
        if not msg.startswith("!"):
            # เช็คคำสุ่มตอบสั้นๆ ในกรณีเล่นเกมพิมพ์เร็วแบบตรงคีย์ (ไม่มี !)
            if self.games.active_game == "fast_response":
                fast_res = self.games.handle_viewer_attempt(user_id, nickname, msg)
                if fast_res:
                    return fast_res[0], fast_res[1], 5
            return None

        parts = msg.split(" ", 1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # --- คำสั่งที่ 1: !ช่วยเหลือ ---
        if command == "!ช่วยเหลือ":
            help_text = (
                "คำสั่งช่องแชทที่มีในระบบคือ: !คะแนน (ดูคะแนน), !อันดับ (ดูอันดับคนดู), "
                "!ภารกิจ (ดูเควสประจำวัน), !ร้านค้า (ดูราคาไอเทม), !ซื้อ (แลกซื้อสิทธิพิเศษ), "
                "!หมุน (วงล้อนำโชค), !เพลง (ขอเพลง), !ถาม (ถามคำถาม AI), !ร่วมกิจกรรม (ลุ้นรางวัลจับสลาก)"
            )
            return help_text, "sfx_comment", 5

        # --- คำสั่งที่ 2: !คะแนน ---
        elif command == "!คะแนน":
            status = self.points.get_points_status(user_id, nickname)
            return status, "sfx_comment", 5

        # --- คำสั่งที่ 3: !อันดับ ---
        elif command == "!อันดับ":
            lead = self.points.get_leaderboard_status(3)
            return lead, "sfx_comment", 5

        # --- คำสั่งที่ 4: !ภารกิจ ---
        elif command == "!ภารกิจ":
            miss = self.points.get_mission_status(user_id, nickname)
            return miss, "sfx_comment", 5

        # --- คำสั่งที่ 5: !เวลา ---
        elif command == "!เวลา":
            now_str = datetime.now().strftime("%H นาฬิกา %M นาที %S วินาที")
            return f"ขณะนี้เวลา {now_str} ครับ", "sfx_comment", 5

        # --- คำสั่งที่ 6: !ร่วมกิจกรรม ---
        elif command == "!ร่วมกิจกรรม":
            res = self.games.join_lucky_draw(user_id, nickname)
            return res, "sfx_comment", 5

        # --- คำสั่งที่ 7: !หมุน ---
        elif command == "!หมุน":
            msg, sfx = self.games.spin_wheel(user_id, nickname)
            return msg, sfx, 5

        # --- คำสั่งที่ 8: !ร้านค้า ---
        elif command == "!ร้านค้า":
            shop = self.points.get_shop_list()
            return shop, "sfx_comment", 5

        # --- คำสั่งที่ 9: !ซื้อ ---
        elif command == "!ซื้อ":
            if not args:
                return f"คุณ {nickname} กรุณาระบุชื่อสินค้าด้วยค่ะ เช่น พิมพ์ !ซื้อ ขอเพลง", "sfx_comment", 5
            buy_res = self.points.buy_item(user_id, nickname, args)
            return buy_res, "sfx_gift", 5

        # --- คำสั่งที่ 10: !เลเวล ---
        elif command == "!เลเวล":
            profile = self.points.db.get_or_create_profile(user_id, nickname)
            level = profile["level"]
            title = self.points.get_level_title(level)
            return f"คุณ {nickname} เลเวล {level} สเตตัส {title}", "sfx_comment", 5

        # --- คำสั่งที่ 11: !สถิติ ---
        elif command == "!สถิติ":
            stats = self.points.db.get_summary_statistics()
            stats_text = f"สถิติห้องปัจจุบัน: ผู้ชมรวม {stats['total_viewers']} คน ยอดคอมเมนต์สะสม {stats['total_comments']} ข้อความ"
            return stats_text, "sfx_comment", 5

        # --- คำสั่งที่ 12: !กิจกรรม ---
        elif command == "!กิจกรรม":
            if self.games.active_game:
                return f"กิจกรรมปัจจุบันคือเกม: {self.games.active_game} พิมพ์คำตอบเพื่อร่วมสนุกได้เลยครับ", "sfx_comment", 5
            return "ขณะนี้ยังไม่มีเกมโต้ตอบเริ่มสตรีมอยู่ สตรีมเมอร์สามารถกดเปิดเกมผ่านเมนูเครื่องมือได้ครับ", "sfx_comment", 5

        # --- คำสั่งที่ 13: !เพลง ---
        elif command == "!เพลง":
            if not args:
                return f"คุณ {nickname} กรุณาระบุชื่อเพลงด้วยครับ เช่น !เพลง กลับตัวกลับใจ", "sfx_comment", 5
            req_msg = self.radio.request_song(nickname, args)
            return req_msg, "sfx_comment", 5

        # --- คำสั่งที่ 14: !ถาม ---
        elif command == "!ถาม":
            if not args:
                return f"คุณ {nickname} กรุณาพิมพ์คำถามต่อท้ายคำสั่ง !ถาม ด้วยครับ", "sfx_comment", 5
            ai_answer = self.ai.answer_viewer_query(nickname, args)
            return ai_answer, "sfx_comment", 5

        return None
