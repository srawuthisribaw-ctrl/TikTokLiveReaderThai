import wx
import json
import os
from typing import Dict, Any, List
from accessibility.reader_helper import ReaderHelper

class SettingsDialog(wx.Dialog):
    """
    หน้าต่างตั้งค่าการทำงานของโปรแกรมหลัก (Settings Dialog)
    รองรับการควบคุมผ่านแป้นพิมพ์ 100% พร้อมตัวควบคุมมิกเซอร์เสียง (Mixer Volume) และ TTS ตลก
    """
    def __init__(self, parent: wx.Window, config_path: str, speak_fn: Any):
        super().__init__(parent, title="ตั้งค่าระบบหลัก", size=(600, 700))
        self.config_path = config_path
        self.speak_fn = speak_fn
        self.reader = ReaderHelper(speak_fn)
        
        # โหลดค่าคอนฟิกปัจจุบัน
        self.config_data = self._load_config()

        # สร้างแผงควบคุมหลัก
        self.panel = wx.Panel(self)
        self.notebook = wx.Notebook(self.panel)
        
        # แท็บย่อย
        self.tab_reading = wx.Panel(self.notebook)
        self.tab_tts = wx.Panel(self.notebook)
        self.tab_sfx = wx.Panel(self.notebook)
        self.tab_mixer = wx.Panel(self.notebook)  # แท็บที่ 5 ใหม่
        self.tab_ai = wx.Panel(self.notebook)
        
        self.notebook.AddPage(self.tab_reading, "การอ่านข้อมูล")
        self.notebook.AddPage(self.tab_tts, "เสียงอ่าน (TTS)")
        self.notebook.AddPage(self.tab_sfx, "เสียงประกอบ (SFX)")
        self.notebook.AddPage(self.tab_mixer, "มิกเซอร์ระดับเสียง")
        self.notebook.AddPage(self.tab_ai, "ผู้ช่วย AI")

        # บูตหน้าจอของแต่ละแท็บ
        self._init_reading_tab()
        self._init_tts_tab()
        self._init_sfx_tab()
        self._init_mixer_tab()
        self._init_ai_tab()
        
        # ผูกเหตุการณ์เมื่อผู้ใช้สลับแท็บ
        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self._on_tab_changed)

        # ออกแบบโครงสร้างปุ่มตกลง/ยกเลิก
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)
        
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_save = wx.Button(self.panel, label="บันทึกการตั้งค่า")
        self.btn_cancel = wx.Button(self.panel, id=wx.ID_CANCEL, label="ยกเลิก")
        
        self.btn_save.Bind(wx.EVT_BUTTON, self._on_save_click)
        self.reader.bind_focus_announcement(self.btn_save, "ปุ่มบันทึกการตั้งค่า กดตกลงเพื่อใช้งาน")
        self.reader.bind_focus_announcement(self.btn_cancel, "ปุ่มยกเลิกปิดหน้าต่างการตั้งค่า")
        
        btn_sizer.Add(self.btn_save, 1, wx.ALL | wx.EXPAND, 5)
        btn_sizer.Add(self.btn_cancel, 1, wx.ALL | wx.EXPAND, 5)
        
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.panel.SetSizer(sizer)
        
        # ตั้งค่าฟอนต์และการเข้าถึงระดับสูง
        self.apply_theme()

    def _load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _init_reading_tab(self):
        vbox = wx.BoxSizer(wx.VERTICAL)
        cfg = self.config_data.get("Settings", {})
        
        self.chk_comment = wx.CheckBox(self.tab_reading, label="อ่านคอมเมนต์สดในแชท (Chat)")
        self.chk_join = wx.CheckBox(self.tab_reading, label="อ่านแจ้งเตือนเมื่อคนเข้าไลฟ์ (Join)")
        self.chk_gift = wx.CheckBox(self.tab_reading, label="อ่านแจ้งเตือนของขวัญ (Gift)")
        self.chk_like = wx.CheckBox(self.tab_reading, label="อ่านแจ้งเตือนถูกใจ (Like)")
        self.chk_share = wx.CheckBox(self.tab_reading, label="อ่านแจ้งเตือนแชร์ไลฟ์ (Share)")
        self.chk_vip = wx.CheckBox(self.tab_reading, label="อ่านแจ้งเตือนสมัครสมาชิก VIP (Sub)")
        self.chk_emoji = wx.CheckBox(self.tab_reading, label="แปลรูปภาพและอีโมจิเป็นคำพูด (Emoji)")

        self.chk_comment.SetValue(cfg.get("read_comment", True))
        self.chk_join.SetValue(cfg.get("read_join", False))
        self.chk_gift.SetValue(cfg.get("read_gift", True))
        self.chk_like.SetValue(cfg.get("read_like", False))
        self.chk_share.SetValue(cfg.get("read_share", True))
        self.chk_vip.SetValue(cfg.get("read_vip", True))
        self.chk_emoji.SetValue(cfg.get("read_emoji", True))

        self.reader.bind_checkbox_announcement(self.chk_comment, "อ่านคอมเมนต์สดในแชท")
        self.reader.bind_checkbox_announcement(self.chk_join, "อ่านแจ้งเตือนคนเข้าห้อง")
        self.reader.bind_checkbox_announcement(self.chk_gift, "อ่านแจ้งเตือนของขวัญ")
        self.reader.bind_checkbox_announcement(self.chk_like, "อ่านแจ้งเตือนการกดถูกใจ")
        self.reader.bind_checkbox_announcement(self.chk_share, "อ่านแจ้งเตือนแชร์ไลฟ์สด")
        self.reader.bind_checkbox_announcement(self.chk_vip, "อ่านแจ้งเตือนสมัครสมาชิกช่อง")
        self.reader.bind_checkbox_announcement(self.chk_emoji, "แปลอีโมจิและเครื่องหมายสัญลักษณ์")

        for chk in (self.chk_comment, self.chk_join, self.chk_gift, self.chk_like, self.chk_share, self.chk_vip, self.chk_emoji):
            vbox.Add(chk, 0, wx.ALL, 5)

        vbox.Add(wx.StaticText(self.tab_reading, label="คำที่ห้ามอ่านออกเสียง (คั่นด้วยเครื่องหมายจุลภาค ,):"), 0, wx.ALL, 5)
        blacklist_list = cfg.get("blacklist", [])
        self.txt_blacklist = wx.TextCtrl(self.tab_reading, value=",".join(blacklist_list))
        self.reader.bind_textctrl_announcement(self.txt_blacklist, "คำกรองแบล็กลิสต์คำห้ามพูด")
        vbox.Add(self.txt_blacklist, 0, wx.ALL | wx.EXPAND, 5)

        self.tab_reading.SetSizer(vbox)

    def _init_tts_tab(self):
        vbox = wx.BoxSizer(wx.VERTICAL)
        cfg = self.config_data.get("TTS", {})
        
        # 1. การเลือกเอนจินหลัก
        vbox.Add(wx.StaticText(self.tab_tts, label="เลือกตัวอ่านเสียงหลัก (TTS Engine):"), 0, wx.ALL, 5)
        self.choice_engine = wx.Choice(self.tab_tts, choices=[
            "NVDA Screen Reader", 
            "JAWS Screen Reader",
            "SAPI5 (Windows standard)", 
            "Windows OneCore (SpeechSynthesizer)", 
            "Google Translate TTS",
            "Microsoft Edge Online TTS"
        ])
        
        engine_mode = cfg.get("mode", "nvda")
        engine_map = {"nvda": 0, "jaws": 1, "sapi5": 2, "onecore": 3, "google": 4, "edge": 5}
        self.choice_engine.SetSelection(engine_map.get(engine_mode, 0))
        self.choice_engine.Bind(wx.EVT_CHOICE, self._on_engine_change)
        self.reader.bind_choice_announcement(self.choice_engine, "เลือกเครื่องมืออ่านเสียง")
        vbox.Add(self.choice_engine, 0, wx.EXPAND | wx.ALL, 5)

        # 2. รายชื่อเสียงพูดที่มีในระบบ
        vbox.Add(wx.StaticText(self.tab_tts, label="เสียงพูดที่ต้องการในระบบ (Voice Selected):"), 0, wx.ALL, 5)
        
        from tts.tts_engine import TTSEngine
        temp_engine = TTSEngine()
        self.available_voices = temp_engine.get_available_voices()
        
        voice_choices = [v["name"] for v in self.available_voices]
        self.choice_voice = wx.Choice(self.tab_tts, choices=voice_choices)
        self.reader.bind_choice_announcement(self.choice_voice, "เลือกเสียงนักอ่าน")
        
        saved_voice_id = cfg.get("voice_id", "")
        # ค้นหา index จาก ID
        saved_idx = 0
        for i, voice_info in enumerate(self.available_voices):
            if voice_info["id"] == saved_voice_id:
                saved_idx = i
                break
        self.choice_voice.SetSelection(saved_idx)
        vbox.Add(self.choice_voice, 0, wx.EXPAND | wx.ALL, 5)

        # 3. แถบความเร็ว
        speed_val = cfg.get("speed", 0)
        self.lbl_speed = wx.StaticText(self.tab_tts, label=f"ความเร็วการอ่านเสียง (Speed): {speed_val}")
        self.sld_speed = wx.Slider(self.tab_tts, value=speed_val, minValue=-10, maxValue=10, style=wx.SL_HORIZONTAL)
        self.reader.bind_slider_announcement(self.sld_speed, "ความเร็วการอ่านเสียง")
        self.sld_speed.Bind(wx.EVT_SLIDER, lambda e: self.lbl_speed.SetLabel(f"ความเร็วการอ่านเสียง (Speed): {self.sld_speed.GetValue()}"))
        vbox.Add(self.lbl_speed, 0, wx.ALL, 5)
        vbox.Add(self.sld_speed, 0, wx.EXPAND | wx.ALL, 5)

        # 4. โหมดเสียงสังเคราะห์ตลก
        vbox.Add(wx.StaticText(self.tab_tts, label="รูปแบบเสียงสังเคราะห์ตลก (Funny TTS Style):"), 0, wx.ALL, 5)
        self.choice_funny_style = wx.Choice(self.tab_tts, choices=[
            "ปกติ (Normal)", "หุ่นยนต์ (Robot)", "เด็ก (Child)", "คนแก่ (Old)", "พูดเร็ว (Fast)", "พูดช้า (Slow)", "ตลกสูง (Funny)"
        ])
        funny_style = cfg.get("funny_style", "normal")
        funny_map = {"normal": 0, "robot": 1, "child": 2, "old": 3, "fast": 4, "slow": 5, "funny": 6}
        self.choice_funny_style.SetSelection(funny_map.get(funny_style, 0))
        self.reader.bind_choice_announcement(self.choice_funny_style, "เลือกรูปแบบความเพี้ยนเสียงตลก")
        vbox.Add(self.choice_funny_style, 0, wx.EXPAND | wx.ALL, 5)

        # 5. ความดังเสียงพูดรวม
        vol_val = int(cfg.get("volume", 1.0) * 100)
        self.lbl_vol = wx.StaticText(self.tab_tts, label=f"ความดังระดับเสียงพูด (Volume Boost): {vol_val}%")
        self.sld_vol = wx.Slider(self.tab_tts, value=vol_val, minValue=0, maxValue=150, style=wx.SL_HORIZONTAL)
        self.reader.bind_slider_announcement(self.sld_vol, "ความดังระดับเสียงพูด", "เปอร์เซ็นต์")
        self.sld_vol.Bind(wx.EVT_SLIDER, lambda e: self.lbl_vol.SetLabel(f"ความดังระดับเสียงพูด (Volume Boost): {self.sld_vol.GetValue()}%"))
        vbox.Add(self.lbl_vol, 0, wx.ALL, 5)
        vbox.Add(self.sld_vol, 0, wx.EXPAND | wx.ALL, 5)

        self.tab_tts.SetSizer(vbox)
        self._update_tts_controls_state()

    def _on_engine_change(self, event: wx.Event):
        self._update_tts_controls_state()
        event.Skip()

    def _update_tts_controls_state(self):
        idx = self.choice_engine.GetSelection()
        is_manual_sapi = idx in (2, 3, 5)  # SAPI5, OneCore, Edge
        self.choice_voice.Enable(is_manual_sapi)
        self.sld_speed.Enable(is_manual_sapi)
        self.choice_funny_style.Enable(is_manual_sapi)

    def _init_sfx_tab(self):
        vbox = wx.BoxSizer(wx.VERTICAL)
        cfg = self.config_data.get("SFX", {})

        master_vol = int(cfg.get("master_volume", 1.0) * 100)
        self.lbl_master_vol = wx.StaticText(self.tab_sfx, label=f"ความดังเสียงเอฟเฟกต์รวม (Master SFX Volume): {master_vol}%")
        self.sld_master_vol = wx.Slider(self.tab_sfx, value=master_vol, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL)
        self.reader.bind_slider_announcement(self.sld_master_vol, "ความดังเสียงเอฟเฟกต์รวม", "เปอร์เซ็นต์")
        self.sld_master_vol.Bind(wx.EVT_SLIDER, lambda e: self.lbl_master_vol.SetLabel(f"ความดังเสียงเอฟเฟกต์รวม (Master SFX Volume): {self.sld_master_vol.GetValue()}%"))
        
        vbox.Add(self.lbl_master_vol, 0, wx.ALL, 5)
        vbox.Add(self.sld_master_vol, 0, wx.EXPAND | wx.ALL, 5)

        vbox.Add(wx.StaticText(self.tab_sfx, label="รายชื่อไฟล์เสียงประกอบเหตุการณ์ปัจจุบัน:"), 0, wx.ALL, 5)
        self.list_sfx = wx.ListBox(self.tab_sfx, choices=[
            f"เสียงคนเข้าไลฟ์: {cfg.get('sfx_join', 'welcome.wav')}",
            f"เสียงแชทคอมเมนต์: {cfg.get('sfx_comment', 'comment.wav')}",
            f"เสียงส่งของขวัญ: {cfg.get('sfx_gift', 'gift.wav')}",
            f"เสียงส่งไลก์: {cfg.get('sfx_like', 'like.wav')}",
            f"เสียงแชร์สตรีม: {cfg.get('sfx_share', 'share.wav')}"
        ])
        self.reader.bind_focus_announcement(self.list_sfx, "รายการสถิติไฟล์เสียงแจ้งเตือนเอฟเฟกต์")
        vbox.Add(self.list_sfx, 1, wx.EXPAND | wx.ALL, 5)
        
        self.tab_sfx.SetSizer(vbox)

    def _init_mixer_tab(self):
        """บูตแสดงผลแถบควบคุมเสียงมิกเซอร์ 6 ช่อง พร้อมโปรไฟล์เสียงสัญจร"""
        vbox = wx.BoxSizer(wx.VERTICAL)
        cfg = self.config_data.get("Mixer", {})
        
        # 1. โปรไฟล์เสียง
        vbox.Add(wx.StaticText(self.tab_mixer, label="เลือกโปรไฟล์มิกเซอร์เสียง (Mixer Profile):"), 0, wx.ALL, 5)
        self.choice_profile = wx.Choice(self.tab_mixer, choices=[
            "โหมดไลฟ์ปกติ (Normal)",
            "โหมดเล่นเกม (Game)",
            "โหมดร้องเพลง (Singing)",
            "โหมดกิจกรรมพิเศษ (Special)"
        ])
        profile_map = {"normal": 0, "game": 1, "singing": 2, "special": 3}
        self.choice_profile.SetSelection(profile_map.get(cfg.get("active_profile", "normal"), 0))
        self.choice_profile.Bind(wx.EVT_CHOICE, self._on_profile_change)
        self.reader.bind_choice_announcement(self.choice_profile, "เลือกโปรไฟล์ปรับแต่งระดับเสียง")
        vbox.Add(self.choice_profile, 0, wx.EXPAND | wx.ALL, 5)

        # 2. ปรับแต่งระดับเสียงแยกช่อง
        active_profile = cfg.get("active_profile", "normal")
        volumes = cfg.get("profiles", {}).get(active_profile, {})

        self.sliders = {}
        channels = [
            ("music", "เครื่องเล่นเพลง (Music)"),
            ("comment", "ข้อความคอมเมนต์ (Comment)"),
            ("gift", "แจ้งเตือนของขวัญ (Gift)"),
            ("sfx", "ซาวด์บอร์ดเอฟเฟกต์ (SFX)"),
            ("tts", "เสียงระบบอ่านหลัก (TTS)"),
            ("ai", "เสียงตอบกลับ AI (AI)")
        ]
        
        for ch_key, ch_label in channels:
            vol_val = int(volumes.get(ch_key, 1.0) * 100)
            lbl = wx.StaticText(self.tab_mixer, label=f"ความดังช่อง {ch_label}: {vol_val}%")
            sld = wx.Slider(self.tab_mixer, value=vol_val, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL)
            
            # ป้องกันปัญหา Lambda ผูกค่าล่าสุดใน Loop
            sld.Bind(wx.EVT_SLIDER, lambda e, k=ch_key, l=lbl, s=sld, label_text=ch_label: self._on_mixer_scroll(k, l, s, label_text))
            self.reader.bind_slider_announcement(sld, f"มิกเซอร์เสียง {ch_label}", "เปอร์เซ็นต์")
            
            vbox.Add(lbl, 0, wx.ALL, 3)
            vbox.Add(sld, 0, wx.EXPAND | wx.ALL, 3)
            self.sliders[ch_key] = (sld, lbl, ch_label)

        self.tab_mixer.SetSizer(vbox)

    def _on_profile_change(self, event: wx.Event):
        """เมื่อผู้ใช้สลับโปรไฟล์มิกเซอร์ ให้ดึงความดังของโปรไฟล์นั้นมาแสดงผลทันที"""
        idx = self.choice_profile.GetSelection()
        profile_map = {0: "normal", 1: "game", 2: "singing", 3: "special"}
        p_key = profile_map[idx]
        
        profiles = self.config_data.get("Mixer", {}).get("profiles", {})
        volumes = profiles.get(p_key, {})
        
        for ch_key, (sld, lbl, ch_label) in self.sliders.items():
            vol_val = int(volumes.get(ch_key, 1.0) * 100)
            sld.SetValue(vol_val)
            lbl.SetLabel(f"ความดังช่อง {ch_label}: {vol_val}%")
            
        self.speak_fn(f"ดึงระดับเสียงสำหรับโปรไฟล์ {self.choice_profile.GetStringSelection()} แล้วค่ะ", 8)
        event.Skip()

    def _on_mixer_scroll(self, ch_key: str, lbl: wx.StaticText, sld: wx.Slider, ch_label: str):
        val = sld.GetValue()
        lbl.SetLabel(f"ความดังช่อง {ch_label}: {val}%")

    def _init_ai_tab(self):
        vbox = wx.BoxSizer(wx.VERTICAL)
        cfg = self.config_data.get("AI", {})

        vbox.Add(wx.StaticText(self.tab_ai, label="Gemini API Key สำหรับผู้ช่วย AI (ข้ามเพื่อใช้ออฟไลน์):"), 0, wx.ALL, 5)
        self.txt_apikey = wx.TextCtrl(self.tab_ai, value=cfg.get("api_key", ""), style=wx.TE_PASSWORD)
        self.reader.bind_textctrl_announcement(self.txt_apikey, "ช่องใส่รหัสเจมินี่ เอพีไอ คีย์")
        vbox.Add(self.txt_apikey, 0, wx.EXPAND | wx.ALL, 5)

        vbox.Add(wx.StaticText(self.tab_ai, label="เวอร์ชัน Model AI:"), 0, wx.ALL, 5)
        self.choice_model = wx.Choice(self.tab_ai, choices=["gemini-1.5-flash", "gemini-1.5-pro"])
        self.reader.bind_choice_announcement(self.choice_model, "เลือกขนาดโมเดลปัญญาประดิษฐ์")
        self.choice_model.SetStringSelection(cfg.get("model_name", "gemini-1.5-flash"))
        vbox.Add(self.choice_model, 0, wx.EXPAND | wx.ALL, 5)

        self.chk_streamer_ai = wx.CheckBox(self.tab_ai, label="เปิดระบบวิเคราะห์เสียงตอบคำถามของสตรีมเมอร์ (Ctrl+Shift+A)")
        self.chk_viewer_ai = wx.CheckBox(self.tab_ai, label="เปิดระบบผู้ช่วย AI โต้ตอบตอบข้อสงสัยของผู้ชมสด (พิมพ์ !ถาม)")
        self.chk_announce_stats = wx.CheckBox(self.tab_ai, label="เปิดระบบการอ่านรายงานสถิติของสตรีมเมอร์ทุกๆ 5 นาที (รายงานผู้จัดไลฟ์)")
        
        self.chk_streamer_ai.SetValue(cfg.get("streamer_assistant_enabled", True))
        self.chk_viewer_ai.SetValue(cfg.get("viewer_assistant_enabled", True))
        self.chk_announce_stats.SetValue(cfg.get("announce_stats_enabled", True))
        
        self.reader.bind_checkbox_announcement(self.chk_streamer_ai, "ระบบสืบค้นสถิติผู้ช่วยสตรีมเมอร์")
        self.reader.bind_checkbox_announcement(self.chk_viewer_ai, "ระบบตอบคำถามแฟนคลับอัตโนมัติด้วยปัญญาประดิษฐ์")
        self.reader.bind_checkbox_announcement(self.chk_announce_stats, "เปิดการประกาศสถิติผู้จัดไลฟ์ทุกห้านาที")
        
        vbox.Add(self.chk_streamer_ai, 0, wx.ALL, 5)
        vbox.Add(self.chk_viewer_ai, 0, wx.ALL, 5)
        vbox.Add(self.chk_announce_stats, 0, wx.ALL, 5)

        self.tab_ai.SetSizer(vbox)

    def _on_tab_changed(self, event: wx.Event):
        idx = event.GetSelection()
        tab_name = self.notebook.GetPageText(idx)
        self.reader.announce_navigation(f"สลับหน้าแท็บ {tab_name} เรียบร้อยแล้วค่ะ", 8)
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
            font_size = 16 if large_font else 11
            font = wx.Font(font_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD if large_font else wx.FONTWEIGHT_NORMAL)
            
            # สีธีม
            bg_color = wx.Colour(0, 0, 0) if high_contrast else wx.SystemSettings.GetColour(wx.SYS_COLOUR_FRAMEBK)
            fg_color = wx.Colour(255, 255, 0) if high_contrast else wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
            
            self.SetBackgroundColour(bg_color)
            self.panel.SetBackgroundColour(bg_color)
            self.panel.SetForegroundColour(fg_color)
            
            if large_font:
                self.SetSize((750, 850))
            else:
                self.SetSize((600, 700))
                
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


    def _on_save_click(self, event: wx.Event):
        # 1. แท็บการอ่านข้อมูล
        self.config_data["Settings"]["read_comment"] = self.chk_comment.GetValue()
        self.config_data["Settings"]["read_join"] = self.chk_join.GetValue()
        self.config_data["Settings"]["read_gift"] = self.chk_gift.GetValue()
        self.config_data["Settings"]["read_like"] = self.chk_like.GetValue()
        self.config_data["Settings"]["read_share"] = self.chk_share.GetValue()
        self.config_data["Settings"]["read_vip"] = self.chk_vip.GetValue()
        self.config_data["Settings"]["read_emoji"] = self.chk_emoji.GetValue()
        
        bl_text = self.txt_blacklist.GetValue().strip()
        self.config_data["Settings"]["blacklist"] = [w.strip() for w in bl_text.split(",") if w.strip()]

        # 2. แท็บเสียง TTS
        engine_map = {0: "nvda", 1: "jaws", 2: "sapi5", 3: "onecore", 4: "google", 5: "edge"}
        self.config_data["TTS"]["mode"] = engine_map.get(self.choice_engine.GetSelection(), "nvda")
        
        sel_idx = self.choice_voice.GetSelection()
        if 0 <= sel_idx < len(self.available_voices):
            self.config_data["TTS"]["voice_id"] = self.available_voices[sel_idx]["id"]
            self.config_data["TTS"]["voice_index"] = sel_idx
            
        self.config_data["TTS"]["speed"] = self.sld_speed.GetValue()
        self.config_data["TTS"]["volume"] = self.sld_vol.GetValue() / 100.0
        
        funny_map = {0: "normal", 1: "robot", 2: "child", 3: "old", 4: "fast", 5: "slow", 6: "funny"}
        self.config_data["TTS"]["funny_style"] = funny_map.get(self.choice_funny_style.GetSelection(), "normal")

        # 3. แท็บ SFX
        self.config_data["SFX"]["master_volume"] = self.sld_master_vol.GetValue() / 100.0

        # 4. แท็บมิกเซอร์ระดับเสียง
        idx = self.choice_profile.GetSelection()
        profile_map = {0: "normal", 1: "game", 2: "singing", 3: "special"}
        p_key = profile_map[idx]
        self.config_data["Mixer"]["active_profile"] = p_key
        
        for ch_key, (sld, lbl, ch_label) in self.sliders.items():
            self.config_data["Mixer"]["profiles"][p_key][ch_key] = snd_val = sld.GetValue() / 100.0

        # 5. แท็บ AI
        self.config_data["AI"]["api_key"] = self.txt_apikey.GetValue().strip()
        self.config_data["AI"]["model_name"] = self.choice_model.GetStringSelection()
        self.config_data["AI"]["streamer_assistant_enabled"] = self.chk_streamer_ai.GetValue()
        self.config_data["AI"]["viewer_assistant_enabled"] = self.chk_viewer_ai.GetValue()
        self.config_data["AI"]["announce_stats_enabled"] = self.chk_announce_stats.GetValue()

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            self.EndModal(wx.ID_OK)
        except Exception as e:
            wx.MessageBox(f"ไม่สามารถบันทึกการตั้งค่าลงเครื่องได้: {e}", "ข้อผิดพลาด", wx.ICON_ERROR)
