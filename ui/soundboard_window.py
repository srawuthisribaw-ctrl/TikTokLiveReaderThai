import wx
from typing import Any
from services.soundboard_service import SoundboardService
from accessibility.reader_helper import ReaderHelper

class SoundboardWindow(wx.Frame):
    """
    หน้าต่างแสดงแผงเอฟเฟกต์เสียงตลก (Soundboard Window Frame)
    รองรับการควบคุมผ่านปุ่มคีย์บอร์ด F1 - F10 และนำทาง 100%
    """
    def __init__(self, parent: wx.Window, soundboard_service: SoundboardService, speak_fn: Any, config_path: str):
        super().__init__(parent, title="ซาวด์บอร์ดเอฟเฟกต์เสียงประกอบสตรีม", size=(500, 550))
        self.sfx = soundboard_service
        self.speak_fn = speak_fn
        self.config_path = config_path
        self.reader = ReaderHelper(speak_fn)
        
        self.panel = wx.Panel(self)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        
        # 1. หัวข้อปุ่มลัดและคำแนะนำคีย์บอร์ด
        self.lbl_info = wx.StaticText(self.panel, label="คีย์ลัดเล่นด่วน (ขณะหน้าต่างนี้เปิดโฟกัสอยู่):\nF1=หัวเราะ, F2=ปรบมือ, F3=เชียร์, F4=ว้าว, F5=ตึ่งโป๊ะ, F6=กลองม้วน, F7=ชนะ, F8=แพ้, F9=สุ่มเสียง", style=wx.ALIGN_CENTER)
        self.lbl_info.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.vbox.Add(self.lbl_info, 0, wx.ALL | wx.EXPAND, 10)
        
        # 2. สร้างกริดสำหรับปุ่มเสียงซาวด์บอร์ด (Grid Sizer)
        grid = wx.GridSizer(cols=3, hgap=5, vgap=5)
        
        # รายการเสียงปุ่มในแผง
        self.buttons_list = [
            ("laugh", "ฮาฮาฮา (F1)"),
            ("applause", "ปรบมือ (F2)"),
            ("cheer", "เชียร์ (F3)"),
            ("wow", "ว้าว (F4)"),
            ("rimshot", "ตึ่งโป๊ะ (F5)"),
            ("drumroll", "กลองม้วน (F6)"),
            ("win", "เสียงชนะ (F7)"),
            ("lose", "เสียงแพ้ (F8)"),
            ("shock", "ตกใจ"),
            ("cat", "เสียงแมว"),
            ("dog", "เสียงหมา"),
            ("rooster", "เสียงไก่"),
            ("duck", "เสียงเป็ด"),
            ("gameshow", "เกมโชว์"),
            ("explosion", "ระเบิด"),
            ("slide", "เสียงสไลด์"),
            ("baby_laugh", "หัวเราะเด็ก"),
            ("cheer2", "โห่ร้อง")
        ]
        
        # สร้างปุ่มสำหรับแต่ละเสียง
        for key, label in self.buttons_list:
            btn = wx.Button(self.panel, label=label)
            btn.Bind(wx.EVT_BUTTON, lambda event, k=key: self._on_play_sfx_click(k))
            self.reader.bind_focus_announcement(btn, f"ปุ่มเล่นเสียงเอฟเฟกต์ {label.replace('(F', 'เอฟเฟกต์เอฟ')}")
            grid.Add(btn, 1, wx.EXPAND)
            
        self.vbox.Add(grid, 1, wx.EXPAND | wx.ALL, 10)
        
        # ปุ่มปิด
        self.btn_close = wx.Button(self.panel, label="ปิดหน้าต่างซาวด์บอร์ด (F10)")
        self.btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        self.reader.bind_focus_announcement(self.btn_close, "ปุ่มปิดหน้าต่างซาวด์บอร์ด")
        self.vbox.Add(self.btn_close, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        
        self.panel.SetSizer(self.vbox)
        
        # ผูกปุ่มลัดคีย์บอร์ดที่รันเฉพาะในหน้าต่างนี้ (Local Key Events)
        self.panel.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        
        self.reader.announce_navigation("เปิดหน้าต่างซาวด์บอร์ดเสียงตลกแล้วค่ะ", 8)
        self.apply_theme()

    def _on_play_sfx_click(self, key: str):
        self.sfx.play_sound(key)

    def _on_char_hook(self, event: wx.KeyEvent):
        """วิเคราะห์การกดคีย์ F1 - F10 บนตัวซาวด์บอร์ด"""
        code = event.GetKeyCode()
        
        # แมปคีย์บอร์ด F1 - F10
        key_map = {
            wx.WXK_F1: "laugh",
            wx.WXK_F2: "applause",
            wx.WXK_F3: "cheer",
            wx.WXK_F4: "wow",
            wx.WXK_F5: "rimshot",
            wx.WXK_F6: "drumroll",
            wx.WXK_F7: "win",
            wx.WXK_F8: "lose"
        }
        
        if code in key_map:
            self.sfx.play_sound(key_map[code])
        elif code == wx.WXK_F9:
            # สุ่มเสียง
            self.sfx.play_random_effect()
        elif code == wx.WXK_F10:
            # ปิดซาวด์บอร์ด
            self.Close()
        else:
            event.Skip()

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
            font_size = 15 if large_font else 10
            font = wx.Font(font_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD if large_font else wx.FONTWEIGHT_NORMAL)
            
            # สีธีม
            bg_color = wx.Colour(0, 0, 0) if high_contrast else wx.SystemSettings.GetColour(wx.SYS_COLOUR_FRAMEBK)
            fg_color = wx.Colour(255, 255, 0) if high_contrast else wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
            
            self.SetBackgroundColour(bg_color)
            self.panel.SetBackgroundColour(bg_color)
            self.panel.SetForegroundColour(fg_color)
            
            if large_font:
                self.SetSize((650, 700))
            else:
                self.SetSize((500, 550))
                
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

