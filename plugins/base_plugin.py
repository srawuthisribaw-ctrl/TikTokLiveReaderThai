from typing import Any

class BasePlugin:
    """
    คลาสแม่แบบสำหรับสร้างระบบปลั๊กอินเพิ่มเติม (Plugin Architecture)
    ผู้พัฒนาสามารถสืบทอดคลาสนี้และจัดวางไฟล์ในโฟลเดอร์ plugins/
    เพื่อเพิ่มสตรีมเกม, บอทตอบคำถาม, หรือระบบเสียงใหม่ๆ โดยไม่ต้องเปลี่ยนโค้ดหลัก
    """
    def __init__(self):
        self.name = "ปลั๊กอินเริ่มต้น"
        self.description = "คำอธิบายปลั๊กอิน"
        self.author = "ผู้พัฒนา"
        self.version = "1.0.0"
        self.enabled = True

    def on_load(self, manager: Any):
        """เรียกใช้เมื่อโปรแกรมเปิดและโหลดปลั๊กอินขึ้นระบบ"""
        pass

    def on_unload(self):
        """เรียกใช้เมื่อปิดใช้งานปลั๊กอิน"""
        pass

    def on_comment(self, user_id: str, nickname: str, comment: str) -> None:
        """เรียกใช้เมื่อมีข้อความแชทใหม่ใน TikTok Live"""
        pass

    def on_gift(self, user_id: str, nickname: str, gift_name: str, count: int, diamonds: int) -> None:
        """เรียกใช้เมื่อได้รับของขวัญ"""
        pass

    def on_join(self, user_id: str, nickname: str) -> None:
        """เรียกใช้เมื่อมีผู้ชมใหม่เข้ามาในไลฟ์"""
        pass

    def on_like(self, user_id: str, nickname: str, total_likes: int) -> None:
        """เรียกใช้เมื่อมีการกดไลค์ในระบบ"""
        pass

    def on_share(self, user_id: str, nickname: str) -> None:
        """เรียกใช้เมื่อมีคนแชร์ลิงก์ไลฟ์สด"""
        pass

    def on_tick(self) -> None:
        """เรียกใช้ทุกๆ 1 วินาทีผ่านระบบ Timer ของโปรแกรมหลัก"""
        pass
