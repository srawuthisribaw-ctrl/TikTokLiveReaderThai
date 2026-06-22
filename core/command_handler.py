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

    def handle_chat_command(self, user_id: str, nickname: str, message: str) -> Optional[Tuple[str, str, int, str]]:
        """
        วิเคราะห์แชทของผู้ชม หากพบคำสั่งที่ขึ้นต้นด้วย '!' จะทำการประมวลผลทันที
        คืนค่า: Tuple(ข้อความเสียงสำหรับอ่านออกอากาศ, คีย์เสียงเอฟเฟกต์, ระดับความสำคัญของเสียง, ช่องเสียงมิกเซอร์) หรือ None
        """
        msg = message.strip()
        if not msg:
            return None

        # 1. จัดการคำทายหรือการโต้ตอบเกมที่กำลังทำงานอยู่เป็นลำดับแรก
        game_res = self.games.handle_viewer_attempt(user_id, nickname, msg)
        if game_res:
            # game_res คืนค่า (ข้อความประกาศ, คีย์ sfx)
            # เราให้ระดับความสำคัญของเกมคีย์เสียง = 5 (คอมเมนต์/คำสั่ง)
            return game_res[0], game_res[1], 5, "tts"

        # ตรวจสอบว่าแชทขึ้นต้นด้วย ! หรือ @ หรือไม่
        if not (msg.startswith("!") or msg.startswith("@")):
            # เช็คคำสุ่มตอบสั้นๆ ในกรณีเล่นเกมพิมพ์เร็วแบบตรงคีย์ (ไม่มี !)
            if self.games.active_game == "fast_response":
                fast_res = self.games.handle_viewer_attempt(user_id, nickname, msg)
                if fast_res:
                    return fast_res[0], fast_res[1], 5, "tts"
            return None

        parts = msg.split(" ", 1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        from core.i18n import get_language
        import json
        lang = get_language()

        # --- คำสั่งที่ 1: !ช่วยเหลือ / !help ---
        if command in ("!ช่วยเหลือ", "!help"):
            if lang == "en":
                help_text = (
                    "Available chat commands: !points (view points), !rank (view leaderboard), "
                    "!mission (view daily quest), !shop (view items), !buy (purchase special privilege), "
                    "!spin (lucky wheel), !song (request a song), !ask (ask AI), !join (join lucky draw)"
                )
            else:
                help_text = (
                    "คำสั่งช่องแชทที่มีในระบบคือ: !คะแนน (ดูคะแนน), !อันดับ (ดูอันดับคนดู), "
                    "!ภารกิจ (ดูเควสประจำวัน), !ร้านค้า (ดูราคาไอเทม), !ซื้อ (แลกซื้อสิทธิพิเศษ), "
                    "!หมุน (วงล้อนำโชค), !เพลง (ขอเพลง), !ถาม หรือ @ตามด้วยคำถาม (ถามคำถาม AI), !ร่วมกิจกรรม (ลุ้นรางวัลจับสลาก)"
                )
            return help_text, "sfx_comment", 5, "tts"

        # --- คำสั่งที่ 2: !คะแนน / !points ---
        elif command in ("!คะแนน", "!points"):
            status = self.points.get_points_status(user_id, nickname)
            return status, "sfx_comment", 5, "tts"

        # --- คำสั่งที่ 3: !อันดับ / !rank ---
        elif command in ("!อันดับ", "!rank"):
            lead = self.points.get_leaderboard_status(3)
            return lead, "sfx_comment", 5, "tts"

        # --- คำสั่งที่ 4: !ภารกิจ / !mission ---
        elif command in ("!ภารกิจ", "!mission"):
            miss = self.points.get_mission_status(user_id, nickname)
            return miss, "sfx_comment", 5, "tts"

        # --- คำสั่งที่ 5: !เวลา / !time ---
        elif command in ("!เวลา", "!time"):
            if lang == "en":
                now_str = datetime.now().strftime("%I:%M:%S %p")
                return f"Current time is {now_str}.", "sfx_comment", 5, "tts"
            else:
                now_str = datetime.now().strftime("%H นาฬิกา %M นาที %S วินาที")
                return f"ขณะนี้เวลา {now_str} ครับ", "sfx_comment", 5, "tts"

        # --- คำสั่งที่ 6: !ร่วมกิจกรรม / !join ---
        elif command in ("!ร่วมกิจกรรม", "!join"):
            res = self.games.join_lucky_draw(user_id, nickname)
            return res, "sfx_comment", 5, "tts"

        # --- คำสั่งที่ 7: !หมุน / !spin ---
        elif command in ("!หมุน", "!spin"):
            msg, sfx = self.games.spin_wheel(user_id, nickname)
            return msg, sfx, 5, "tts"

        # --- คำสั่งที่ 8: !ร้านค้า / !shop ---
        elif command in ("!ร้านค้า", "!shop"):
            shop = self.points.get_shop_list()
            return shop, "sfx_comment", 5, "tts"

        # --- คำสั่งที่ 9: !ซื้อ / !buy ---
        elif command in ("!ซื้อ", "!buy"):
            if not args:
                if lang == "en":
                    return f"Hello {nickname}, please specify a shop item name. Example: !buy Song Request", "sfx_comment", 5, "tts"
                else:
                    return f"คุณ {nickname} กรุณาระบุชื่อสินค้าด้วยค่ะ เช่น พิมพ์ !ซื้อ ขอเพลง", "sfx_comment", 5, "tts"
            buy_res = self.points.buy_item(user_id, nickname, args)
            return buy_res, "sfx_gift", 5, "tts"

        # --- คำสั่งที่ 10: !เลเวล / !level ---
        elif command in ("!เลเวล", "!level"):
            profile = self.points.db.get_or_create_profile(user_id, nickname)
            level = profile["level"]
            title = self.points.get_level_title(level)
            if lang == "en":
                return f"{nickname} level is {level}, title is {title}.", "sfx_comment", 5, "tts"
            else:
                return f"คุณ {nickname} เลเวล {level} สเตตัส {title}", "sfx_comment", 5, "tts"

        # --- คำสั่งที่ 11: !สถิติ / !stats ---
        elif command in ("!สถิติ", "!stats"):
            stats = self.points.db.get_summary_statistics()
            if lang == "en":
                stats_text = f"Current room stats: Total Viewers: {stats['total_viewers']}, Cumulative Comments: {stats['total_comments']}"
            else:
                stats_text = f"สถิติห้องปัจจุบัน: ผู้ชมรวม {stats['total_viewers']} คน ยอดคอมเมนต์สะสม {stats['total_comments']} ข้อความ"
            return stats_text, "sfx_comment", 5, "tts"

        # --- คำสั่งที่ 12: !กิจกรรม / !game ---
        elif command in ("!กิจกรรม", "!game"):
            if self.games.active_game:
                if lang == "en":
                    return f"Current activity is game: {self.games.active_game}. Type your answer to join the fun!", "sfx_comment", 5, "tts"
                else:
                    return f"กิจกรรมปัจจุบันคือเกม: {self.games.active_game} พิมพ์คำตอบเพื่อร่วมสนุกได้เลยครับ", "sfx_comment", 5, "tts"
            if lang == "en":
                return "No active interactive game at the moment. Streamers can start a game from the Tools menu.", "sfx_comment", 5, "tts"
            else:
                return "ขณะนี้ยังไม่มีเกมโต้ตอบเริ่มสตรีมอยู่ สตรีมเมอร์สามารถกดเปิดเกมผ่านเมนูเครื่องมือได้ครับ", "sfx_comment", 5, "tts"

        # --- คำสั่งที่ 13: !เพลง / !song ---
        elif command in ("!เพลง", "!song"):
            if not args:
                if lang == "en":
                    return f"Hello {nickname}, please specify a song name. Example: !song My Way", "sfx_comment", 5, "tts"
                else:
                    return f"คุณ {nickname} กรุณาระบุชื่อเพลงด้วยครับ เช่น !เพลง กลับตัวกลับใจ", "sfx_comment", 5, "tts"
            req_msg = self.radio.request_song(nickname, args)
            return req_msg, "sfx_comment", 5, "tts"

        # --- คำสั่งที่ 14: !ถาม / !ask / @ถาม / @ask / @บอท / @bot / @ai / @AI / หรือการใช้ @ นำหน้าคำถาม ---
        elif command in ("!ถาม", "!ask", "@ถาม", "@ask", "@บอท", "@bot", "@ai", "@AI") or command == "@" or command.startswith("@"):
            # ตรวจสอบการเปิดใช้งานผู้ช่วย AI สำหรับผู้ชมจากไฟล์คอนฟิก
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                viewer_enabled = config.get("AI", {}).get("viewer_assistant_enabled", True)
            except Exception:
                viewer_enabled = True

            if not viewer_enabled:
                return None

            if command in ("!ถาม", "!ask", "@ถาม", "@ask", "@บอท", "@bot", "@ai", "@AI"):
                question_text = args
            elif command == "@":
                question_text = args
            else:
                question_text = command[1:]
                if args:
                    question_text += " " + args

            if not question_text.strip():
                if lang == "en":
                    return f"Hello {nickname}, please type a question after the @ or !ask command.", "sfx_comment", 5, "ai"
                else:
                    return f"คุณ {nickname} กรุณาพิมพ์คำถามต่อท้ายเครื่องหมาย @ หรือ !ถาม ด้วยครับ", "sfx_comment", 5, "ai"
            ai_answer = self.ai.answer_viewer_query(nickname, question_text)
            return ai_answer, "sfx_comment", 5, "ai"

        return None
