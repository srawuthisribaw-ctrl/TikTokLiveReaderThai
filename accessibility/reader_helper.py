import wx
import os
import sys
import json
from typing import Callable, Any

class ReaderHelper:
    """
    คลาสช่วยเหลือสำหรับการเข้าถึง (Accessibility Helper)
    ทำหน้าที่ผูกเหตุการณ์ Focus และสลับข้อมูลให้เครื่องอ่านจอภาพ (Screen Reader) 
    รับรู้สถานะปุ่มและตัวเลือกต่างๆ ได้ทันที (Self-Voicing UI)
    """
    def __init__(self, speak_fn: Callable[[str, int], None]):
        self.speak_fn = speak_fn
        self.advanced_blind_mode = False
        self.speak_navigation = False
        self.tts_mode = "nvda"
        
        # โหลดการตั้งค่าจากไฟล์ config.dat โดยตรง
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        config_path = os.path.join(base_dir, "config.dat")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                acc = cfg.get("Accessibility", {})
                self.advanced_blind_mode = acc.get("advanced_blind_mode", False)
                self.speak_navigation = acc.get("speak_navigation", False)
                self.tts_mode = cfg.get("TTS", {}).get("mode", "nvda")
            except Exception:
                pass

    def set_advanced_blind_mode(self, enabled: bool):
        self.advanced_blind_mode = enabled

    def set_speak_navigation(self, enabled: bool):
        self.speak_navigation = enabled

    def set_tts_mode(self, mode: str):
        self.tts_mode = mode

    def announce_text(self, text: str, priority: int = 5):
        """ส่งเสียงประกาศออกระบบทั่วไปหากเปิดโหมดคนตาบอดขั้นสูง"""
        if self.advanced_blind_mode:
            self.speak_fn(text, priority)

    def announce_navigation(self, text: str, priority: int = 5):
        """
        ประกาศเสียงข้อมูลโฟกัสและการเปลี่ยนค่าในอินเทอร์เฟซ (Navigation/Interaction events)
        เพื่อหลีกเลี่ยงเสียงสะท้อนทับซ้อน (Double-voicing) เมื่อผู้ใช้ใช้ NVDA หรือ JAWS
        """
        if self.advanced_blind_mode and self.speak_navigation:
            # หากใช้โหมด NVDA หรือ JAWS ตัวเครื่องอ่านจอภาพจะออกเสียงปุ่มและสถานะตัวควบคุมต่างๆ
            # นำทางหลักตามธรรมชาติอยู่แล้ว จึงข้ามการนำเสนอเสียงซ้ำซ้อน
            if self.tts_mode in ("nvda", "jaws"):
                return
            self.speak_fn(text, priority)

    def bind_focus_announcement(self, control: wx.Window, announce_text: str):
        """
        ผูกเหตุการณ์การได้รับโฟกัส (EVT_SET_FOCUS)
        ให้ระบบเสียงพูดอธิบายปุ่มหรือตัวเลือกนั้นเมื่อแท็บมาถึง
        """
        def on_focus(event: wx.FocusEvent):
            self.announce_navigation(announce_text, 5)
            event.Skip()
            
        control.Bind(wx.EVT_SET_FOCUS, on_focus)

    def bind_checkbox_announcement(self, checkbox: wx.CheckBox, label: str):
        """ผูกความสัมพันธ์สำหรับการแจ้งเตือนสถานะกล่องเลือก (Checked/Unchecked)"""
        def on_toggle(event: wx.CommandEvent):
            state = "ติ๊กถูกเปิดใช้งาน" if checkbox.GetValue() else "ไม่ติ๊กถูกปิดใช้งาน"
            self.announce_navigation(f"{label} สถานะคือ {state}", 8)
            event.Skip()

        checkbox.Bind(wx.EVT_CHECKBOX, on_toggle)
        # ผูกคำอธิบายเวลาแท็บโฟกัสด้วย
        self.bind_focus_announcement(checkbox, f"{label} แถบตัวเลือก")

    def bind_choice_announcement(self, choice: wx.Choice, label: str):
        """ผูกความสัมพันธ์สำหรับตัวเลือกแบบคอมโบ (Choice Combobox)"""
        def on_selection(event: wx.CommandEvent):
            selected = choice.GetStringSelection()
            self.announce_navigation(f"{label} เปลี่ยนเป็น {selected}", 8)
            event.Skip()

        choice.Bind(wx.EVT_CHOICE, on_selection)
        self.bind_focus_announcement(choice, f"{label} เลือกจากตัวเลือก")

    def bind_textctrl_announcement(self, textctrl: wx.TextCtrl, label: str):
        """ผูกการได้รับโฟกัสของกล่องพิมพ์ข้อความ"""
        self.bind_focus_announcement(textctrl, f"ช่องกรอกข้อมูล {label} ปัจจุบันมีข้อความว่า {textctrl.GetValue()}")

    def bind_slider_announcement(self, slider: wx.Slider, label: str, suffix: str = ""):
        """ผูกสถานะของสไลเดอร์ปรับความกว้าง/เสียง"""
        def on_scroll(event: wx.ScrollEvent):
            val = slider.GetValue()
            self.announce_navigation(f"{label} ปรับระดับเป็น {val} {suffix}", 8)
            event.Skip()

        slider.Bind(wx.EVT_SCROLL, on_scroll)
        self.bind_focus_announcement(slider, f"แถบเลื่อน {label} ปัจจุบันอยู่ที่ {slider.GetValue()} {suffix}")

    def announce_menu_item(self, label: str):
        """ประกาศเสียงเมื่อผู้ใช้วิ่งผ่านแถบเมนูในโปรแกรม"""
        self.announce_navigation(f"เข้าสู่เมนู {label}", 5)
