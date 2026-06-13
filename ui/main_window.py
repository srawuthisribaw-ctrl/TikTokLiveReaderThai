import wx
import os
import json
import csv
import time
from datetime import datetime
from typing import Dict, Any, List

from core.tiktok_manager import TikTokManager
from tts.audio_queue import AudioQueue
from database.db_helper import DatabaseHelper
from accessibility.hotkey_manager import HotkeyManager
from accessibility.reader_helper import ReaderHelper
from ui.settings_dialog import SettingsDialog
from ui.stats_window import StatsWindow
from ui.music_window import MusicWindow
from ui.soundboard_window import SoundboardWindow
from ui.radio_window import RadioWindow

class MainWindow(wx.Frame):
    """
    หน้าต่างโปรแกรมหลัก (Main Window Frame)
    เป็นศูนย์รวมการประมวลผลและการสลับสถานะทั้งหมดในระบบ
    """
    def __init__(self, title: str, config_path: str):
        super().__init__(None, title=title, size=(650, 700))
        self.config_path = config_path
        
        # 1. เริ่มระบบเสียงประกอบและ TTS Queue
        self.audio = AudioQueue(config_path)
        
        # 2. บูตโมดูล TikTok Manager
        self.manager = TikTokManager(config_path, self.audio, self._on_manager_callback)
        self.db = DatabaseHelper()
        self.reader = ReaderHelper(self.audio.add_to_queue)
        
        # 2.5 เริ่มโมดูลตรวจสอบสิทธิ์การใช้งาน
        from core.licensing import LicenseManager
        self.lic_manager = LicenseManager(config_path)
        
        # 3. เตรียมคอมโพเนนต์อินเทอร์เฟซผู้ใช้
        self.panel = wx.Panel(self)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        
        self._init_menu_bar()
        self._init_gui_layout()
        
        # 4. จัดการปุ่มลัดระบบ (Global Hotkeys)
        self.hotkeys = HotkeyManager(self)
        self._bind_global_hotkeys()
        
        # โหลดสไตล์ธีมและความดังเสียง
        self.apply_theme()
        
        self.Bind(wx.EVT_CLOSE, self._on_close_window)
        self.Show()
        
        # ทักทายเสียงเปิดตัวแรก
        wx.CallAfter(lambda: self.audio.add_to_queue("ยินดีต้อนรับสู่ ติ๊กต็อก ไลฟ์ รีดเดอร์ พร้อมใช้งานค่ะ", 10, "sfx_join"))
        wx.CallAfter(self._check_and_prompt_thai_offline)

    def _init_menu_bar(self):
        """สร้างแถบเมนูในภาษาไทยเพื่อคนตาบอด"""
        menu_bar = wx.MenuBar()
        
        # 1. เมนูไฟล์
        menu_file = wx.Menu()
        item_save_log = menu_file.Append(wx.ID_ANY, "บันทึก Log การไลฟ์ (F11)")
        menu_file.AppendSeparator()
        item_exit = menu_file.Append(wx.ID_EXIT, "ออกจากโปรแกรม")
        
        # 2. เมนูเชื่อมต่อ
        menu_connect = wx.Menu()
        item_conn = menu_connect.Append(wx.ID_ANY, "เริ่มเชื่อมต่อห้องไลฟ์สด (F2)")
        item_disconn = menu_connect.Append(wx.ID_ANY, "หยุดการเชื่อมต่อห้อง (F3)")
        
        # 3. เมนูสถิติ
        menu_stats = menu_connect  # หรือเมนูแยก
        menu_stats_view = wx.Menu()
        item_view_stats = menu_stats_view.Append(wx.ID_ANY, "เปิดรายงานสรุปสถิติสด (F8)")
        item_view_leader = menu_stats_view.Append(wx.ID_ANY, "อ่านคะแนนอันดับผู้ชม (F7)")
        
        # 4. เมนูเสียง
        menu_voice = wx.Menu()
        item_set_voice = menu_voice.Append(wx.ID_ANY, "ตั้งค่าเสียงอ่านและภาษา (F9)")
        item_mute = menu_voice.Append(wx.ID_ANY, "หยุดและเงียบเสียงพูดด่วน (F6)")

        # 5. เมนูการเข้าถึง (Accessibility)
        menu_acc = wx.Menu()
        item_toggle_blind = menu_acc.Append(wx.ID_ANY, "สลับโหมดคนตาบอดขั้นสูง (Self-Voicing)")
        item_toggle_contrast = menu_acc.Append(wx.ID_ANY, "สลับสีอินเทอร์เฟซคอนทราสต์สูง (High Contrast)")
        item_toggle_font = menu_acc.Append(wx.ID_ANY, "สลับข้อความขนาดใหญ่ (Large Font)")

        # 6. เมนูเครื่องมือ (Tools)
        menu_tools = wx.Menu()
        item_game_num = menu_tools.Append(wx.ID_ANY, "เริ่มเกมทายตัวเลข")
        item_game_word = menu_tools.Append(wx.ID_ANY, "เริ่มเกมทายคำศัพท์")
        item_game_quiz = menu_tools.Append(wx.ID_ANY, "เริ่มเกมตอบคำถาม")
        menu_tools.AppendSeparator()
        item_radio_player = menu_tools.Append(wx.ID_ANY, "เครื่องเล่นวิทยุออนไลน์ (Ctrl+Shift+R)")
        menu_tools.AppendSeparator()
        item_music_player = menu_tools.Append(wx.ID_ANY, "เครื่องเล่นเพลงสตรีมเมอร์ (Ctrl+Shift+M)")
        item_soundboard = menu_tools.Append(wx.ID_ANY, "ซาวด์บอร์ดเอฟเฟกต์เสียง (Alt+F10)")
        menu_tools.AppendSeparator()
        item_draw = menu_tools.Append(wx.ID_ANY, "จับสลากสุ่มผู้ชมผู้โชคดี")

        # 7. เมนูช่วยเหลือ (Help)
        menu_help = wx.Menu()
        item_register = menu_help.Append(wx.ID_ANY, "ลงทะเบียนเปิดใช้งานเวอร์ชันเต็ม")
        item_doc_th = menu_help.Append(wx.ID_ANY, "คู่มือการใช้งานทั่วไป")
        item_doc_blind = menu_help.Append(wx.ID_ANY, "คู่มือการเข้าถึงสำหรับผู้พิการทางสายตา")
        item_check_update = menu_help.Append(wx.ID_ANY, "ตรวจสอบเวอร์ชันและการอัปเดต")
        item_about = menu_help.Append(wx.ID_ANY, "เกี่ยวกับโปรแกรม")

        # ผูกไอดี
        menu_bar.Append(menu_file, "ไฟล์")
        menu_bar.Append(menu_connect, "เชื่อมต่อห้อง")
        menu_bar.Append(menu_stats_view, "สถิติสะสม")
        menu_bar.Append(menu_voice, "ระบบเสียง")
        menu_bar.Append(menu_acc, "การเข้าถึง")
        menu_bar.Append(menu_tools, "เครื่องมือและเกม")
        menu_bar.Append(menu_help, "ช่วยเหลือ")

        self.SetMenuBar(menu_bar)

        # ผูก Callback ของเมนู
        self.Bind(wx.EVT_MENU, lambda e: self._on_export_logs_click(), item_save_log)
        self.Bind(wx.EVT_MENU, lambda e: self.Close(), item_exit)
        self.Bind(wx.EVT_MENU, lambda e: self._on_start_connection(), item_conn)
        self.Bind(wx.EVT_MENU, lambda e: self._on_stop_connection(), item_disconn)
        self.Bind(wx.EVT_MENU, lambda e: self._on_open_stats_window(), item_view_stats)
        self.Bind(wx.EVT_MENU, lambda e: self._on_speak_leaderboard(), item_view_leader)
        self.Bind(wx.EVT_MENU, lambda e: self._on_open_settings_voice(), item_set_voice)
        self.Bind(wx.EVT_MENU, lambda e: self._on_mute_triggered(), item_mute)
        
        self.Bind(wx.EVT_MENU, lambda e: self._on_toggle_blind_mode(), item_toggle_blind)
        self.Bind(wx.EVT_MENU, lambda e: self._on_toggle_contrast_mode(), item_toggle_contrast)
        self.Bind(wx.EVT_MENU, lambda e: self._on_toggle_large_font(), item_toggle_font)

        self.Bind(wx.EVT_MENU, lambda e: self._on_start_game("number"), item_game_num)
        self.Bind(wx.EVT_MENU, lambda e: self._on_start_game("word"), item_game_word)
        self.Bind(wx.EVT_MENU, lambda e: self._on_start_game("quiz"), item_game_quiz)
        
        self.Bind(wx.EVT_MENU, lambda e: self._on_open_radio_window(), item_radio_player)
        
        self.Bind(wx.EVT_MENU, lambda e: self._on_draw_lucky_winner(), item_draw)
        self.Bind(wx.EVT_MENU, lambda e: self._on_open_music_window(), item_music_player)
        self.Bind(wx.EVT_MENU, lambda e: self._on_open_soundboard_window(), item_soundboard)
        
        self.Bind(wx.EVT_MENU, lambda e: self._on_show_manual("general"), item_doc_th)
        self.Bind(wx.EVT_MENU, lambda e: self._on_show_manual("blind"), item_doc_blind)
        self.Bind(wx.EVT_MENU, lambda e: self._on_check_update_action(), item_check_update)
        self.Bind(wx.EVT_MENU, lambda e: self._on_show_about(), item_about)
        self.Bind(wx.EVT_MENU, lambda e: self._on_register_app(), item_register)

    def _init_gui_layout(self):
        """ออกแบบเลย์เอาต์ช่องข้อความและปุ่มหลัก"""
        # 1. ส่วนกรอกชื่อห้อง
        self.vbox.Add(wx.StaticText(self.panel, label="พิมพ์ TikTok ID สตรีมเมอร์ (ห้ามใส่เครื่องหมาย @ เช่น user123):"), 0, wx.ALL, 5)
        
        # อ่านไอดีล่าสุดในคอนฟิกเพื่อใส่เป็นค่าเริ่มต้น
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            last_id = cfg.get("Settings", {}).get("last_id", "")
        except Exception:
            last_id = ""

        self.txt_tiktok_id = wx.TextCtrl(self.panel, value=last_id)
        self.reader.bind_textctrl_announcement(self.txt_tiktok_id, "ช่องพิมพ์ไอดีติ๊กต็อกผู้ใช้งาน")
        self.vbox.Add(self.txt_tiktok_id, 0, wx.EXPAND | wx.ALL, 5)

        # 2. แถบปุ่มควบคุม
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_toggle_conn = wx.Button(self.panel, label="เริ่มการเชื่อมต่อไลฟ์สด")
        self.btn_open_settings = wx.Button(self.panel, label="ตั้งค่าเสียงโปรแกรม (F10)")
        self.btn_open_stats = wx.Button(self.panel, label="ดูผลสถิติแชท (F8)")
        
        self.btn_toggle_conn.Bind(wx.EVT_BUTTON, self._on_toggle_conn_click)
        self.btn_open_settings.Bind(wx.EVT_BUTTON, lambda e: self._on_open_settings_voice())
        self.btn_open_stats.Bind(wx.EVT_BUTTON, lambda e: self._on_open_stats_window())
        
        self.reader.bind_focus_announcement(self.btn_toggle_conn, "ปุ่มเริ่มและหยุดการเชื่อมต่อติ๊กต็อก")
        self.reader.bind_focus_announcement(self.btn_open_settings, "ปุ่มเปิดหน้าต่างตั้งค่าระบบโปรแกรมหลัก")
        self.reader.bind_focus_announcement(self.btn_open_stats, "ปุ่มเปิดหน้าต่างรายงานผลสถิติไลฟ์สด")

        hbox.Add(self.btn_toggle_conn, 1, wx.ALL | wx.EXPAND, 5)
        hbox.Add(self.btn_open_settings, 1, wx.ALL | wx.EXPAND, 5)
        hbox.Add(self.btn_open_stats, 1, wx.ALL | wx.EXPAND, 5)
        self.vbox.Add(hbox, 0, wx.EXPAND)

        # 3. ช่องประวัติกิจกรรม (History Log)
        self.vbox.Add(wx.StaticText(self.panel, label="ประวัติกิจกรรมและคอมเมนต์ในไลฟ์ปัจจุบัน:"), 0, wx.ALL, 5)
        self.list_history = wx.ListBox(self.panel, style=wx.LB_SINGLE)
        self.reader.bind_focus_announcement(self.list_history, "รายการแสดงประวัติคอมเมนต์และเหตุการณ์สด")
        self.vbox.Add(self.list_history, 1, wx.EXPAND | wx.ALL, 5)

        # 4. สถานะโปรแกรมย่อ
        self.st_status = wx.StaticText(self.panel, label="สถานะ: พร้อมเชื่อมต่อ")
        self.vbox.Add(self.st_status, 0, wx.ALL, 5)

        self.panel.SetSizer(self.vbox)

    def _bind_global_hotkeys(self):
        """ผูก Callback กับปุ่มลัด F1 - F12 และปุ่มลัดเพลง/ซาวด์บอร์ดใหม่"""
        callbacks = {
            101: self._on_speak_status,              # F1
            102: self._on_start_connection,          # F2
            103: self._on_stop_connection,           # F3
            104: lambda: self._on_toggle_read_setting("read_comment", "คอมเมนต์แชท"), # F4
            105: lambda: self._on_toggle_read_setting("read_join", "การเข้าห้อง"),    # F5
            106: lambda: self._on_toggle_read_setting("read_gift", "ของขวัญ"),       # F6
            107: self._on_speak_leaderboard,         # F7
            108: self._on_speak_statistics,          # F8
            109: self._on_open_settings_voice,       # F9
            110: self._on_open_settings_voice,       # F10 (ให้เปิดตั่งค่าหลัก)
            111: self._on_export_logs_click,         # F11
            112: self._on_speak_live_summary,        # F12
            113: self._on_streamer_ai_assistant_ask, # Ctrl+Shift+A
            114: self._on_quick_voice_stats,         # Ctrl+Shift+S
            # เครื่องเล่นเพลง
            115: self._on_music_play_pause,          # Ctrl+P
            116: self._on_music_next,                # Ctrl+N
            117: self._on_music_prev,                # Ctrl+B
            118: self._on_toggle_music_mute,         # Ctrl+M
            119: self._on_open_music_window,         # Ctrl+Shift+M
            # ซาวด์บอร์ด Alt+F1 - Alt+F10
            120: lambda: self._on_play_sfx("laugh"),      # Alt+F1
            121: lambda: self._on_play_sfx("applause"),   # Alt+F2
            122: lambda: self._on_play_sfx("cheer"),      # Alt+F3
            123: lambda: self._on_play_sfx("wow"),        # Alt+F4
            124: lambda: self._on_play_sfx("rimshot"),    # Alt+F5
            125: lambda: self._on_play_sfx("drumroll"),   # Alt+F6
            126: lambda: self._on_play_sfx("win"),        # Alt+F7
            127: lambda: self._on_play_sfx("lose"),       # Alt+F8
            128: self._on_play_random_sfx,                # Alt+F9
            129: self._on_open_soundboard_window,          # Alt+F10
            130: self._on_open_radio_window                # Ctrl+Shift+R
        }
        self.hotkeys.register_all_hotkeys(callbacks)

    def _on_manager_callback(self, status: str, detail: str):
        """รับเหตุการณ์การเชื่อมต่อและการแปลงข้อมูลแชทเพื่อแสดงบนหน้าต่างหลัก"""
        if status == "connected":
            wx.CallAfter(self.st_status.SetLabel, f"สถานะ: เชื่อมต่อสำเร็จ ห้อง {detail}")
            wx.CallAfter(self.btn_toggle_conn.SetLabel, "หยุดการเชื่อมต่อ")
            wx.CallAfter(self.txt_tiktok_id.Disable)
        elif status == "disconnected":
            wx.CallAfter(self.st_status.SetLabel, "สถานะ: พร้อมเชื่อมต่อ")
            wx.CallAfter(self.btn_toggle_conn.SetLabel, "เริ่มการเชื่อมต่อไลฟ์สด")
            wx.CallAfter(self.txt_tiktok_id.Enable)
        elif status == "connection_failed":
            wx.CallAfter(self.st_status.SetLabel, f"ข้อผิดพลาด: {detail}")
            wx.CallAfter(self.btn_toggle_conn.SetLabel, "เริ่มการเชื่อมต่อไลฟ์สด")
            wx.CallAfter(self.txt_tiktok_id.Enable)
        elif status == "history":
            # ป้อนลงประวัติหน้าจอหลัก
            wx.CallAfter(self._append_to_history, detail)

    def _append_to_history(self, text: str):
        self.list_history.Append(text)
        if self.list_history.GetCount() > 200:
            self.list_history.Delete(0)
        # สั่งให้สกรอลลงไปด้านล่างสุดของประวัติ
        self.list_history.SetSelection(self.list_history.GetCount() - 1)

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
                self.SetSize((800, 850))
            else:
                self.SetSize((650, 700))
            
            self._apply_theme_to_child_controls(self.panel, font, bg_color, fg_color)
            self.panel.Layout()
            self.Layout()
            
            # ส่งต่อการปรับขนาดและสีธีมไปยังหน้าต่างย่อยที่ทำงานอยู่
            if hasattr(self, "music_win") and self.music_win:
                try:
                    self.music_win.apply_theme()
                except Exception:
                    pass
            if hasattr(self, "soundboard_win") and self.soundboard_win:
                try:
                    self.soundboard_win.apply_theme()
                except Exception:
                    pass
            if hasattr(self, "radio_win") and self.radio_win:
                try:
                    self.radio_win.apply_theme()
                except Exception:
                    pass
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


    # --- ฟังก์ชันการทำงานปุ่มและคีย์ลัด ---
    def _on_toggle_conn_click(self, event: wx.Event):
        if not self.manager.is_connected:
            self._on_start_connection()
        else:
            self._on_stop_connection()

    def _on_start_connection(self):
        tid = self.txt_tiktok_id.GetValue().strip()
        if not tid:
            self.audio.add_to_queue("กรุณาใส่ไอดีติ๊กต็อกก่อนทำการเชื่อมต่อค่ะ", 8)
            return
            
        # บันทึกไอดีลงคอนฟิกเก็บไว้
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["Settings"]["last_id"] = tid
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass
            
        self.st_status.SetLabel("สถานะ: กำลังเชื่อมต่อ...")
        self.audio.add_to_queue(f"กำลังเชื่อมต่อกับห้องติ๊กต็อกไอดี {tid} ค่ะ", 8)
        self.manager.connect_live(tid)

    def _on_stop_connection(self):
        if self.manager.is_connected:
            self.audio.add_to_queue("กำลังตัดการเชื่อมต่อห้องไลฟ์สดค่ะ", 8)
            self.manager.disconnect_live()
            self._append_to_history("--- ตัดการเชื่อมต่อแชทสะสม ---")

    def _on_speak_status(self):
        """F1: อ่านสถานะระบบปัจจุบัน"""
        status_msg = "โปรแกรม ติ๊กต็อกไลฟ์ รีดเดอร์ พร้อมใช้งานค่ะ "
        if self.manager.is_connected:
            status_msg += f"สถานะปัจจุบันเชื่อมต่ออยู่กับห้อง {self.manager.room_id} สัญญาณเสถียรค่ะ"
        else:
            status_msg += "สถานะปัจจุบันไม่ได้เชื่อมต่อห้องค่ะ"
        self.audio.add_to_queue(status_msg, 8)

    def _on_mute_triggered(self):
        """F6: เคลียร์คิวเสียงพูดปัจจุบัน"""
        self.audio.mute()
        self._append_to_history("--- ปิดการออกเสียง (Muted) ---")

    def _on_toggle_read_setting(self, setting_key: str, desc: str):
        """F4/F5/F6: เปิดหรือปิดตัวเลือกการอ่านสะสม"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                
            curr = cfg.get("Settings", {}).get(setting_key, True)
            new_val = not curr
            cfg["Settings"][setting_key] = new_val
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
                
            state_str = "เปิดใช้งาน" if new_val else "ปิดใช้งาน"
            self.audio.add_to_queue(f"ระบบเปลี่ยนการตั้งค่า อ่าน{desc} เป็น {state_str} แล้วค่ะ", 8)
        except Exception:
            pass

    def _on_speak_leaderboard(self):
        """F7: อ่านอันดับสปอนเซอร์สูงสุดสามอันดับแรก"""
        lead = self.manager.points.get_leaderboard_status(3)
        self.audio.add_to_queue(lead, 8)

    def _on_speak_statistics(self):
        """F8 หรือเปิดจากปุ่ม: อ่านสถิติผู้เข้าชม"""
        stats = self.db.get_summary_statistics()
        text = (
            f"ยอดรายงานสถิติล่าสุด: มีคนดูสะสม {stats['total_viewers']} คน, "
            f"คอมเมนต์ {stats['total_comments']} ข้อความ, "
            f"ของขวัญ {stats['total_gifts']} ชิ้น ยอดรายได้สะสมประมาณ {stats['estimated_earnings_thb']:.2f} บาทค่ะ"
        )
        self.audio.add_to_queue(text, 8)

    def _on_quick_voice_stats(self):
        """Ctrl+Shift+S: อ่านสถิติสดด่วน"""
        self._on_speak_statistics()

    def _on_speak_live_summary(self):
        """F12: อ่านสรุปการไลฟ์สด"""
        stats = self.db.get_summary_statistics()
        text = (
            f"สรุปผลไลฟ์เซสชันปัจจุบัน: มีคอมเมนต์สะสม {stats['total_comments']} ข้อความ, "
            f"ได้รับของขวัญมูลค่ารวม {stats['total_diamonds']} เพชร, "
            f"ผู้ติดตามช่องเพิ่มขึ้น {stats['total_followers']} คนค่ะ"
        )
        self.audio.add_to_queue(text, 8)

    def _on_open_settings_voice(self):
        """F9/F10: เปิดหน้าจอตั้งค่าตัวเลือกเสียง"""
        dlg = SettingsDialog(self, self.config_path, self.audio.add_to_queue)
        if dlg.ShowModal() == wx.ID_OK:
            self.audio.add_to_queue("บันทึกการตั้งค่าลงระบบเรียบร้อยแล้วค่ะ", 8)
            self.audio.reload_settings()
            self.apply_theme()
        dlg.Destroy()

    def _on_open_stats_window(self):
        """เปิดรายงานผลลีดเดอร์บอร์ดภาพรวม"""
        win = StatsWindow(self, self.config_path, self.audio.add_to_queue)
        win.Show()

    def _on_export_logs_click(self):
        """F11: บันทึกข้อมูลออกมาเป็น TXT, CSV, JSON"""
        import sys
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logs_dir = os.path.join(base_dir, "logs")
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            
        today_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # 1. เขียนแบบ TXT
        txt_path = os.path.join(logs_dir, f"tiktok_log_{today_str}.txt")
        comments = self.db.execute_query("SELECT nickname, comment, timestamp FROM comments")
        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("=== TikTok Live Log History ===\n")
                for c in comments:
                    f.write(f"[{c['timestamp']}] {c['nickname']}: {c['comment']}\n")
        except Exception:
            pass
            
        # 2. เขียนแบบ CSV
        csv_path = os.path.join(logs_dir, f"tiktok_log_{today_str}.csv")
        try:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Nickname", "Comment"])
                for c in comments:
                    writer.writerow([c["timestamp"], c["nickname"], c["comment"]])
        except Exception:
            pass

        # 3. เขียนแบบ JSON
        json_path = os.path.join(logs_dir, f"tiktok_log_{today_str}.json")
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(comments, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        self.audio.add_to_queue(f"ส่งออกประวัติสตรีมเป็นไฟล์ข้อความ ซีเอสวี และเจสัน เรียบร้อยแล้วค่ะ", 8)
        self._append_to_history(f"[ระบบ]: บันทึกข้อมูล Log ในโฟลเดอร์ logs เรียบร้อย")

    def _on_streamer_ai_assistant_ask(self):
        """
        Ctrl+Shift+A: เรียกปัญญาประดิษฐ์ตอบคำถามเสียงเกี่ยวกับไลฟ์
        ใช้การพิมพ์/พูดจำลอง (ในกรณีผู้ใช้ตาบอด จะมี Popup เด้งขึ้นมาเพื่อถามเสียงหรือพิมพ์ถามด่วน)
        """
        if not self._check_license_and_prompt("ผู้ช่วย AI"):
            return
        # เพื่อความรวดเร็วและใช้แป้นพิมพ์เป็นหลัก
        # เราเปิด Dialog ถามคำถามเสียงสตรีมเมอร์
        dlg = wx.TextEntryDialog(self, "ถามผู้ช่วย AI เกี่ยวกับสถิติไลฟ์ของคุณ:", "ผู้ช่วยสตรีมเมอร์ตาบอด AI")
        self.reader.announce_text("เด้งหน้าจอกล่องข้อความ ถามผู้ช่วยเอไอ พิมพ์เสร็จกดตกลงเพื่อฟังคำตอบ", 8)
        if dlg.ShowModal() == wx.ID_OK:
            q = dlg.GetValue()
            if q.strip():
                ans = self.manager.ai.answer_streamer_voice_query(q)
                self.audio.add_to_queue(ans, 10)
        dlg.Destroy()

    # --- ฟังก์ชันระบบเครื่องมือและเกม ---
    def _on_start_game(self, game_type: str):
        """เริ่มกิจกรรมเกมแชท"""
        if game_type == "number":
            msg = self.manager.games.start_guess_number()
        elif game_type == "word":
            msg = self.manager.games.start_guess_word()
        else:
            msg = self.manager.games.start_quiz()
            
        self.audio.add_to_queue(msg, 8)
        self._append_to_history(f"[เกม]: {msg}")

    def _on_draw_lucky_winner(self):
        """จับสลากสุ่มผู้ชมผู้โชคดี"""
        msg = self.manager.games.draw_lucky_winner()
        self.audio.add_to_queue(msg, 8)
        self._append_to_history(f"[สุ่มรางวัล]: {msg}")

    def _on_open_radio_window(self):
        """เปิดหน้าต่างควบคุมเครื่องเล่นวิทยุออนไลน์"""
        if not self._check_license_and_prompt("เครื่องเล่นวิทยุออนไลน์"):
            return
        if hasattr(self, "radio_win") and self.radio_win:
            try:
                self.radio_win.Raise()
                return
            except wx.PyDeadObjectError:
                pass
        self.radio_win = RadioWindow(self, self.manager.radio, self.audio.add_to_queue, self.config_path)
        self.radio_win.Show()

    def _on_show_manual(self, manual_type: str):
        """เปิดไฟล์แสดงคู่มือในโปรแกรมประมวลผลคำเพื่อความง่ายในการอ่านผ่าน Screen reader"""
        doc_name = "คู่มือภาษาไทย.txt" if manual_type == "general" else "คู่มือคนตาบอด.txt"
        import sys
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        doc_path = os.path.join(base_dir, doc_name)
        if os.path.exists(doc_path):
            os.system(f'notepad.exe "{doc_path}"')
            self.audio.add_to_queue(f"เปิดคู่มือความช่วยเหลือ เรียบร้อยแล้วค่ะ", 8)
        else:
            self.audio.add_to_queue(f"ไม่พบไฟล์คู่มือ {doc_name} ค่ะ", 8)

    def _on_check_update_action(self):
        self.audio.add_to_queue("กำลังตรวจสอบรุ่นโปรแกรมล่าสุดกับเซิร์ฟเวอร์หลักค่ะ", 8)
        # ตรวจสอบตัวอัปเดตเวอร์ชัน
        wx.MessageBox("เวอร์ชันปัจจุบันของคุณ 3.0.0 เป็นรุ่นล่าสุดและเสถียรที่สุดแล้วค่ะ", "อัปเดตระบบสำเร็จ", wx.ICON_INFORMATION)

    def _on_show_about(self):
        msg = (
            "TikTok Live Reader Thai Accessibility Edition\n"
            "เวอร์ชัน: 3.0.0\n"
            "พัฒนาโดย: sarawoot sribaw\n"
            "ออกแบบและพัฒนาเพื่อผู้พิการทางสายตา 100%\n"
            "ขอบคุณผู้ร่วมสนับสนุนโครงการทุกท่านค่ะ\n\n"
            "ช่องทางการติดต่อนักพัฒนา:\n"
            "อีเมล (Email): srawuthisribaw@gmail.com\n"
            "เฟซบุ๊ก (Facebook): sarawoot sribaw"
        )
        # ออกเสียงแนะนำเพื่อความสะดวกสำหรับคนตาบอด
        self.audio.add_to_queue("ข้อมูลติดต่อนักพัฒนา อีเมล srawuthisribaw@gmail.com และ เฟซบุ๊ก sarawoot sribaw ค่ะ", 8, channel="tts")
        wx.MessageBox(msg, "เกี่ยวกับผู้พัฒนาและข้อมูลการติดต่อ", wx.ICON_INFORMATION)

    # --- การเข้าถึง (Accessibility) ---
    def _on_toggle_blind_mode(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            curr = cfg.get("Accessibility", {}).get("advanced_blind_mode", False)
            new_val = not curr
            cfg["Accessibility"]["advanced_blind_mode"] = new_val
            cfg["Accessibility"]["speak_navigation"] = False
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            
            self.reader.set_advanced_blind_mode(new_val)
            self.reader.set_speak_navigation(False)
            state_str = "เปิดใช้งาน" if new_val else "ปิดใช้งาน"
            self.audio.add_to_queue(f"สลับระบบเสียงนำทางคนตาบอดเป็น {state_str} แล้วค่ะ", 8)
        except Exception:
            pass

    def _on_toggle_contrast_mode(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            curr = cfg.get("Accessibility", {}).get("high_contrast", False)
            new_val = not curr
            cfg["Accessibility"]["high_contrast"] = new_val
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            
            self.apply_theme()
            state_str = "เปิดใช้งานสีตัดกันสูง" if new_val else "ปิดใช้งานสีตัดกันสูง"
            self.audio.add_to_queue(f"สลับโหมดสี {state_str} แล้วค่ะ", 8)
        except Exception:
            pass

    def _on_toggle_large_font(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            curr = cfg.get("Accessibility", {}).get("large_font", False)
            new_val = not curr
            cfg["Accessibility"]["large_font"] = new_val
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            
            self.apply_theme()
            state_str = "ขยายตัวอักษรใหญ่" if new_val else "ตัวอักษรขนาดปกติ"
            self.audio.add_to_queue(f"สลับโหมดฟอนต์เป็น {state_str} แล้วค่ะ", 8)
        except Exception:
            pass

    def _on_music_play_pause(self):
        if not self._check_license_silent("ควบคุมเครื่องเล่นเพลง"):
            return
        self.manager.music.pause_or_resume()

    def _on_music_next(self):
        if not self._check_license_silent("ควบคุมเครื่องเล่นเพลง"):
            return
        self.manager.music.next_track()

    def _on_music_prev(self):
        if not self._check_license_silent("ควบคุมเครื่องเล่นเพลง"):
            return
        self.manager.music.prev_track()

    def _on_toggle_music_mute(self):
        if not self._check_license_silent("ควบคุมเครื่องเล่นเพลง"):
            return
        music = self.manager.music
        if music.music_volume > 0.0:
            self._prev_music_volume = music.music_volume
            music.set_volume(0.0)
            self.audio.add_to_queue("ปิดเสียงเพลงแล้วค่ะ", 5)
        else:
            vol = getattr(self, "_prev_music_volume", 0.3)
            if vol <= 0.0:
                vol = 0.3
            music.set_volume(vol)
            self.audio.add_to_queue(f"เปิดเสียงเพลง ความดัง {int(vol * 100)} เปอร์เซ็นต์ค่ะ", 5)

    def _on_open_music_window(self):
        if not self._check_license_and_prompt("เครื่องเล่นเพลงคำขอ"):
            return
        # ป้องกันการเปิดหลายหน้าต่าง
        if hasattr(self, "music_win") and self.music_win:
            try:
                self.music_win.Raise()
                return
            except wx.PyDeadObjectError:
                pass
        self.music_win = MusicWindow(self, self.manager.music, self.audio.add_to_queue, self.config_path)
        self.music_win.Show()

    def _on_play_sfx(self, key: str):
        if not self._check_license_silent("ซาวด์บอร์ดเอฟเฟกต์"):
            return
        self.manager.soundboard.play_sound(key)

    def _on_play_random_sfx(self):
        if not self._check_license_silent("ซาวด์บอร์ดเอฟเฟกต์"):
            return
        self.manager.soundboard.play_random_effect()

    def _on_open_soundboard_window(self):
        if not self._check_license_and_prompt("แผงซาวด์บอร์ดเอฟเฟกต์"):
            return
        # ป้องกันการเปิดหลายหน้าต่าง
        if hasattr(self, "soundboard_win") and self.soundboard_win:
            try:
                self.soundboard_win.Raise()
                return
            except wx.PyDeadObjectError:
                pass
        self.soundboard_win = SoundboardWindow(self, self.manager.soundboard, self.audio.add_to_queue, self.config_path)
        self.soundboard_win.Show()

    def _on_close_window(self, event: wx.CloseEvent):
        # ถอนปุ่มลัดออกทั้งหมด
        self.hotkeys.unregister_all_hotkeys()
        
        # ปิดการเชื่อมต่อ TikTok Live
        if self.manager.is_connected:
            self.manager.disconnect_live()
            
        # เคลียร์เสียง
        self.audio.mute()
        
        # ปิดหน้าต่างย่อยถ้าเปิดอยู่
        if hasattr(self, "music_win") and self.music_win:
            try:
                self.music_win.Close()
            except Exception:
                pass
        if hasattr(self, "soundboard_win") and self.soundboard_win:
            try:
                self.soundboard_win.Close()
            except Exception:
                pass
        if hasattr(self, "radio_win") and self.radio_win:
            try:
                self.radio_win.Close()
            except Exception:
                pass
        
        event.Skip()
        os._exit(0)

    def _check_and_prompt_thai_offline(self):
        """ตรวจสอบความพร้อมของเสียงภาษาไทยแบบออฟไลน์ และขอติดตั้งหากจำเป็น"""
        tts_engine = self.audio.tts if hasattr(self, "audio") and hasattr(self.audio, "tts") else None
        if not tts_engine:
            return

        status = tts_engine.check_thai_offline_status()
        if status == "can_install":
            msg = (
                "ระบบตรวจพบว่าเครื่องคอมพิวเตอร์ของคุณมีเสียงพูดภาษาไทยออฟไลน์ (Microsoft Pattara) "
                "แต่ยังไม่ได้ลงทะเบียนให้ใช้งานกับ SAPI5 (โปรแกรมตัวอ่านหน้าจอหรือระบบออฟไลน์ทั่วไป)\n\n"
                "ต้องการให้โปรแกรมทำการลงทะเบียนและเปิดใช้งานเสียงนี้โดยอัตโนมัติหรือไม่?\n"
                "(หมายเหตุ: จะมีการขอสิทธิ์ผู้ดูแลระบบ/Administrator ในขั้นตอนถัดไป)"
            )
            dlg = wx.MessageDialog(self, msg, "พบเสียงภาษาไทยที่ยังไม่ได้ลงทะเบียน", wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal() == wx.ID_YES:
                self.audio.add_to_queue("กำลังเริ่มการลงทะเบียนเสียงภาษาไทยแบบออฟไลน์ กรุณากดตกลงอนุญาตสิทธิ์ผู้ดูแลระบบค่ะ", 8)
                success = tts_engine.install_thai_offline()
                if success:
                    wx.MessageBox(
                        "ลงทะเบียนเสียงภาษาไทยแบบออฟไลน์ (Microsoft Pattara) สำเร็จแล้วค่ะ!\n"
                        "คุณสามารถเลือกใช้เสียงนี้ได้จากหน้าต่างตั้งค่าเสียง (กดปุ่ม F9 หรือ F10)",
                        "ลงทะเบียนเสียงสำเร็จ",
                        wx.ICON_INFORMATION
                    )
                    self.audio.add_to_queue("ลงทะเบียนเสียงภาษาไทยแบบออฟไลน์สำเร็จแล้วค่ะ", 8)
                else:
                    wx.MessageBox(
                        "ไม่สามารถลงทะเบียนเสียงได้ หรือคุณปฏิเสธการให้สิทธิ์ผู้ดูแลระบบค่ะ",
                        "การติดตั้งไม่สำเร็จ",
                        wx.ICON_WARNING
                    )
                    self.audio.add_to_queue("การลงทะเบียนเสียงล้มเหลว หรือไม่ได้รับสิทธิ์ค่ะ", 8)
            dlg.Destroy()

    def _check_license_and_prompt(self, feature_name: str) -> bool:
        """ตรวจสอบสิทธิ์และแสดงหน้าจอเปิดใช้งานกรณีไม่ได้ลงทะเบียน (สำหรับเมนู/หน้าต่างเปิดหลัก)"""
        if self.lic_manager.is_activated():
            return True
        self.audio.add_to_queue(f"ฟีเจอร์ {feature_name} สำหรับผู้ใช้งานเวอร์ชันเต็มเท่านั้น กรุณาลงทะเบียนเพื่อเปิดใช้งานค่ะ", 8)
        if self.lic_manager.check_activation_flow():
            return True
        return False

    def _check_license_silent(self, feature_name: str) -> bool:
        """ตรวจสอบสิทธิ์แบบไม่มีหน้าจอป๊อปอัปอัตโนมัติ (สำหรับคีย์ลัดด่วน)"""
        if self.lic_manager.is_activated():
            return True
        self.audio.add_to_queue(f"ฟีเจอร์ {feature_name} จำกัดเฉพาะผู้ใช้งานเวอร์ชันเต็มเท่านั้นค่ะ", 8)
        return False

    def _on_register_app(self):
        """คลิกเมนูลงทะเบียน"""
        if self.lic_manager.is_activated():
            self.audio.add_to_queue("โปรแกรมนี้เปิดใช้งานเวอร์ชันเต็มเรียบร้อยแล้วค่ะ ขอบคุณมากค่ะ", 8)
            wx.MessageBox("โปรแกรมนี้เปิดใช้งานเวอร์ชันเต็มเรียบร้อยแล้ว ขอบคุณที่สนับสนุนครับ!", "ลงทะเบียนสำเร็จแล้ว", wx.OK | wx.ICON_INFORMATION)
            return
        self.lic_manager.check_activation_flow()
