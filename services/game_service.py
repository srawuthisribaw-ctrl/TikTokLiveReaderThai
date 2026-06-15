import random
from typing import Dict, Any, List, Tuple, Optional
from database.db_helper import DatabaseHelper

class GameService:
    """
    บริการระบบเกมโต้ตอบและสุ่มรางวัลในไลฟ์สดสำหรับผู้ชม
    """
    def __init__(self):
        self.db = DatabaseHelper()
        self.active_game: Optional[str] = None  # ชนิดเกมที่กำลังเล่นอยู่
        self.game_data: Dict[str, Any] = {}     # ข้อมูลสถานะเกมปัจจุบัน
        self.lucky_draw_entrants: List[Tuple[str, str]] = [] # รายชื่อผู้ร่วมกิจกรรมจับฉลาก (user_id, nickname)
        
        
        # คลังเกมตอบคำถาม (Quiz)
        self.quizzes = [
            {"q": "อะไรเอ่ย กลางวันมีสี่ขา กลางคืนมีสองขา?", "a": "ที่นอน", "hint": "ใช้หนุนนอน"},
            {"q": "จังหวัดใดในประเทศไทยอยู่ใต้สุด?", "a": "ยะลา", "hint": "อักษรนำ ย. ยักษ์"},
            {"q": "กรุงเทพมหานครมีชื่อเดิมว่าอะไร?", "a": "บางกอก", "hint": "คำขึ้นต้นด้วย บาง"},
            {"q": "ผลไม้อะไรเอ่ย มีตารอบตัว?", "a": "สับปะรด", "hint": "รสเปรี้ยวอมหวาน"},
            {"q": "สัตว์ประจำชาติไทยคือตัวอะไร?", "a": "ช้าง", "hint": "สัตว์สี่เท้าขนาดใหญ่ มีงวง"}
        ]
        
        self.quizzes_en = [
            {"q": "What is the capital of France?", "a": "Paris", "hint": "Starts with P"},
            {"q": "Which planet is known as the Red Planet?", "a": "Mars", "hint": "Four letters"},
            {"q": "How many days are in a leap year?", "a": "366", "hint": "Three-digit number"},
            {"q": "What is the largest mammal in the world?", "a": "Blue Whale", "hint": "Lives in the ocean"},
            {"q": "What is the color of an emerald?", "a": "Green", "hint": "Like grass"}
        ]
        
        # คลังเกมทายคำ (Scrambled word)
        self.words = [
            {"word": "กล้วยหอม", "scrambled": "หล้วยกอม", "hint": "ผลไม้สีเหลืองยาวๆ"},
            {"word": "พัทยา", "scrambled": "ยาทัพ", "hint": "สถานที่ท่องเที่ยวทะเลจังหวัดชลบุรี"},
            {"word": "ปลาทูน่า", "scrambled": "น่าทูปลา", "hint": "ปลาทะเลกระป๋องยอดฮิต"},
            {"word": "เครื่องบิน", "scrambled": "บินเครื่อง", "hint": "ยานพาหนะลอยฟ้า"}
        ]

        self.words_en = [
            {"word": "banana", "scrambled": "nabana", "hint": "A yellow curved fruit"},
            {"word": "computer", "scrambled": "roctpmue", "hint": "Device used for coding and gaming"},
            {"word": "airplane", "scrambled": "nalpaeir", "hint": "Flying vehicle"},
            {"word": "chocolate", "scrambled": "lacoetoch", "hint": "Sweet brown treat"}
        ]

    def start_guess_number(self) -> str:
        """เริ่มเกมทายตัวเลข (1 - 100)"""
        from core.i18n import get_language
        lang = get_language()
        self.active_game = "guess_number"
        target = random.randint(1, 100)
        self.game_data = {"target": target}
        if lang == "en":
            return "Number guessing game started! Guess a number between 1 and 100. Type !guess <number>. First to guess correctly wins!"
        else:
            return "ระบบเริ่มเกมทายตัวเลขแล้ว! ให้ผู้ชมพิมพ์ !ทาย ตามด้วยตัวเลขระหว่าง 1 ถึง 100 ใครตอบถูกก่อนชนะ"

    def start_guess_word(self) -> str:
        """เริ่มเกมทายคำศัพท์"""
        from core.i18n import get_language
        lang = get_language()
        self.active_game = "guess_word"
        
        pool = self.words_en if lang == "en" else self.words
        chosen = random.choice(pool)
        self.game_data = {"word": chosen["word"], "scrambled": chosen["scrambled"]}
        
        if lang == "en":
            return f"Scrambled word game started! Scrambled: {chosen['scrambled']} (Hint: {chosen['hint']}) Type !guess <word> to answer!"
        else:
            return f"เริ่มเกมทายคำศัพท์! คำสลับอักษรคือ: {chosen['scrambled']} (คำใบ้: {chosen['hint']}) พิมพ์ !ทาย ตามด้วยคำศัพท์ที่ถูกต้อง"

    def start_quiz(self) -> str:
        """เริ่มเกมตอบคำถามความรู้รอบตัว"""
        from core.i18n import get_language
        lang = get_language()
        self.active_game = "quiz"
        
        pool = self.quizzes_en if lang == "en" else self.quizzes
        chosen = random.choice(pool)
        self.game_data = {"q": chosen["q"], "a": chosen["a"], "hint": chosen["hint"]}
        
        if lang == "en":
            return f"Trivia quiz game started! Question: {chosen['q']} Type !answer <answer> to reply!"
        else:
            return f"เริ่มเกมตอบคำถาม! คำถามคือ: {chosen['q']} พิมพ์ !ตอบ ตามด้วยคำตอบของคุณ"

    def start_fast_response(self) -> str:
        """เริ่มเกมทายเร็ว (พิมพ์เร็ว)"""
        from core.i18n import get_language
        lang = get_language()
        self.active_game = "fast_response"
        
        if lang == "en":
            words_pool = ["streamer fighting", "this live stream is fun", "give a big heart", "lovely supporters"]
        else:
            words_pool = ["สตรีมเมอร์สู้ๆ", "ไลฟ์สดสัปดาห์นี้สนุกมาก", "ขอหัวใจดวงโตๆ", "ผู้สนับสนุนที่น่ารัก"]
            
        target_phrase = random.choice(words_pool)
        self.game_data = {"target": target_phrase}
        
        if lang == "en":
            return f"Fast typing game started! Type this phrase as fast as you can to get bonus points: '{target_phrase}' (Type directly in chat)"
        else:
            return f"เริ่มเกมตอบเร็ว! ใครพิมพ์คำนี้เร็วที่สุดรับคะแนนพิเศษ: '{target_phrase}' พิมพ์ตรงๆ ในช่องแชทได้เลย"

    def start_monopoly_event(self) -> str:
        """เริ่มกิจกรรมจำลองเกมเศรษฐีแบบสุ่มเหตุการณ์"""
        from core.i18n import get_language
        lang = get_language()
        self.active_game = "monopoly"
        
        if lang == "en":
            events = [
                ("Landed on a bonus square", 100),
                ("Fined for property tax", -50),
                ("Won property sweepstakes", 200),
                ("Landed on travel square", 50),
                ("Donated to charity", -30)
            ]
        else:
            events = [
                ("เดินตกช่องรับโบนัส", 100),
                ("ถูกปรับภาษีที่อยู่อาศัย", -50),
                ("ชนะการจับรางวัลอสังหาริมทรัพย์", 200),
                ("ตกช่องเดินทางท่องเที่ยว", 50),
                ("บริจาคการกุศล", -30)
            ]
        chosen_event, score_mod = random.choice(events)
        self.game_data = {"event": chosen_event, "mod": score_mod}
        
        if lang == "en":
            return f"Monopoly event started! The next viewer to comment will land on: {chosen_event} (Get/deduct {score_mod} points)"
        else:
            return f"เริ่มกิจกรรมเกมเศรษฐีจำลอง! ผู้ชมที่ส่งคอมเมนต์ถัดไปจะเข้าช่อง: {chosen_event} (รับ/หัก {score_mod} คะแนน)"

    def join_lucky_draw(self, user_id: str, nickname: str) -> str:
        """ผู้ชมพิมพ์ !ร่วมกิจกรรม เพื่อเข้าคิวลุ้นรางวัล"""
        from core.i18n import get_language
        lang = get_language()
        entrant = (user_id, nickname)
        if entrant in self.lucky_draw_entrants:
            if lang == "en":
                return f"{nickname} is already registered for the drawing."
            else:
                return f"{nickname} ลงทะเบียนสิทธิ์รับรางวัลไปก่อนหน้านี้แล้ว"
        
        self.lucky_draw_entrants.append(entrant)
        if lang == "en":
            return f"Added {nickname} to the lucky draw queue."
        else:
            return f"บันทึกชื่อ {nickname} เข้าคิวสุ่มรับรางวัลเรียบร้อยแล้ว"

    def draw_lucky_winner(self, mode: str = "random") -> str:
        """
        จับฉลากสุ่มหาผู้โชคดีจากรายชื่อ
        """
        from core.i18n import get_language
        lang = get_language()
        if not self.lucky_draw_entrants:
            if lang == "en":
                return "No entrants registered for the lucky draw. Type !join to participate."
            else:
                return "ไม่พบผู้ลงทะเบียนลุ้นรับรางวัลในขณะนี้ พิมพ์ !ร่วมกิจกรรม เพื่อเข้าร่วม"
            
        winner_id, winner_nickname = random.choice(self.lucky_draw_entrants)
        self.lucky_draw_entrants.clear() # เคลียร์ประวัติหลังจบเกม
        
        # รางวัลสุ่ม: เพิ่มคะแนนสะสม 300 คะแนน
        self.db.add_points(winner_id, winner_nickname, 300)
        if lang == "en":
            return f"Lucky draw winner is {winner_nickname}! Congratulations! Received a bonus of 300 points."
        else:
            return f"สุ่มประกาศผลผู้โชคดีแล้ว! ผู้ชนะคือคุณ {winner_nickname} ยินดีด้วยครับ! ได้รับโบนัส 300 คะแนน"

    def spin_wheel(self, user_id: str, nickname: str) -> Tuple[str, str]:
        """
        ผู้ชมพิมพ์คำสั่ง !หมุน เพื่อเล่นวงล้อนำโชค
        หักคะแนนผู้เล่น 50 คะแนนเพื่อเล่น
        """
        from core.i18n import get_language
        lang = get_language()
        profile = self.db.get_or_create_profile(user_id, nickname)
        if profile["points"] < 50:
            if lang == "en":
                return f"{nickname} does not have enough points to spin the wheel (needs 50 points)", "sfx_like"
            else:
                return f"{nickname} มีคะแนนไม่เพียงพอสำหรับการหมุนวงล้อนำโชค (ต้องการ 50 คะแนน)", "sfx_like"
            
        # หักค่าหมุนวงล้อ
        self.db.record_purchase(user_id, "หมุนวงล้อนำโชค", 50)
        
        if lang == "en":
            rewards = [
                ("150 bonus points", 150),
                ("300 jackpot points", 300),
                ("20 small reward points", 20),
                ("No reward", 0),
                ("Better luck next time!", 0)
            ]
        else:
            rewards = [
                ("โบนัสคะแนน 150 คะแนน", 150),
                ("รางวัลแจ็คพ็อต 300 คะแนน", 300),
                ("รางวัลเล็ก 20 คะแนน", 20),
                ("ไม่ได้รางวัล (เกลือ)", 0),
                ("เสียดายจัง ลองใหม่อีกครั้งนะ", 0)
            ]
        
        reward_name, points_awarded = random.choice(rewards)
        sfx_to_play = "sfx_gift" if points_awarded > 0 else "sfx_like"
        
        if points_awarded > 0:
            self.db.add_points(user_id, nickname, points_awarded)
            if lang == "en":
                msg = f"{nickname} spun the wheel and won {reward_name}! Total points increased."
            else:
                msg = f"{nickname} ทำการหมุนวงล้อนำโชคและได้รับ {reward_name}! ยอดสุทธิสะสมเพิ่มขึ้น"
        else:
            if lang == "en":
                msg = f"{nickname} spun the wheel and got... {reward_name}!"
            else:
                msg = f"{nickname} หมุนวงล้อนำโชคและได้รับ... {reward_name}!"
            
        return msg, sfx_to_play

    def handle_viewer_attempt(self, user_id: str, nickname: str, message: str) -> Optional[Tuple[str, str]]:
        """
        ประมวลผลคำตอบ/ข้อความของผู้ชมในขณะที่มีเกมรันอยู่
        คืนค่า: Tuple(ข้อความเสียงประกาศ, คีย์เสียงเอฟเฟกต์) หากเกมจบลง
        """
        if not self.active_game:
            return None

        from core.i18n import get_language
        lang = get_language()
        clean_msg = message.strip()
        
        # Supports both !ทาย and !guess / !ตอบ and !answer
        is_guess = clean_msg.startswith("!ทาย") or clean_msg.startswith("!guess")
        guess_val = clean_msg.replace("!ทาย", "").replace("!guess", "").strip()
        
        is_answer = clean_msg.startswith("!ตอบ") or clean_msg.startswith("!answer")
        answer_val = clean_msg.replace("!ตอบ", "").replace("!answer", "").strip()

        # 1. จัดการคำทายในเกมทายตัวเลข
        if self.active_game == "guess_number" and is_guess:
            try:
                guess = int(guess_val)
                target = self.game_data["target"]
                
                if guess == target:
                    self.active_game = None
                    self.db.add_points(user_id, nickname, 100)
                    if lang == "en":
                        return f"{nickname} guessed {guess} correctly! Received a bonus of 100 points.", "sfx_gift"
                    else:
                        return f"{nickname} ทายเลข {guess} ถูกต้องแล้วครับ! ได้รับโบนัส 100 คะแนน", "sfx_gift"
                elif guess < target:
                    if lang == "en":
                        return f"{nickname} guessed {guess} which is too low", "sfx_comment"
                    else:
                        return f"{nickname} ทายเลข {guess} น้อยเกินไป", "sfx_comment"
                else:
                    if lang == "en":
                        return f"{nickname} guessed {guess} which is too high", "sfx_comment"
                    else:
                        return f"{nickname} ทายเลข {guess} มากเกินไป", "sfx_comment"
            except:
                pass

        # 2. จัดการเกมทายคำ
        elif self.active_game == "guess_word" and is_guess:
            guess_word = guess_val
            target_word = self.game_data["word"]
            
            if guess_word.lower() == target_word.lower():
                self.active_game = None
                self.db.add_points(user_id, nickname, 100)
                if lang == "en":
                    return f"{nickname} guessed '{guess_word}' correctly! Received a bonus of 100 points.", "sfx_gift"
                else:
                    return f"{nickname} ทายคำว่า {guess_word} ถูกต้องแล้วครับ! ได้รับโบนัส 100 คะแนน", "sfx_gift"
            else:
                if lang == "en":
                    return f"{nickname} guessed '{guess_word}' which is incorrect", "sfx_comment"
                else:
                    return f"{nickname} ทายคำว่า {guess_word} ยังไม่ถูกต้อง", "sfx_comment"

        # 3. จัดการตอบคำถาม (Quiz)
        elif self.active_game == "quiz" and is_answer:
            answer = answer_val
            target_answer = self.game_data["a"]
            
            if answer.lower() == target_answer.lower():
                self.active_game = None
                self.db.add_points(user_id, nickname, 100)
                if lang == "en":
                    return f"{nickname} answered '{answer}' correctly! Received a bonus of 100 points.", "sfx_gift"
                else:
                    return f"{nickname} ตอบว่า {answer} ถูกต้องแล้วครับ! ได้รับโบนัส 100 คะแนน", "sfx_gift"
            else:
                if lang == "en":
                    return f"{nickname} answered '{answer}' which is incorrect (Hint: {self.game_data['hint']})", "sfx_comment"
                else:
                    return f"{nickname} ตอบว่า {answer} ยังไม่ถูกต้อง (คำใบ้: {self.game_data['hint']})", "sfx_comment"

        # 4. เกมตอบเร็ว (รันการประมวลผลคำตอบตรงๆ)
        elif self.active_game == "fast_response":
            target = self.game_data["target"]
            if clean_msg.lower() == target.lower():
                self.active_game = None
                self.db.add_points(user_id, nickname, 150)
                if lang == "en":
                    return f"Congratulations to {nickname}! Typed '{clean_msg}' fastest and gets 150 points.", "sfx_gift"
                else:
                    return f"ยินดีด้วยกับคุณ {nickname} พิมพ์คำว่า {clean_msg} ได้เร็วที่สุดรับไปเลย 150 คะแนน", "sfx_gift"

        # 5. กิจกรรมเกมเศรษฐี
        elif self.active_game == "monopoly":
            self.active_game = None
            event_name = self.game_data["event"]
            mod = self.game_data["mod"]
            self.db.add_points(user_id, nickname, mod)
            
            if lang == "en":
                effect_str = "received" if mod >= 0 else "lost"
                sfx = "sfx_gift" if mod >= 0 else "sfx_like"
                return f"Monopoly square landed on {nickname}! {event_name} - {effect_str} {abs(mod)} points.", sfx
            else:
                effect_str = "ได้รับ" if mod >= 0 else "โดนหัก"
                sfx = "sfx_gift" if mod >= 0 else "sfx_like"
                return f"ช่องเศรษฐีตกที่คุณ {nickname}! {event_name} ส่งผลให้{effect_str} {abs(mod)} คะแนน", sfx

        return None
