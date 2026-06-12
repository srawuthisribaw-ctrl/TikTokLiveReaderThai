import wx
import json
from database.db_helper import DatabaseHelper
from accessibility.reader_helper import ReaderHelper
from typing import Dict, Any, List

class StatsWindow(wx.Frame):
    """
    หน้าต่างสำหรับสรุปและวิเคราะห์ผลลัพธ์การไลฟ์สด (Live Stats & Leaderboards)
    ออกแบบให้จัดระบบการขยายตัวอักษรและพูดข้อมูลสะท้อนกลับเพื่อให้สอดคล้องกับตัวอ่านหน้าจอ
    """
    def __init__(self, parent: wx.Window, config_path: str, speak_fn: Any):
        super().__init__(parent, title="สรุปสถิติจำลองการไลฟ์สดและผู้สนับสนุน", size=(500, 600))
        self.config_path = config_path
        self.speak_fn = speak_fn
        self.db = DatabaseHelper()
        self.reader = ReaderHelper(speak_fn)
        
        self.panel = wx.Panel(self)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        
        # 1. ข้อความหัวเรื่องหน้าต่าง
        self.lbl_title = wx.StaticText(self.panel, label="สรุปข้อมูลสถิติช่อง TikTok Live", style=wx.ALIGN_CENTER)
        self.lbl_title.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.vbox.Add(self.lbl_title, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        
        # 2. รายการข้อมูลสรุปไลฟ์
        self.vbox.Add(wx.StaticText(self.panel, label="ภาพรวมและรายรับจากเพชรสะสม:"), 0, wx.ALL, 5)
        self.list_summary = wx.ListBox(self.panel, style=wx.LB_SINGLE)
        self.reader.bind_focus_announcement(self.list_summary, "รายการประวัติสรุปสถิติภาพรวมไลฟ์สด กดลูกศรลงเพื่ออ่านข้อมูล")
        self.vbox.Add(self.list_summary, 1, wx.EXPAND | wx.ALL, 5)
        
        # 3. ตารางผู้สนับสนุนสูงสุด
        self.vbox.Add(wx.StaticText(self.panel, label="อันดับผู้สนับสนุนสูงสุดประจำสตรีม (Fanclub Leaderboards):"), 0, wx.ALL, 5)
        self.list_leaderboard = wx.ListBox(self.panel, style=wx.LB_SINGLE)
        self.reader.bind_focus_announcement(self.list_leaderboard, "รายการอันดับแฟนคลับผู้สนับสนุนสูงสุดสามอันดับแรก")
        self.vbox.Add(self.list_leaderboard, 1, wx.EXPAND | wx.ALL, 5)
        
        # ปุ่มควบคุมปิด
        self.btn_close = wx.Button(self.panel, label="ปิดหน้าต่างสถิติ")
        self.btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        self.reader.bind_focus_announcement(self.btn_close, "ปุ่มปิดหน้าต่างสถิติ ย้อนกลับสู่หน้าจอหลัก")
        self.vbox.Add(self.btn_close, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        
        self.panel.SetSizer(self.vbox)
        
        # โหลดข้อมูลจริงเข้ามาแสดงผล
        self._load_live_stats()
        self.apply_theme()
        
        # ประกาศหน้าจอด่วนเพื่อประโยชน์ของคนตาบอดเมื่อหน้าจอโผล่
        wx.CallAfter(lambda: self.reader.announce_navigation("เปิดหน้าต่างสถิติและคะแนนผู้สนับสนุนแล้วค่ะ", 8))

    def _load_live_stats(self):
        """ดึงข้อมูลสถิติล่าสุดจาก SQLite และป้อนเข้า List Box"""
        stats = self.db.get_summary_statistics()
        
        # คำนวณถูกใจสะสม
        total_likes_rows = self.db.execute_query("SELECT SUM(value) as total_l FROM statistics WHERE metric_name = 'likes'")
        try:
            total_likes = int(total_likes_rows[0]["total_l"]) if total_likes_rows and total_likes_rows[0]["total_l"] else 0
        except:
            total_likes = 0

        # ป้อนลงรายการสรุป
        summary_items = [
            f"ยอดผู้ชมสะสม: {stats['total_viewers']} คน",
            f"ข้อความคอมเมนต์รวม: {stats['total_comments']} แชท",
            f"จำนวนของขวัญที่ได้รับ: {stats['total_gifts']} ชิ้น",
            f"เพชรสะสม (Diamonds): {stats['total_diamonds']} เม็ด",
            f"ผู้กดติดตามใหม่: {stats['total_followers']} คน",
            f"ยอดกดถูกใจรวม: {total_likes} ไลก์",
            f"รายได้ประมาณจากการสตรีม: {stats['estimated_earnings_thb']:.2f} บาท"
        ]
        self.list_summary.Set(summary_items)
        
        # โหลดลีดเดอร์บอร์ดคนดูสูงสุด 5 อันดับแรก
        top_viewers = self.db.get_top_viewers(5)
        leader_items = []
        for idx, viewer in enumerate(top_viewers):
            leader_items.append(
                f"อันดับที่ {idx + 1}: {viewer['nickname']} (สะสม {viewer['points']} คะแนน, เลเวล {viewer['level']})"
            )
        
        if not leader_items:
            leader_items = ["ยังไม่มีการจัดอันดับสะสมคะแนนคนดู"]
        self.list_leaderboard.Set(leader_items)

    def apply_theme(self):
        """สลับและใช้งานการตั้งค่าหน้าจอและขนาดตัวอักษรเพื่อผู้มีปัญหาสายตา"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            
            acc = cfg.get("Accessibility", {})
            self.reader.set_advanced_blind_mode(acc.get("advanced_blind_mode", False))
            self.reader.set_speak_navigation(acc.get("speak_navigation", False))
            self.reader.set_tts_mode(cfg.get("TTS", {}).get("mode", "nvda"))
            
            high_contrast = acc.get("high_contrast", False)
            large_font = acc.get("large_font", False)
            
            # ปรับแต่งขนาดตัวอักษร
            font_size = 16 if large_font else 11
            font = wx.Font(font_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD if large_font else wx.FONTWEIGHT_NORMAL)
            
            # สีธีม
            bg_color = wx.Colour(0, 0, 0) if high_contrast else wx.SystemSettings.GetColour(wx.SYS_COLOUR_FRAMEBK)
            fg_color = wx.Colour(255, 255, 0) if high_contrast else wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
            
            self.SetBackgroundColour(bg_color)
            self.panel.SetBackgroundColour(bg_color)
            self.panel.SetForegroundColour(fg_color)
            
            if large_font:
                self.SetSize((650, 750))
            else:
                self.SetSize((500, 600))
                
            self._apply_theme_to_child_controls(self.panel, font, bg_color, fg_color)
            self.panel.Layout()
            self.Layout()
        except Exception as e:
            print(f"Apply theme error: {e}")

    def _apply_theme_to_child_controls(self, parent: wx.Window, font: wx.Font, bg: wx.Colour, fg: wx.Colour):
        for child in parent.GetChildren():
            child.SetFont(font)
            if not isinstance(child, wx.CheckBox):
                child.SetBackgroundColour(bg)
                child.SetForegroundColour(fg)
            if child.GetChildren():
                self._apply_theme_to_child_controls(child, font, bg, fg)

