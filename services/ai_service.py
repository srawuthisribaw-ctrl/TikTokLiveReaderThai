import json
import requests
import re
from typing import Dict, Any, Optional
from database.db_helper import DatabaseHelper

class AIService:
    """
    บริการจัดการระบบ AI ผู้ช่วยสำหรับสตรีมเมอร์ (สถิติแชทและไลฟ์) 
    และระบบตอบคำถามผู้ชมในช่องแชทแบบเรียลไทม์
    """
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.db = DatabaseHelper()

    def _get_api_config(self) -> tuple[str, str]:
        """ดึง API Key และ Model Name จากไฟล์คอนฟิก"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            ai_cfg = config.get("AI", {})
            return ai_cfg.get("api_key", ""), ai_cfg.get("model_name", "gemini-1.5-flash")
        except Exception:
            return "", "gemini-1.5-flash"

    def answer_streamer_voice_query(self, query: str) -> str:
        """
        ระบบผู้ช่วยสตรีมเมอร์ (Streamer Assistant)
        วิเคราะห์คำถามเกี่ยวกับสถิติและสถานการณ์ปัจจุบันของห้องไลฟ์สด
        """
        stats = self.db.get_summary_statistics()
        
        # เพิ่มยอดไลก์สะสมสมมติหรือจากสถิติ
        # โดยการดึงแถวข้อมูลสถิติ
        total_likes_rows = self.db.execute_query("SELECT SUM(value) as total_l FROM statistics WHERE metric_name = 'likes'")
        try:
            total_likes = int(total_likes_rows[0]["total_l"]) if total_likes_rows and total_likes_rows[0]["total_l"] else 0
        except:
            total_likes = 0

        # ทำความสะอาดประโยคคำถาม
        q = query.strip().lower()

        if any(w in q for w in ("คนดู", "ผู้ชม", "ผู้ชมขณะนี้")):
            return f"ขณะนี้มีผู้ชมสะสมทั้งหมด {stats['total_viewers']} คนค่ะ"
            
        elif any(w in q for w in ("คอมเมนต์", "แชท", "ข้อความ")):
            return f"มีผู้ส่งคอมเมนต์ทั้งหมดในเซสชันนี้ {stats['total_comments']} ข้อความค่ะ"
            
        elif any(w in q for w in ("ไลก์", "ถูกใจ", "ยอดถูกใจ")):
            return f"ยอดไลก์รวมสะสมในห้องสตรีมอยู่ที่ {total_likes} ไลก์ค่ะ"
            
        elif any(w in q for w in ("ของขวัญ", "กิฟต์", "เพชร")):
            return f"ได้รับของขวัญทั้งหมด {stats['total_gifts']} ชิ้น รวมมูลค่า {stats['total_diamonds']} เพชรค่ะ"
            
        elif any(w in q for w in ("ผู้ติดตาม", "คนติดตาม", "ติดตามใหม่")):
            return f"มีผู้กดติดตามช่องเพิ่มใหม่ในวันนี้ {stats['total_followers']} คนค่ะ"
            
        elif any(w in q for w in ("เงิน", "รายได้", "ได้กี่บาท")):
            return f"รายได้สะสมประมาณการจากการสตรีมปัจจุบันอยู่ที่ประมาณ {stats['estimated_earnings_thb']:.2f} บาทค่ะ"
            
        elif any(w in q for w in ("สรุป", "ภาพรวม", "สถิติทั้งหมด")):
            return (
                f"สรุปการไลฟ์สดปัจจุบัน: มีผู้ชม {stats['total_viewers']} ท่าน, "
                f"คอมเมนต์ {stats['total_comments']} ข้อความ, ถูกใจสะสม {total_likes} ครั้ง, "
                f"ได้รับ {stats['total_diamonds']} เพชร และผู้ติดตามเพิ่มใหม่ {stats['total_followers']} คนค่ะ"
            )
        else:
            # ใช้ Gemini API ตอบคำถามสถิติขั้นสูง หากใส่ API Key
            api_key, model = self._get_api_config()
            if api_key:
                system_prompt = (
                    f"คุณคือผู้ช่วย AI ส่วนตัวของคนตาบอด สถิติปัจจุบันของไลฟ์คือ: "
                    f"ผู้ชมสะสม={stats['total_viewers']}, ข้อความคอมเมนต์={stats['total_comments']}, "
                    f"ยอดเพชร={stats['total_diamonds']}, ผู้ติดตามใหม่={stats['total_followers']}, ไลก์={total_likes}. "
                    f"จงตอบคำถามผู้ใช้สั้นๆ กระชับ และเป็นเสียงนำทางที่เป็นมิตรภาษาไทย"
                )
                response = self._call_gemini_api(api_key, model, query, system_prompt)
                if response:
                    return response
            
            return "ฉันสามารถรายงานสถิติสดของห้องได้ค่ะ ลองถามถึง คนดู, คอมเมนต์, ไลก์, ของขวัญ หรือ รายได้ นะคะ"

    def answer_viewer_query(self, nickname: str, question: str) -> str:
        """
        ระบบผู้ช่วยตอบคำถามผู้ชมในแชท (Viewer Assistant)
        รองรับการเชื่อมโยงกับ API ภายนอกหรือมีคำตอบมาตรฐาน
        """
        # ลบคีย์เวิร์ด !ถาม ออกจากเนื้อหาคำถาม
        clean_q = question.replace("!ถาม", "").strip()
        if not clean_q:
            return f"คุณ {nickname} ต้องการถามอะไรบอท AI หรือเปล่าครับ? ตัวอย่าง พิมพ์ !ถาม วันนี้อากาศดีไหม"

        api_key, model = self._get_api_config()
        if api_key:
            system_prompt = (
                f"คุณคือ AI ผู้ช่วยสตรีมเมอร์ คอยบริการตอบคำถามแทนสตรีมเมอร์ในห้อง TikTok Live "
                f"จงตอบคำถามผู้ชมที่ชื่อ {nickname} ด้วยน้ำเสียงสุภาพ เป็นกันเอง ภาษาไทย และสั้นกระชับ (ไม่เกิน 2 ประโยค)"
            )
            response = self._call_gemini_api(api_key, model, clean_q, system_prompt)
            if response:
                return f"AI ตอบคุณ {nickname} ว่า: {response}"

        # หากออฟไลน์ (ไม่มี API Key)
        local_rules = [
            (r"สวัสดี|หวัดดี|hi|hello", f"สวัสดีครับคุณ {nickname} ยินดีต้อนรับสู่สตรีม ขอให้สนุกกับการรับชมครับ"),
            (r"เหนื่อยไหม|เป็นยังไงบ้าง", f"เพื่อความบันเทิงของคุณผู้ชมทุกคน สตรีมเมอร์และทีมงานเต็มที่เสมอครับ!"),
            (r"เล่นเกม|เกมอะไร", f"ขณะนี้มีกิจกรรมเกมสนุกๆ ลองพิมพ์ !ช่วยเหลือ เพื่อดูวิธีเล่นและสะสมคะแนนได้เลยครับ"),
            (r"ชื่ออะไร|ใครตอบ", f"ผมคือระบบ AI ผู้ช่วยสตรีมเมอร์ คอยดูแลตอบคำถามผู้ชมอัตโนมัติครับ"),
            (r"สภาพอากาศ|ร้อนไหม", f"ขณะนี้ระบบ AI ทำงานในโหมดออฟไลน์ หากอยากให้อ่านสภาพอากาศสด รบกวนให้สตรีมเมอร์ใส่ API Key ในระบบเพื่อเชื่อมต่อด้วยนะครับ")
        ]

        for pattern, response_text in local_rules:
            if re.search(pattern, clean_q, re.IGNORECASE):
                return response_text

        return f"คุณ {nickname} ถามว่า: {clean_q} (บอทผู้ช่วยตอบ: บันทึกคำถามเข้าระบบแล้วครับ ขอบคุณสำหรับคอมเมนต์ครับ!)"

    def _call_gemini_api(self, api_key: str, model_name: str, prompt: str, system_instruction: str) -> Optional[str]:
        """
        เรียกใช้ HTTP API ของ Google Gemini โดยตรงโดยไม่ต้องใช้ SDK ภายนอก
        ป้องกันประเด็นความปลอดภัยและความยากในการติดตั้ง package
        """
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {"text": system_instruction}
                ]
            },
            "generationConfig": {
                "maxOutputTokens": 150,
                "temperature": 0.7
            }
        }

        try:
            # ใช้ Timeout 5.0 วินาที เพื่อไม่ให้แชทสะสมหน่วง
            response = requests.post(url, headers=headers, json=payload, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                # แกะค่า text จากโครงสร้าง response ของ Gemini
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
            print(f"Gemini API Error Status: {response.status_code}, Body: {response.text}")
        except Exception as e:
            print(f"Failed to call Gemini API: {e}")
        return None
