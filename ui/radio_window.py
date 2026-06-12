import wx
import os
from typing import Dict, Any, List
from services.radio_service import RadioService
from accessibility.reader_helper import ReaderHelper

class RadioWindow(wx.Frame):
    """
    หน้าต่างสำหรับจัดการวิทยุออนไลน์และระดับเสียง (Radio Player UI)
    การเข้าถึงออกแบบตามหลักอารยะสากลสำหรับตัวอ่านหน้าจอ
    """
    def __init__(self, parent: wx.Window, radio_service: RadioService, speak_fn: Any, config_path: str):
        super().__init__(parent, title="เครื่องเล่นวิทยุออนไลน์สำหรับสตรีมเมอร์", size=(450, 350))
        self.radio = radio_service
        self.speak_fn = speak_fn
        self.config_path = config_path
        self.reader = ReaderHelper(speak_fn)
        
        self.panel = wx.Panel(self)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        
        self._init_controls()
        self._apply_layout()
        self._update_ui_state()
        self.apply_theme()
        
        self.Bind(wx.EVT_CLOSE, self._on_close)
        
        # ประกาศเมื่อหน้าจอโผล่
        self.reader.announce_navigation("เปิดหน้าต่างเครื่องเล่นวิทยุออนไลน์แล้วค่ะ", 8)

    def _init_controls(self):
        # 1. กลุ่มสถานี
        self.choice_stations = wx.Choice(self.panel, choices=[s["name"] for s in self.radio.stations])
        self.choice_stations.SetSelection(self.radio.current_idx)
        self.choice_stations.Bind(wx.EVT_CHOICE, self._on_station_select)
        self.reader.bind_choice_announcement(self.choice_stations, "เลือกช่องสถานีวิทยุออนไลน์")

        # 2. ปุ่มควบคุม
        self.btn_play = wx.Button(self.panel, label="เปิดวิทยุ")
        self.btn_stop = wx.Button(self.panel, label="หยุดวิทยุ")
        self.btn_prev = wx.Button(self.panel, label="สถานีก่อนหน้า")
        self.btn_next = wx.Button(self.panel, label="สถานีถัดไป")
        
        self.btn_play.Bind(wx.EVT_BUTTON, self._on_play_click)
        self.btn_stop.Bind(wx.EVT_BUTTON, self._on_stop_click)
        self.btn_prev.Bind(wx.EVT_BUTTON, self._on_prev_click)
        self.btn_next.Bind(wx.EVT_BUTTON, self._on_next_click)

        self.reader.bind_focus_announcement(self.btn_play, "ปุ่มเริ่มเล่นสถานีวิทยุออนไลน์ที่เลือก")
        self.reader.bind_focus_announcement(self.btn_stop, "ปุ่มหยุดเล่นวิทยุ")
        self.reader.bind_focus_announcement(self.btn_prev, "ปุ่มเปลี่ยนช่องสถานีเป็นช่องก่อนหน้า")
        self.reader.bind_focus_announcement(self.btn_next, "ปุ่มเปลี่ยนช่องสถานีเป็นช่องถัดไป")

        # 3. ระดับความดัง
        self.lbl_volume = wx.StaticText(self.panel, label=f"ความดังวิทยุ: {self.radio.volume_pct}%")
        self.sld_volume = wx.Slider(self.panel, value=self.radio.volume_pct, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL)
        self.sld_volume.Bind(wx.EVT_SLIDER, self._on_volume_scroll)
        self.reader.bind_slider_announcement(self.sld_volume, "ระดับเสียงวิทยุ", "เปอร์เซ็นต์")

        # 4. ปุ่มควบคุมความดังด่วน (สำหรับ accessibility เพิ่ม/ลดทีละ 10%)
        self.btn_vol_down = wx.Button(self.panel, label="ลดเสียงวิทยุ (-10%)")
        self.btn_vol_up = wx.Button(self.panel, label="เพิ่มเสียงวิทยุ (+10%)")
        
        self.btn_vol_down.Bind(wx.EVT_BUTTON, self._on_vol_down_click)
        self.btn_vol_up.Bind(wx.EVT_BUTTON, self._on_vol_up_click)

        self.reader.bind_focus_announcement(self.btn_vol_down, "ปุ่มลดระดับความดังเสียงลงสิบเปอร์เซ็นต์")
        self.reader.bind_focus_announcement(self.btn_vol_up, "ปุ่มเพิ่มระดับความดังเสียงขึ้นสิบเปอร์เซ็นต์")

    def _apply_layout(self):
        # 1. แถบเลือกสถานี
        self.vbox.Add(wx.StaticText(self.panel, label="เลือกสถานีวิทยุที่ต้องการเปิด:"), 0, wx.ALL | wx.EXPAND, 8)
        self.vbox.Add(self.choice_stations, 0, wx.ALL | wx.EXPAND, 8)

        # 2. ปุ่มเปิด/หยุด
        hbox_control = wx.BoxSizer(wx.HORIZONTAL)
        hbox_control.Add(self.btn_prev, 1, wx.ALL | wx.EXPAND, 4)
        hbox_control.Add(self.btn_play, 1, wx.ALL | wx.EXPAND, 4)
        hbox_control.Add(self.btn_stop, 1, wx.ALL | wx.EXPAND, 4)
        hbox_control.Add(self.btn_next, 1, wx.ALL | wx.EXPAND, 4)
        self.vbox.Add(hbox_control, 0, wx.EXPAND | wx.ALL, 8)

        # 3. แถบเลื่อนความดัง
        hbox_vol = wx.BoxSizer(wx.HORIZONTAL)
        hbox_vol.Add(self.lbl_volume, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 8)
        hbox_vol.Add(self.sld_volume, 1, wx.ALL | wx.EXPAND, 8)
        self.vbox.Add(hbox_vol, 0, wx.EXPAND | wx.ALL, 8)

        # 4. ปุ่มปรับความดังด่วน
        hbox_vol_quick = wx.BoxSizer(wx.HORIZONTAL)
        hbox_vol_quick.Add(self.btn_vol_down, 1, wx.ALL | wx.EXPAND, 4)
        hbox_vol_quick.Add(self.btn_vol_up, 1, wx.ALL | wx.EXPAND, 4)
        self.vbox.Add(hbox_vol_quick, 0, wx.EXPAND | wx.ALL, 8)

        self.panel.SetSizer(self.vbox)

    def _update_ui_state(self):
        self.choice_stations.SetSelection(self.radio.current_idx)
        self.lbl_volume.SetLabel(f"ความดังวิทยุ: {self.radio.volume_pct}%")
        self.sld_volume.SetValue(self.radio.volume_pct)

    def _on_station_select(self, event: wx.Event):
        idx = self.choice_stations.GetSelection()
        self.radio.current_idx = idx
        name = self.radio.stations[idx]["name"]
        self.radio._save_current_station_index()
        self.reader.announce_text(f"เปลี่ยนช่องวิทยุเป็น {name} สำเร็จค่ะ", 8)
        if self.radio.is_playing:
            self.radio.stop_radio()
            msg = self.radio.play_current_station()
            self.speak_fn(msg, 8)

    def _on_play_click(self, event: wx.Event):
        msg = self.radio.play_current_station()
        self.speak_fn(msg, 8)

    def _on_stop_click(self, event: wx.Event):
        msg = self.radio.stop_radio()
        self.speak_fn(msg, 8)

    def _on_prev_click(self, event: wx.Event):
        msg = self.radio.prev_station()
        self.speak_fn(msg, 8)
        self._update_ui_state()

    def _on_next_click(self, event: wx.Event):
        msg = self.radio.next_station()
        self.speak_fn(msg, 8)
        self._update_ui_state()

    def _on_volume_scroll(self, event: wx.Event):
        val = self.sld_volume.GetValue()
        self.lbl_volume.SetLabel(f"ความดังวิทยุ: {val}%")
        self.radio.set_volume(val)

    def _on_vol_down_click(self, event: wx.Event):
        val = max(0, self.radio.volume_pct - 10)
        self.radio.set_volume(val)
        self._update_ui_state()
        self.speak_fn(f"ลดความดังวิทยุเป็น {val} เปอร์เซ็นต์ค่ะ", 5)

    def _on_vol_up_click(self, event: wx.Event):
        val = min(100, self.radio.volume_pct + 10)
        self.radio.set_volume(val)
        self._update_ui_state()
        self.speak_fn(f"เพิ่มความดังวิทยุเป็น {val} เปอร์เซ็นต์ค่ะ", 5)

    def _on_close(self, event: wx.CloseEvent):
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
            font_size = 18 if large_font else 12
            font = wx.Font(font_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD if large_font else wx.FONTWEIGHT_NORMAL)
            
            # สีธีม
            bg_color = wx.Colour(0, 0, 0) if high_contrast else wx.SystemSettings.GetColour(wx.SYS_COLOUR_FRAMEBK)
            fg_color = wx.Colour(255, 255, 0) if high_contrast else wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
            
            self.SetBackgroundColour(bg_color)
            self.panel.SetBackgroundColour(bg_color)
            self.panel.SetForegroundColour(fg_color)
            
            if large_font:
                self.SetSize((550, 450))
            else:
                self.SetSize((450, 350))
                
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

