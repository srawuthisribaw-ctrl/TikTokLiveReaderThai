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
from core.i18n import tr

APP_VERSION = "3.0.5"

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
        wx.CallAfter(lambda: self.audio.add_to_queue(tr("WELCOME_MSG"), 10, "sfx_join"))
        wx.CallAfter(self._check_and_prompt_thai_offline)

    def _init_menu_bar(self):
        """สร้างแถบเมนูในภาษาไทยเพื่อคนตาบอด"""
        menu_bar = wx.MenuBar()
        
        # 1. เมนูไฟล์
        menu_file = wx.Menu()
        item_save_log = menu_file.Append(wx.ID_ANY, tr("MENU_SAVE_LOG"))
        menu_file.AppendSeparator()
        item_exit = menu_file.Append(wx.ID_EXIT, tr("MENU_EXIT"))
        
        # 2. เมนูเชื่อมต่อ
        menu_connect = wx.Menu()
        item_conn = menu_connect.Append(wx.ID_ANY, tr("MENU_CONN"))
        item_disconn = menu_connect.Append(wx.ID_ANY, tr("MENU_DISCONN"))
        
        # 3. เมนูสถิติ
        menu_stats = menu_connect  # หรือเมนูแยก
        menu_stats_view = wx.Menu()
        item_view_stats = menu_stats_view.Append(wx.ID_ANY, tr("MENU_VIEW_STATS"))
        item_view_leader = menu_stats_view.Append(wx.ID_ANY, tr("MENU_VIEW_LEADER"))
        
        # 4. เมนูเสียง
        menu_voice = wx.Menu()
        item_set_voice = menu_voice.Append(wx.ID_ANY, tr("MENU_SET_VOICE"))
        item_mute = menu_voice.Append(wx.ID_ANY, tr("MENU_MUTE"))

        # 5. เมนูการเข้าถึง (Accessibility)
        menu_acc = wx.Menu()
        item_toggle_blind = menu_acc.Append(wx.ID_ANY, tr("MENU_TOGGLE_BLIND"))
        item_toggle_contrast = menu_acc.Append(wx.ID_ANY, tr("MENU_TOGGLE_CONTRAST"))
        item_toggle_font = menu_acc.Append(wx.ID_ANY, tr("MENU_TOGGLE_FONT"))

        # 6. เมนูเครื่องมือ (Tools)
        menu_tools = wx.Menu()
        item_game_num = menu_tools.Append(wx.ID_ANY, tr("MENU_GAME_NUM"))
        item_game_word = menu_tools.Append(wx.ID_ANY, tr("MENU_GAME_WORD"))
        item_game_quiz = menu_tools.Append(wx.ID_ANY, tr("MENU_GAME_QUIZ"))
        menu_tools.AppendSeparator()
        item_radio_player = menu_tools.Append(wx.ID_ANY, tr("MENU_RADIO"))
        menu_tools.AppendSeparator()
        item_music_player = menu_tools.Append(wx.ID_ANY, tr("MENU_MUSIC"))
        item_soundboard = menu_tools.Append(wx.ID_ANY, tr("MENU_SOUNDBOARD"))
        menu_tools.AppendSeparator()
        item_draw = menu_tools.Append(wx.ID_ANY, tr("MENU_DRAW", "จับสลากสุ่มผู้ชมผู้โชคดี"))

        # 7. เมนูช่วยเหลือ (Help)
        menu_help = wx.Menu()
        is_activated = self.lic_manager.is_activated()
        if is_activated:
            from core.i18n import get_language
            lang = get_language()
            reg_label = "Full Version (Activated)" if lang == "en" else "เวอร์ชันเต็ม (เปิดใช้งานแล้ว)"
        else:
            reg_label = tr("MENU_HELP_REGISTER")
        self.item_register = menu_help.Append(wx.ID_ANY, reg_label)
        item_doc_th = menu_help.Append(wx.ID_ANY, tr("MENU_HELP_GUIDE"))
        item_doc_blind = menu_help.Append(wx.ID_ANY, tr("MENU_HELP_BLIND"))
        item_check_update = menu_help.Append(wx.ID_ANY, tr("MENU_CHECK_UPDATE", "ตรวจสอบเวอร์ชันและการอัปเดต"))
        item_about = menu_help.Append(wx.ID_ANY, tr("MENU_HELP_ABOUT"))

        # ผูกไอดี
        menu_bar.Append(menu_file, tr("MENU_FILE"))
        menu_bar.Append(menu_connect, tr("MENU_CONNECT"))
        menu_bar.Append(menu_stats_view, tr("MENU_STATS"))
        menu_bar.Append(menu_voice, tr("MENU_VOICE"))
        menu_bar.Append(menu_acc, tr("MENU_ACC"))
        menu_bar.Append(menu_tools, tr("MENU_TOOLS"))
        menu_bar.Append(menu_help, tr("MENU_HELP"))

        self.SetMenuBar(menu_bar)

        # ผูก Callback ของเมนู
        self.Bind(wx.EVT_MENU, lambda e: self._on_export_logs_click(), item_save_log)
        self.Bind(wx.EVT_MENU, lambda e: self.Close(), item_exit)
        self.Bind(wx.EVT_MENU, lambda e: self._on_start_connection(), item_conn)
        self.Bind(wx.EVT_MENU, lambda e: self._on_stop_connection(), item_disconn)
        self.Bind(wx.EVT_MENU, lambda e: self._on_open_stats_window(), item_view_stats)
        self.Bind(wx.EVT_MENU, lambda e: self._on_speak_leaderboard(), item_view_leader)
        self.Bind(wx.EVT_MENU, lambda e: self._on_open_settings_voice(1), item_set_voice)
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
        self.Bind(wx.EVT_MENU, lambda e: self._on_register_app(), self.item_register)

    def _init_gui_layout(self):
        """ออกแบบเลย์เอาต์ช่องข้อความและปุ่มหลัก"""
        # 1. ส่วนกรอกชื่อห้อง
        self.vbox.Add(wx.StaticText(self.panel, label=tr("LABEL_STREAMER_ID")), 0, wx.ALL, 5)
        
        # อ่านไอดีล่าสุดในคอนฟิกเพื่อใส่เป็นค่าเริ่มต้น
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            last_id = cfg.get("Settings", {}).get("last_id", "")
        except Exception:
            last_id = ""
 
        self.txt_tiktok_id = wx.TextCtrl(self.panel, value=last_id)
        self.reader.bind_textctrl_announcement(self.txt_tiktok_id, tr("FOCUS_TXT_TIKTOK_ID", "ช่องพิมพ์ไอดีติ๊กต็อกผู้ใช้งาน"))
        self.vbox.Add(self.txt_tiktok_id, 0, wx.EXPAND | wx.ALL, 5)
 
        # 2. แถบปุ่มควบคุม
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_toggle_conn = wx.Button(self.panel, label=tr("BTN_LABEL_CONNECT", "เริ่มการเชื่อมต่อไลฟ์สด"))
        self.btn_open_settings = wx.Button(self.panel, label=tr("BTN_OPEN_SETTINGS", "ตั้งค่าระบบหลักและภาษา (F10)"))
        self.btn_open_stats = wx.Button(self.panel, label=tr("BTN_OPEN_STATS", "ดูผลสถิติแชท (F8)"))
        
        self.btn_toggle_conn.Bind(wx.EVT_BUTTON, self._on_toggle_conn_click)
        self.btn_open_settings.Bind(wx.EVT_BUTTON, lambda e: self._on_open_settings_voice(0))
        self.btn_open_stats.Bind(wx.EVT_BUTTON, lambda e: self._on_open_stats_window())
        
        self.reader.bind_focus_announcement(self.btn_toggle_conn, tr("FOCUS_BTN_TOGGLE_CONN", "ปุ่มเริ่มและหยุดการเชื่อมต่อติ๊กต็อก"))
        self.reader.bind_focus_announcement(self.btn_open_settings, tr("FOCUS_BTN_OPEN_SETTINGS", "ปุ่มเปิดหน้าต่างตั้งค่าระบบโปรแกรมหลัก"))
        self.reader.bind_focus_announcement(self.btn_open_stats, tr("FOCUS_BTN_OPEN_STATS", "ปุ่มเปิดหน้าต่างรายงานผลสถิติไลฟ์สด"))
 
        hbox.Add(self.btn_toggle_conn, 1, wx.ALL | wx.EXPAND, 5)
        hbox.Add(self.btn_open_settings, 1, wx.ALL | wx.EXPAND, 5)
        hbox.Add(self.btn_open_stats, 1, wx.ALL | wx.EXPAND, 5)
        self.vbox.Add(hbox, 0, wx.EXPAND)
 
        # 3. ช่องประวัติกิจกรรม (History Log)
        self.vbox.Add(wx.StaticText(self.panel, label=tr("LBL_HISTORY_LOG", "ประวัติกิจกรรมและคอมเมนต์ในไลฟ์ปัจจุบัน:")), 0, wx.ALL, 5)
        self.list_history = wx.ListBox(self.panel, style=wx.LB_SINGLE)
        self.reader.bind_focus_announcement(self.list_history, tr("FOCUS_LIST_HISTORY", "รายการแสดงประวัติคอมเมนต์และเหตุการณ์สด"))
        self.vbox.Add(self.list_history, 1, wx.EXPAND | wx.ALL, 5)
 
        # 4. สถานะโปรแกรมย่อ
        self.st_status = wx.StaticText(self.panel, label=tr("STATUS_READY", "สถานะ: พร้อมเชื่อมต่อ"))
        self.vbox.Add(self.st_status, 0, wx.ALL, 5)
 
        self.panel.SetSizer(self.vbox)

    def _bind_global_hotkeys(self):
        """ผูก Callback กับปุ่มลัด F1 - F12 และปุ่มลัดเพลง/ซาวด์บอร์ดใหม่"""
        callbacks = {
            101: self._on_speak_status,              # F1
            102: self._on_start_connection,          # F2
            103: self._on_stop_connection,           # F3
            104: lambda: self._on_toggle_read_setting("read_comment", "คอมเมนต์แชท", "chat comments"), # F4
            105: lambda: self._on_toggle_read_setting("read_join", "การเข้าห้อง", "join room alerts"),    # F5
            106: self._on_mute_triggered,            # F6
            107: self._on_speak_leaderboard,         # F7
            108: self._on_speak_statistics,          # F8
            109: lambda: self._on_open_settings_voice(1),       # F9 (ตั้งค่าเสียงอ่าน/การเข้าถึง)
            110: lambda: self._on_open_settings_voice(0),       # F10 (ตั้งค่าระบบหลัก/การอ่านแชท)
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
            130: self._on_open_radio_window,               # Ctrl+Shift+R
            131: lambda: self._on_toggle_read_setting("read_gift", "ของขวัญ", "gift alerts") # Ctrl+Shift+G
        }
        self.hotkeys.register_all_hotkeys(callbacks)

    def _on_manager_callback(self, status: str, detail: str):
        """รับเหตุการณ์การเชื่อมต่อและการแปลงข้อมูลแชทเพื่อแสดงบนหน้าต่างหลัก"""
        if status == "connected":
            wx.CallAfter(self.st_status.SetLabel, tr("STATUS_CONNECTED_ROOM").format(room=detail))
            wx.CallAfter(self.btn_toggle_conn.SetLabel, tr("BTN_DISCONNECT"))
            wx.CallAfter(self.txt_tiktok_id.Disable)
        elif status == "disconnected":
            wx.CallAfter(self.st_status.SetLabel, tr("STATUS_READY"))
            wx.CallAfter(self.btn_toggle_conn.SetLabel, tr("BTN_LABEL_CONNECT"))
            wx.CallAfter(self.txt_tiktok_id.Enable)
        elif status == "connection_failed":
            wx.CallAfter(self.st_status.SetLabel, tr("STATUS_ERROR_DETAIL").format(error=detail))
            wx.CallAfter(self.btn_toggle_conn.SetLabel, tr("BTN_LABEL_CONNECT"))
            wx.CallAfter(self.txt_tiktok_id.Enable)
            
            # Log to history listbox
            error_msg = f"--- {tr('STATUS_ERROR_DETAIL').format(error=detail)} ---"
            wx.CallAfter(self._append_to_history, error_msg)
            
            # Determine localized speech message
            from core.i18n import get_language
            lang = get_language()
            if lang == "en":
                if "UserOfflineError" in detail or "offline" in detail.lower():
                    speak_err = "Connection failed because the user is currently offline."
                elif "UserNotFoundError" in detail or "not exist" in detail.lower():
                    speak_err = "Connection failed because the user was not found."
                elif "SIGI_STATE" in detail or "blocked" in detail.lower():
                    speak_err = "Connection blocked by TikTok. Please try again later."
                else:
                    speak_err = f"Connection failed due to {detail}"
            else:
                if "UserOfflineError" in detail or "offline" in detail.lower():
                    speak_err = "การเชื่อมต่อล้มเหลว เนื่องจากผู้ใช้ไม่ได้กำลังไลฟ์สดอยู่ในขณะนี้ค่ะ"
                elif "UserNotFoundError" in detail or "not exist" in detail.lower() or "never gone live" in detail.lower():
                    speak_err = "การเชื่อมต่อล้มเหลว เนื่องจากไม่พบชื่อผู้ใช้งานนี้ในระบบค่ะ"
                elif "SIGI_STATE" in detail or "blocked" in detail.lower():
                    speak_err = "การเชื่อมต่อถูกบล็อกชั่วคราวโดยติ๊กต็อก กรุณาลองใหม่อีกครั้งภายหลังค่ะ"
                else:
                    speak_err = f"การเชื่อมต่อล้มเหลวเนื่องจาก {detail}"
            
            self.audio.add_to_queue(speak_err, 9, channel="tts")
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
            self.audio.add_to_queue(tr("MSG_ERR_NO_ID"), 8)
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
            
        self.st_status.SetLabel(tr("STATUS_CONNECTING"))
        self.audio.add_to_queue(tr("MSG_CONNECTING_TO").format(id=tid), 8)
        self.manager.connect_live(tid)

    def _on_stop_connection(self):
        from core.i18n import get_language
        lang = get_language()
        if self.manager.is_connected:
            self.audio.add_to_queue(tr("MSG_DISCONNECTING"), 8)
            self.manager.disconnect_live()
            self._append_to_history("--- Connection Disconnected ---" if lang == "en" else "--- ตัดการเชื่อมต่อแชทสะสม ---")

    def _on_speak_status(self):
        """F1: อ่านสถานะระบบปัจจุบัน"""
        status_msg = tr("MSG_STATUS_READY")
        if self.manager.is_connected:
            status_msg += tr("MSG_STATUS_CONNECTED").format(room=self.manager.room_id)
        else:
            status_msg += tr("MSG_STATUS_DISCONNECTED")
        self.audio.add_to_queue(status_msg, 8)

    def _on_mute_triggered(self):
        """F6: เคลียร์คิวเสียงพูดปัจจุบัน"""
        from core.i18n import get_language
        lang = get_language()
        self.audio.mute()
        self._append_to_history("--- Speech Muted ---" if lang == "en" else "--- ปิดการออกเสียง (Muted) ---")

    def _on_toggle_read_setting(self, setting_key: str, desc_th: str, desc_en: str):
        """F4/F5/F6: เปิดหรือปิดตัวเลือกการอ่านสะสม"""
        from core.i18n import get_language
        lang = get_language()
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                
            curr = cfg.get("Settings", {}).get(setting_key, True)
            new_val = not curr
            cfg["Settings"][setting_key] = new_val
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
                
            desc = desc_en if lang == "en" else desc_th
            if lang == "en":
                state_str = "enabled" if new_val else "disabled"
                self.audio.add_to_queue(f"System changed setting to {state_str} reading {desc} successfully.", 8)
            else:
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
        from core.i18n import get_language
        lang = get_language()
        stats = self.db.get_summary_statistics()
        if lang == "en":
            text = (
                f"Latest live statistics: Total viewers: {stats['total_viewers']}, "
                f"comments: {stats['total_comments']}, "
                f"gifts: {stats['total_gifts']}, estimated earnings: {stats['estimated_earnings_thb']:.2f} Baht."
            )
        else:
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
        from core.i18n import get_language
        lang = get_language()
        stats = self.db.get_summary_statistics()
        if lang == "en":
            text = (
                f"Current live session summary: Cumulative comments: {stats['total_comments']}, "
                f"received total diamonds: {stats['total_diamonds']}, "
                f"new followers: {stats['total_followers']}."
            )
        else:
            text = (
                f"สรุปผลไลฟ์เซสชันปัจจุบัน: มีคอมเมนต์สะสม {stats['total_comments']} ข้อความ, "
                f"ได้รับของขวัญมูลค่ารวม {stats['total_diamonds']} เพชร, "
                f"ผู้ติดตามช่องเพิ่มขึ้น {stats['total_followers']} คนค่ะ"
            )
        self.audio.add_to_queue(text, 8)

    def _on_open_settings_voice(self, initial_tab: int = 1):
        """F9/F10: เปิดหน้าจอตั้งค่าตัวเลือกเสียง"""
        dlg = SettingsDialog(self, self.config_path, self.audio.add_to_queue, initial_tab)
        if dlg.ShowModal() == wx.ID_OK:
            self.audio.add_to_queue(tr("MSG_SAVE_RESTART"), 8)
            wx.MessageBox(tr("MSG_SAVE_RESTART"), tr("TITLE_SAVE"), wx.OK | wx.ICON_INFORMATION)
            self.audio.reload_settings()
            self.apply_theme()
        dlg.Destroy()

    def _on_open_stats_window(self):
        """เปิดรายงานผลลีดเดอร์บอร์ดภาพรวม"""
        win = StatsWindow(self, self.config_path, self.audio.add_to_queue)
        win.Show()

    def _on_export_logs_click(self):
        """F11: บันทึกข้อมูลออกมาเป็น TXT, CSV, JSON"""
        from core.i18n import get_language
        lang = get_language()
        import sys
        if getattr(sys, 'frozen', False):
            base_dir = os.path.join(os.path.dirname(sys.executable), "_internal")
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

        if lang == "en":
            self.audio.add_to_queue("Exported stream logs to Text, CSV, and JSON successfully.", 8)
            self._append_to_history("[System]: Saved logs to logs folder.")
        else:
            self.audio.add_to_queue(f"ส่งออกประวัติสตรีมเป็นไฟล์ข้อความ ซีเอสวี และเจสัน เรียบร้อยแล้วค่ะ", 8)
            self._append_to_history(f"[ระบบ]: บันทึกข้อมูล Log ในโฟลเดอร์ logs เรียบร้อย")

    def _on_streamer_ai_assistant_ask(self):
        """
        Ctrl+Shift+A: เรียกปัญญาประดิษฐ์ตอบคำถามเสียงเกี่ยวกับไลฟ์
        ใช้การพิมพ์/พูดจำลอง (ในกรณีผู้ใช้ตาบอด จะมี Popup เด้งขึ้นมาเพื่อถามเสียงหรือพิมพ์ถามด่วน)
        """
        from core.i18n import get_language
        lang = get_language()
        feature_name = "AI Assistant" if lang == "en" else "ผู้ช่วย AI"
        if not self._check_license_and_prompt(feature_name):
            return
        # เพื่อความรวดเร็วและใช้แป้นพิมพ์เป็นหลัก
        # เราเปิด Dialog ถามคำถามเสียงสตรีมเมอร์
        prompt_label = "Ask AI assistant about your live statistics:" if lang == "en" else "ถามผู้ช่วย AI เกี่ยวกับสถิติไลฟ์ของคุณ:"
        title_label = "AI Streamer Assistant" if lang == "en" else "ผู้ช่วยสตรีมเมอร์ตาบอด AI"
        announce_label = "Opened prompt dialog. Ask AI assistant and press Enter to hear answer." if lang == "en" else "เด้งหน้าจอกล่องข้อความ ถามผู้ช่วยเอไอ พิมพ์เสร็จกดตกลงเพื่อฟังคำตอบ"
        dlg = wx.TextEntryDialog(self, prompt_label, title_label)
        self.reader.announce_text(announce_label, 8)
        if dlg.ShowModal() == wx.ID_OK:
            q = dlg.GetValue()
            if q.strip():
                ans = self.manager.ai.answer_streamer_voice_query(q)
                self.audio.add_to_queue(ans, 10)
        dlg.Destroy()

    # --- ฟังก์ชันระบบเครื่องมือและเกม ---
    def _on_start_game(self, game_type: str):
        """เริ่มกิจกรรมเกมแชท"""
        from core.i18n import get_language
        lang = get_language()
        if game_type == "number":
            msg = self.manager.games.start_guess_number()
        elif game_type == "word":
            msg = self.manager.games.start_guess_word()
        else:
            msg = self.manager.games.start_quiz()
            
        self.audio.add_to_queue(msg, 8)
        self._append_to_history(f"[Game]: {msg}" if lang == "en" else f"[เกม]: {msg}")

    def _on_draw_lucky_winner(self):
        """จับสลากสุ่มผู้ชมผู้โชคดี"""
        from core.i18n import get_language
        lang = get_language()
        msg = self.manager.games.draw_lucky_winner()
        self.audio.add_to_queue(msg, 8)
        self._append_to_history(f"[Lucky Draw]: {msg}" if lang == "en" else f"[สุ่มรางวัล]: {msg}")

    def _on_open_radio_window(self):
        """เปิดหน้าต่างควบคุมเครื่องเล่นวิทยุออนไลน์"""
        from core.i18n import get_language
        lang = get_language()
        feature_name = "Online Radio Player" if lang == "en" else "เครื่องเล่นวิทยุออนไลน์"
        if not self._check_license_and_prompt(feature_name):
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
        from core.i18n import get_language
        lang = get_language()
        doc_name = "คู่มือภาษาไทย.txt" if manual_type == "general" else "คู่มือคนตาบอด.txt"
        import sys
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        doc_path = os.path.join(base_dir, doc_name)
        if os.path.exists(doc_path):
            os.system(f'notepad.exe "{doc_path}"')
            if lang == "en":
                self.audio.add_to_queue("Help manual opened successfully.", 8)
            else:
                self.audio.add_to_queue(f"เปิดคู่มือความช่วยเหลือ เรียบร้อยแล้วค่ะ", 8)
        else:
            if lang == "en":
                self.audio.add_to_queue(f"Help manual file {doc_name} not found.", 8)
            else:
                self.audio.add_to_queue(f"ไม่พบไฟล์คู่มือ {doc_name} ค่ะ", 8)

    def _on_check_update_action(self):
        import threading
        from core.i18n import get_language
        lang = get_language()
        
        if lang == "en":
            self.audio.add_to_queue("Checking the latest program version from primary server.", 8)
        else:
            self.audio.add_to_queue("กำลังตรวจสอบรุ่นโปรแกรมล่าสุดกับเซิร์ฟเวอร์หลักค่ะ", 8)
            
        def check_thread():
            import requests
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                response = requests.get("https://raw.githubusercontent.com/srawuthisribaw-ctrl/TikTokLiveReaderThai/main/version.txt", headers=headers, timeout=5)
                latest_ver = response.text.strip()
                wx.CallAfter(self._on_check_update_result, latest_ver, None)
            except Exception as e:
                wx.CallAfter(self._on_check_update_result, None, str(e))
                
        t = threading.Thread(target=check_thread, daemon=True)
        t.start()

    def _on_check_update_result(self, latest_ver: str, error: str):
        from core.i18n import get_language
        lang = get_language()
        
        if error:
            if lang == "en":
                self.audio.add_to_queue("Failed to check for updates. Please try again later.", 8)
                wx.MessageBox(f"Failed to connect to update server:\n{error}", "Update Error", wx.OK | wx.ICON_ERROR)
            else:
                self.audio.add_to_queue("ล้มเหลวในการตรวจสอบการอัปเดตค่ะ กรุณาลองใหม่อีกครั้งภายหลัง", 8)
                wx.MessageBox(f"ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์อัปเดตได้ค่ะ:\n{error}", "ข้อผิดพลาดระบบ", wx.OK | wx.ICON_ERROR)
            return

        local_ver = APP_VERSION
        
        def parse_ver(v_str):
            try:
                return tuple(map(int, v_str.strip().split('.')))
            except Exception:
                return (0, 0, 0)
                
        if parse_ver(latest_ver) > parse_ver(local_ver):
            if lang == "en":
                self.audio.add_to_queue(f"New version {latest_ver} is available. Do you want to update now?", 8)
                msg = f"New version {latest_ver} is available (Current: {local_ver}).\nDo you want to update now?\nThe program will close to install the update."
                title = "Update Available"
            else:
                self.audio.add_to_queue(f"พบรุ่นใหม่ เวอร์ชัน {latest_ver} พร้อมใช้งานแล้วค่ะ คุณต้องการอัปเดตทันทีหรือไม่", 8)
                msg = f"พบรุ่นปรับปรุงใหม่ เวอร์ชัน {latest_ver} พร้อมใช้งานแล้วค่ะ (เวอร์ชันปัจจุบัน: {local_ver})\nคุณต้องการดาวน์โหลดและติดตั้งตัวอัปเดตทันทีเลยหรือไม่?\n*โปรแกรมจะปิดตัวลงชั่วคราวเพื่อทำรายการค่ะ*"
                title = "พบเวอร์ชันใหม่"
                
            dial = wx.MessageDialog(self, msg, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            if dial.ShowModal() == wx.ID_YES:
                self._run_updater_program()
        else:
            if lang == "en":
                self.audio.add_to_queue("Your program is up to date.", 8)
                wx.MessageBox(f"Your current version {local_ver} is the latest and most stable.", "System Update Successful", wx.OK | wx.ICON_INFORMATION)
            else:
                self.audio.add_to_queue("โปรแกรมของคุณเป็นรุ่นล่าสุดและเสถียรที่สุดแล้วค่ะ", 8)
                wx.MessageBox(f"เวอร์ชันปัจจุบันของคุณ {local_ver} เป็นรุ่นล่าสุดและเสถียรที่สุดแล้วค่ะ", "อัปเดตระบบสำเร็จ", wx.OK | wx.ICON_INFORMATION)

    def _run_updater_program(self):
        import subprocess
        import sys
        
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
            updater_exe = os.path.join(base_dir, "_internal", "updater.exe")
            if not os.path.exists(updater_exe):
                updater_exe = os.path.join(base_dir, "updater.exe")
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            updater_exe = os.path.join(base_dir, "updater.py")
            
        try:
            if getattr(sys, 'frozen', False) and os.path.exists(updater_exe):
                subprocess.Popen([updater_exe])
            else:
                subprocess.Popen([sys.executable, updater_exe])
            
            self.Close()
        except Exception as e:
            from core.i18n import get_language
            lang = get_language()
            if lang == "en":
                wx.MessageBox(f"Failed to start updater: {e}", "Error", wx.OK | wx.ICON_ERROR)
            else:
                wx.MessageBox(f"ไม่สามารถเริ่มโปรแกรมอัปเดตได้ค่ะ: {e}", "ข้อผิดพลาด", wx.OK | wx.ICON_ERROR)

    def _on_show_about(self):
        from core.i18n import get_language
        lang = get_language()
        if lang == "en":
            msg = (
                "TikTok Live Reader Thai Accessibility Edition\n"
                f"Version: {APP_VERSION}\n"
                "Developed by: sarawoot sribaw\n"
                "Designed and developed for visually impaired 100%\n"
                "Thank you to all project supporters.\n\n"
                "Developer contact info:\n"
                "Email: srawuthisribaw@gmail.com\n"
                "Facebook: sarawoot sribaw"
            )
            self.audio.add_to_queue(f"Developer contact details: Email srawuthisribaw@gmail.com and Facebook sarawoot sribaw. Version {APP_VERSION}.", 8, channel="tts")
            wx.MessageBox(msg, "About Developer & Contact Info", wx.ICON_INFORMATION)
        else:
            msg = (
                "TikTok Live Reader Thai Accessibility Edition\n"
                f"เวอร์ชัน: {APP_VERSION}\n"
                "พัฒนาโดย: sarawoot sribaw\n"
                "ออกแบบและพัฒนาเพื่อผู้พิการทางสายตา 100%\n"
                "ขอบคุณผู้ร่วมสนับสนุนโครงการทุกท่านค่ะ\n\n"
                "ช่องทางการติดต่อนักพัฒนา:\n"
                "อีเมล (Email): srawuthisribaw@gmail.com\n"
                "เฟซบุ๊ก (Facebook): sarawoot sribaw"
            )
            self.audio.add_to_queue(f"ข้อมูลติดต่อนักพัฒนา อีเมล srawuthisribaw@gmail.com และ เฟซบุ๊ก sarawoot sribaw ค่ะ เวอร์ชัน {APP_VERSION}.", 8, channel="tts")
            wx.MessageBox(msg, "เกี่ยวกับผู้พัฒนาและข้อมูลการติดต่อ", wx.ICON_INFORMATION)

    # --- การเข้าถึง (Accessibility) ---
    def _on_toggle_blind_mode(self):
        from core.i18n import get_language
        lang = get_language()
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
            if lang == "en":
                state_str = "enabled" if new_val else "disabled"
                self.audio.add_to_queue(f"Toggled advanced blind mode to {state_str}.", 8)
            else:
                state_str = "เปิดใช้งาน" if new_val else "ปิดใช้งาน"
                self.audio.add_to_queue(f"สลับระบบเสียงนำทางคนตาบอดเป็น {state_str} แล้วค่ะ", 8)
        except Exception:
            pass

    def _on_toggle_contrast_mode(self):
        from core.i18n import get_language
        lang = get_language()
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            curr = cfg.get("Accessibility", {}).get("high_contrast", False)
            new_val = not curr
            cfg["Accessibility"]["high_contrast"] = new_val
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            
            self.apply_theme()
            if lang == "en":
                state_str = "high contrast enabled" if new_val else "high contrast disabled"
                self.audio.add_to_queue(f"Toggled color theme to {state_str}.", 8)
            else:
                state_str = "เปิดใช้งานสีตัดกันสูง" if new_val else "ปิดใช้งานสีตัดกันสูง"
                self.audio.add_to_queue(f"สลับโหมดสี {state_str} แล้วค่ะ", 8)
        except Exception:
            pass

    def _on_toggle_large_font(self):
        from core.i18n import get_language
        lang = get_language()
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            curr = cfg.get("Accessibility", {}).get("large_font", False)
            new_val = not curr
            cfg["Accessibility"]["large_font"] = new_val
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            
            self.apply_theme()
            if lang == "en":
                state_str = "large font enabled" if new_val else "normal font size"
                self.audio.add_to_queue(f"Toggled font style to {state_str}.", 8)
            else:
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
        from core.i18n import get_language
        lang = get_language()
        feature_name = "Control Music Player" if lang == "en" else "ควบคุมเครื่องเล่นเพลง"
        if not self._check_license_silent(feature_name):
            return
        music = self.manager.music
        if music.music_volume > 0.0:
            self._prev_music_volume = music.music_volume
            music.set_volume(0.0)
            self.audio.add_to_queue("Music muted." if lang == "en" else "ปิดเสียงเพลงแล้วค่ะ", 5)
        else:
            vol = getattr(self, "_prev_music_volume", 0.3)
            if vol <= 0.0:
                vol = 0.3
            music.set_volume(vol)
            if lang == "en":
                self.audio.add_to_queue(f"Music unmuted. Volume is {int(vol * 100)} percent.", 5)
            else:
                self.audio.add_to_queue(f"เปิดเสียงเพลง ความดัง {int(vol * 100)} เปอร์เซ็นต์ค่ะ", 5)

    def _on_open_music_window(self):
        from core.i18n import get_language
        lang = get_language()
        feature_name = "Viewer Song Request Player" if lang == "en" else "เครื่องเล่นเพลงคำขอ"
        if not self._check_license_and_prompt(feature_name):
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
        from core.i18n import get_language
        lang = get_language()
        feature_name = "Soundboard Effects" if lang == "en" else "ซาวด์บอร์ดเอฟเฟกต์"
        if not self._check_license_silent(feature_name):
            return
        self.manager.soundboard.play_sound(key)

    def _on_play_random_sfx(self):
        from core.i18n import get_language
        lang = get_language()
        feature_name = "Soundboard Effects" if lang == "en" else "ซาวด์บอร์ดเอฟเฟกต์"
        if not self._check_license_silent(feature_name):
            return
        self.manager.soundboard.play_random_effect()

    def _on_open_soundboard_window(self):
        from core.i18n import get_language
        lang = get_language()
        feature_name = "Soundboard Effects Panel" if lang == "en" else "แผงซาวด์บอร์ดเอฟเฟกต์"
        if not self._check_license_and_prompt(feature_name):
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
            msg = tr("TH_OFFLINE_PROMPT")
            dlg = wx.MessageDialog(self, msg, tr("TH_OFFLINE_TITLE"), wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal() == wx.ID_YES:
                self.audio.add_to_queue(tr("MSG_START_OFFLINE_INSTALL", "กำลังเริ่มการลงทะเบียนเสียงภาษาไทยแบบออฟไลน์ กรุณากดตกลงอนุญาตสิทธิ์ผู้ดูแลระบบค่ะ"), 8)
                success = tts_engine.install_thai_offline()
                if success:
                    wx.MessageBox(
                        tr("MSG_TH_OFFLINE_SUCCESS"),
                        tr("TITLE_TH_OFFLINE_SUCCESS"),
                        wx.ICON_INFORMATION
                    )
                    self.audio.add_to_queue(tr("TITLE_TH_OFFLINE_SUCCESS"), 8)
                else:
                    wx.MessageBox(
                        tr("MSG_TH_OFFLINE_FAILED"),
                        tr("TITLE_TH_OFFLINE_FAILED"),
                        wx.ICON_WARNING
                    )
                    self.audio.add_to_queue(tr("TITLE_TH_OFFLINE_FAILED"), 8)
            dlg.Destroy()

    def _check_license_and_prompt(self, feature_name: str) -> bool:
        """ตรวจสอบสิทธิ์และแสดงหน้าจอเปิดใช้งานกรณีไม่ได้ลงทะเบียน (สำหรับเมนู/หน้าต่างเปิดหลัก)"""
        from core.i18n import get_language
        lang = get_language()
        if self.lic_manager.is_activated():
            return True
        if lang == "en":
            self.audio.add_to_queue(f"Feature {feature_name} is only available in the full version. Please register to activate.", 8)
        else:
            self.audio.add_to_queue(f"ฟีเจอร์ {feature_name} สำหรับผู้ใช้งานเวอร์ชันเต็มเท่านั้น กรุณาลงทะเบียนเพื่อเปิดใช้งานค่ะ", 8)
        if self.lic_manager.check_activation_flow():
            return True
        return False

    def _check_license_silent(self, feature_name: str) -> bool:
        """ตรวจสอบสิทธิ์แบบไม่มีหน้าจอป๊อปอัปอัตโนมัติ (สำหรับคีย์ลัดด่วน)"""
        from core.i18n import get_language
        lang = get_language()
        if self.lic_manager.is_activated():
            return True
        if lang == "en":
            self.audio.add_to_queue(f"Feature {feature_name} is restricted to the full version.", 8)
        else:
            self.audio.add_to_queue(f"ฟีเจอร์ {feature_name} จำกัดเฉพาะผู้ใช้งานเวอร์ชันเต็มเท่านั้นค่ะ", 8)
        return False

    def _on_register_app(self):
        """คลิกเมนูลงทะเบียน"""
        from core.i18n import get_language
        lang = get_language()
        if self.lic_manager.is_activated():
            reg_label = "Full Version (Activated)" if lang == "en" else "เวอร์ชันเต็ม (เปิดใช้งานแล้ว)"
            self.item_register.SetItemLabel(reg_label)
            if lang == "en":
                self.audio.add_to_queue("This program is already activated in the full version. Thank you very much.", 8)
                wx.MessageBox("This program is already activated in the full version. Thank you for your support!", "Registration Successful", wx.OK | wx.ICON_INFORMATION)
            else:
                self.audio.add_to_queue("โปรแกรมนี้เปิดใช้งานเวอร์ชันเต็มเรียบร้อยแล้วค่ะ ขอบคุณมากค่ะ", 8)
                wx.MessageBox("โปรแกรมนี้เปิดใช้งานเวอร์ชันเต็มเรียบร้อยแล้ว ขอบคุณที่สนับสนุนครับ!", "ลงทะเบียนสำเร็จแล้ว", wx.OK | wx.ICON_INFORMATION)
            return
        if self.lic_manager.check_activation_flow():
            reg_label = "Full Version (Activated)" if lang == "en" else "เวอร์ชันเต็ม (เปิดใช้งานแล้ว)"
            self.item_register.SetItemLabel(reg_label)
