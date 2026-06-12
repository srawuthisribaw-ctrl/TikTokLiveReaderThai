import wx
import os
from typing import Dict, Any, List
from services.music_service import MusicService
from accessibility.reader_helper import ReaderHelper

class MusicWindow(wx.Frame):
    """
    หน้าต่างสำหรับจัดการเครื่องเล่นเพลง คิวขอเพลง และเพลย์ลิสต์ของผู้จัดไลฟ์ (Music Player UI)
    การเข้าถึงออกแบบตามหลักอารยะสากลสำหรับตัวอ่านหน้าจอ
    """
    def __init__(self, parent: wx.Window, music_service: MusicService, speak_fn: Any, config_path: str):
        super().__init__(parent, title="เครื่องเล่นเพลงและคิวขอเพลงสตรีมเมอร์", size=(650, 700))
        self.music = music_service
        self.speak_fn = speak_fn
        self.config_path = config_path
        self.reader = ReaderHelper(speak_fn)
        
        self.panel = wx.Panel(self)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        
        self._init_controls()
        self._apply_layout()
        self._load_playlists_combo()
        self._update_song_list()
        self._update_request_list()
        
        # เริ่มการวนลูปเช็คความยาวเพลงเมื่อจบลง (Ticker)
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_timer_tick, self.timer)
        self.timer.Start(1000) # ตรวจทุกๆ 1 วินาที

        self.Bind(wx.EVT_CLOSE, self._on_close)
        
        # ประกาศเมื่อหน้าจอโผล่
        self.reader.announce_navigation("เปิดหน้าต่างเครื่องเล่นเพลงและคิวขอเพลงแล้วค่ะ", 8)

    def _init_controls(self):
        # 1. การควบคุมเล่นเพลง
        self.btn_play = wx.Button(self.panel, label="เล่น / พักเพลง (Ctrl+P)")
        self.btn_stop = wx.Button(self.panel, label="หยุดเพลง")
        self.btn_prev = wx.Button(self.panel, label="เพลงก่อนหน้า (Ctrl+B)")
        self.btn_next = wx.Button(self.panel, label="เพลงถัดไป (Ctrl+N)")
        
        self.btn_play.Bind(wx.EVT_BUTTON, self._on_play_click)
        self.btn_stop.Bind(wx.EVT_BUTTON, self._on_stop_click)
        self.btn_prev.Bind(wx.EVT_BUTTON, self._on_prev_click)
        self.btn_next.Bind(wx.EVT_BUTTON, self._on_next_click)

        self.reader.bind_focus_announcement(self.btn_play, "ปุ่มเล่นหรือพักเพลงชั่วคราว คอนโทรลบวกพี")
        self.reader.bind_focus_announcement(self.btn_stop, "ปุ่มหยุดเครื่องเล่นเพลง")
        self.reader.bind_focus_announcement(self.btn_prev, "ปุ่มข้ามไปเล่นเพลงก่อนหน้า คอนโทรลบวกบี")
        self.reader.bind_focus_announcement(self.btn_next, "ปุ่มข้ามไปเล่นเพลงถัดไป คอนโทรลบวกเอ็น")

        # 2. ปรับความดังเพลง
        self.lbl_volume = wx.StaticText(self.panel, label=f"ความดังเพลง: {int(self.music.channel_volume * 100)}%")
        self.sld_volume = wx.Slider(self.panel, value=int(self.music.channel_volume * 100), minValue=0, maxValue=100, style=wx.SL_HORIZONTAL)
        self.sld_volume.Bind(wx.EVT_SLIDER, self._on_volume_scroll)
        self.reader.bind_slider_announcement(self.sld_volume, "ระดับเสียงเพลง", "เปอร์เซ็นต์")

        # โหมดการสุ่ม/วนซ้ำ (ย้ายขึ้นมาเพื่อปรับระดับ Tab Order ให้ตรงกับ Visual Layout)
        self.chk_shuffle = wx.CheckBox(self.panel, label="เล่นเพลงแบบสุ่ม (Shuffle)")
        self.chk_shuffle.SetValue(self.music.shuffle)
        self.chk_shuffle.Bind(wx.EVT_CHECKBOX, self._on_shuffle_toggle)
        self.reader.bind_checkbox_announcement(self.chk_shuffle, "สลับการเล่นสุ่มเพลง")

        # 3. เลือกเพลย์ลิสต์ และปุ่มสร้าง/ลบเพลย์ลิสต์
        self.choice_playlists = wx.Choice(self.panel, choices=[])
        self.choice_playlists.Bind(wx.EVT_CHOICE, self._on_playlist_select)
        self.reader.bind_choice_announcement(self.choice_playlists, "เลือกกลุ่มเพลย์ลิสต์ประวัติเพลง")
        
        self.btn_add_playlist = wx.Button(self.panel, label="สร้างเพลย์ลิสต์")
        self.btn_del_playlist = wx.Button(self.panel, label="ลบเพลย์ลิสต์")
        self.btn_add_playlist.Bind(wx.EVT_BUTTON, self._on_add_playlist_click)
        self.btn_del_playlist.Bind(wx.EVT_BUTTON, self._on_del_playlist_click)
        self.reader.bind_focus_announcement(self.btn_add_playlist, "ปุ่มสร้างกลุ่มเพลงสะสมใหม่")
        self.reader.bind_focus_announcement(self.btn_del_playlist, "ปุ่มลบกลุ่มเพลงสะสมปัจจุบัน")

        # 4. รายการเพลงในเพลย์ลิสต์ และปุ่มจัดการไฟล์เพลง
        self.list_songs = wx.ListBox(self.panel, style=wx.LB_SINGLE)
        self.list_songs.Bind(wx.EVT_LISTBOX_DCLICK, self._on_song_double_click)
        self.reader.bind_focus_announcement(self.list_songs, "รายการชื่อเพลงในเพลย์ลิสต์ปัจจุบัน ดับเบิ้ลคลิกหรือกดเอนเทอร์เพื่อเล่น")
        
        self.btn_add_songs = wx.Button(self.panel, label="เพิ่มเพลง (+)")
        self.btn_del_song = wx.Button(self.panel, label="ลบเพลง (-)")
        self.btn_add_songs.Bind(wx.EVT_BUTTON, self._on_add_songs_click)
        self.btn_del_song.Bind(wx.EVT_BUTTON, self._on_del_song_click)
        self.reader.bind_focus_announcement(self.btn_add_songs, "ปุ่มเพิ่มไฟล์เพลงจากคอมพิวเตอร์เข้าเพลย์ลิสต์ที่เลือก")
        self.reader.bind_focus_announcement(self.btn_del_song, "ปุ่มลบเพลงที่เลือกออกจากเพลย์ลิสต์")

        # 5. คิวเพลงที่ขอเข้ามาจากคนดูแชท
        self.list_requests = wx.ListBox(self.panel, style=wx.LB_SINGLE)
        self.reader.bind_focus_announcement(self.list_requests, "รายการแสดงคิวจองขอเพลงจากผู้ชมไลฟ์สด")

        # 6. ปุ่มควบคุมคิวขอเพลง
        self.btn_approve = wx.Button(self.panel, label="อนุมัติเพลง (Ctrl+Shift+Y)")
        self.btn_reject = wx.Button(self.panel, label="ปฏิเสธเพลง (Ctrl+Shift+R)")
        self.btn_skip_req = wx.Button(self.panel, label="ข้ามเพลงจอง")
        
        self.btn_approve.Bind(wx.EVT_BUTTON, self._on_approve_click)
        self.btn_reject.Bind(wx.EVT_BUTTON, self._on_reject_click)
        self.btn_skip_req.Bind(wx.EVT_BUTTON, self._on_skip_req_click)

        self.reader.bind_focus_announcement(self.btn_approve, "ปุ่มอนุมัติเพลงจองแชท คอนโทรลบวกชิฟต์บวกวาย")
        self.reader.bind_focus_announcement(self.btn_reject, "ปุ่มปฏิเสธแบนเพลงจองแชท คอนโทรลบวกชิฟต์บวกราร์")
        self.reader.bind_focus_announcement(self.btn_skip_req, "ปุ่มลัดข้ามเพลงคำขอปัจจุบัน")

    def _apply_layout(self):
        # จัดปุ่มควบคุมหลัก
        hbox_buttons = wx.BoxSizer(wx.HORIZONTAL)
        hbox_buttons.Add(self.btn_prev, 1, wx.ALL | wx.EXPAND, 3)
        hbox_buttons.Add(self.btn_play, 1, wx.ALL | wx.EXPAND, 3)
        hbox_buttons.Add(self.btn_stop, 1, wx.ALL | wx.EXPAND, 3)
        hbox_buttons.Add(self.btn_next, 1, wx.ALL | wx.EXPAND, 3)
        self.vbox.Add(hbox_buttons, 0, wx.EXPAND | wx.ALL, 5)

        # จัดแถบเสียงและเล่นสุ่ม
        hbox_settings = wx.BoxSizer(wx.HORIZONTAL)
        hbox_settings.Add(self.lbl_volume, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        hbox_settings.Add(self.sld_volume, 1, wx.ALL | wx.EXPAND, 5)
        hbox_settings.Add(self.chk_shuffle, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.vbox.Add(hbox_settings, 0, wx.EXPAND | wx.ALL, 5)

        # เพลย์ลิสต์
        self.vbox.Add(wx.StaticText(self.panel, label="เลือกกลุ่มเพลย์ลิสต์สะสม:"), 0, wx.ALL, 3)
        hbox_playlist = wx.BoxSizer(wx.HORIZONTAL)
        hbox_playlist.Add(self.choice_playlists, 1, wx.ALL | wx.EXPAND, 3)
        hbox_playlist.Add(self.btn_add_playlist, 0, wx.ALL | wx.EXPAND, 3)
        hbox_playlist.Add(self.btn_del_playlist, 0, wx.ALL | wx.EXPAND, 3)
        self.vbox.Add(hbox_playlist, 0, wx.EXPAND | wx.ALL, 5)

        # รายชื่อเพลง
        self.vbox.Add(wx.StaticText(self.panel, label="เพลงที่มีทั้งหมดในเพลย์ลิสต์ที่เลือก:"), 0, wx.ALL, 3)
        self.vbox.Add(self.list_songs, 1, wx.EXPAND | wx.ALL, 5)
        
        # จัดการไฟล์เพลง
        hbox_song_files = wx.BoxSizer(wx.HORIZONTAL)
        hbox_song_files.Add(self.btn_add_songs, 1, wx.ALL | wx.EXPAND, 3)
        hbox_song_files.Add(self.btn_del_song, 1, wx.ALL | wx.EXPAND, 3)
        self.vbox.Add(hbox_song_files, 0, wx.EXPAND | wx.ALL, 5)

        # คิวขอเพลง
        self.vbox.Add(wx.StaticText(self.panel, label="รายการคิวที่ผู้ชมจองเพลงเข้ามาสด (!เพลง):"), 0, wx.ALL, 3)
        self.vbox.Add(self.list_requests, 1, wx.EXPAND | wx.ALL, 5)

        # ปุ่มจัดการคิว
        hbox_req = wx.BoxSizer(wx.HORIZONTAL)
        hbox_req.Add(self.btn_approve, 1, wx.ALL | wx.EXPAND, 3)
        hbox_req.Add(self.btn_reject, 1, wx.ALL | wx.EXPAND, 3)
        hbox_req.Add(self.btn_skip_req, 1, wx.ALL | wx.EXPAND, 3)
        self.vbox.Add(hbox_req, 0, wx.EXPAND | wx.ALL, 5)

        self.panel.SetSizer(self.vbox)

    def _load_playlists_combo(self):
        """โหลดรายชื่อเพลย์ลิสต์ที่มีทั้งหมดลงคอมโบ"""
        names = list(self.music.playlists.keys())
        self.choice_playlists.Set(names)
        if self.music.current_playlist_name in names:
            idx = names.index(self.music.current_playlist_name)
            self.choice_playlists.SetSelection(idx)
        else:
            self.choice_playlists.SetSelection(0)

    def _update_song_list(self):
        """อัปเดตข้อมูลรายการชื่อเพลงลง ListBox"""
        tracks = self.music.playlists.get(self.music.current_playlist_name, [])
        song_names = [os.path.basename(t) for t in tracks]
        if not song_names:
            song_names = ["(ไม่พบไฟล์เพลงในเพลย์ลิสต์นี้)"]
        self.list_songs.Set(song_names)

    def _update_request_list(self):
        """ดึงคิวข้อเสนอเพลงแชทมาแสดง"""
        pending = self.music.get_pending_requests()
        items = []
        for r in pending:
            items.append(f"รหัส {r['id']}: เพลง {r['song']} (ขอโดย {r['user']})")
        
        if not items:
            items = ["(ยังไม่มีคิวขอเพลงค้างอยู่ในระบบ)"]
        self.list_requests.Set(items)

    # --- เหตุการณ์ Callback ---
    def _on_play_click(self, event: wx.Event):
        self.music.pause_or_resume()

    def _on_stop_click(self, event: wx.Event):
        self.music.stop_music()

    def _on_prev_click(self, event: wx.Event):
        self.music.prev_track()
        self._update_song_selection()

    def _on_next_click(self, event: wx.Event):
        self.music.next_track()
        self._update_song_selection()

    def _update_song_selection(self):
        """เน้นสีเพลงที่กําลังเล่นปัจจุบันใน ListBox"""
        tracks = self.music.playlists.get(self.music.current_playlist_name, [])
        if tracks and 0 <= self.music.current_song_idx < len(tracks):
            self.list_songs.SetSelection(self.music.current_song_idx)

    def _on_volume_scroll(self, event: wx.Event):
        val = self.sld_volume.GetValue()
        self.lbl_volume.SetLabel(f"ความดังเพลง: {val}%")
        self.music.set_volume(val / 100.0)

    def _on_playlist_select(self, event: wx.Event):
        name = self.choice_playlists.GetStringSelection()
        self.music.current_playlist_name = name
        self.music.current_song_idx = 0
        self._update_song_list()
        self.reader.announce_text(f"เปลี่ยนกลุ่มเพลย์ลิสต์สตรีมเป็น {name} สำเร็จค่ะ", 8)

    def _on_song_double_click(self, event: wx.Event):
        idx = self.list_history_idx = self.list_songs.GetSelection()
        tracks = self.music.playlists.get(self.music.current_playlist_name, [])
        if tracks and 0 <= idx < len(tracks):
            self.music.current_song_idx = idx
            self.music.play_song()

    def _on_shuffle_toggle(self, event: wx.Event):
        self.music.shuffle = self.chk_shuffle.GetValue()
        state = "สุ่มเพลงเปิดใช้งาน" if self.music.shuffle else "ปิดสุ่มเพลง"
        self.reader.announce_text(state, 8)

    def _on_approve_click(self, event: wx.Event):
        req_id = self._get_selected_request_id()
        if req_id > 0:
            success, msg = self.music.approve_viewer_request(req_id)
            self._update_request_list()
        else:
            self.reader.announce_text("กรุณาเลือกคิวจองขอเพลงในตารางล่างก่อนกดปุ่มค่ะ", 8)

    def _on_reject_click(self, event: wx.Event):
        req_id = self._get_selected_request_id()
        if req_id > 0:
            success, msg = self.music.reject_viewer_request(req_id)
            self._update_request_list()
        else:
            self.reader.announce_text("กรุณาเลือกคิวจองขอเพลงในตารางล่างก่อนกดปุ่มค่ะ", 8)

    def _on_skip_req_click(self, event: wx.Event):
        self.reader.announce_text("ข้ามเพลงจองสดในแชทปัจจุบันแล้วค่ะ", 8)
        self.music.next_track()

    def _get_selected_request_id(self) -> int:
        idx = self.list_requests.GetSelection()
        if idx == wx.NOT_FOUND:
            return -1
        
        pending = self.music.get_pending_requests()
        if 0 <= idx < len(pending):
            return pending[idx]["id"]
        return -1

    def _on_timer_tick(self, event: wx.TimerEvent):
        """สั่งเครื่องเล่นเพลงคอยตรวจสอบวิทยุและการอัปเดตไฟล์เพลงหมดแถว"""
        self.music.check_music_tick()
        # ทำการอัปเดตชื่อสิทธิ์เลือกเพลงที่เน้นสี
        if self.music.is_playing and not self.music.is_paused:
            tracks = self.music.playlists.get(self.music.current_playlist_name, [])
            if tracks and self.list_songs.GetSelection() != self.music.current_song_idx:
                self._update_song_selection()

    def _on_add_playlist_click(self, event: wx.Event):
        dlg = wx.TextEntryDialog(self, "ระบุชื่อเพลย์ลิสต์ใหม่ที่ต้องการสร้าง:", "สร้างเพลย์ลิสต์ใหม่")
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetValue().strip()
            if name:
                success = self.music.create_playlist(name)
                if success:
                    self._load_playlists_combo()
                    self.choice_playlists.SetStringSelection(name)
                    self.music.current_playlist_name = name
                    self.music.current_song_idx = 0
                    self._update_song_list()
                    self.reader.announce_text(f"สร้างเพลย์ลิสต์ {name} สำเร็จและเลือกใช้งานแล้วค่ะ", 8)
                else:
                    self.reader.announce_text("ชื่อเพลย์ลิสต์นี้มีอยู่แล้วในระบบค่ะ", 8)
        dlg.Destroy()

    def _on_del_playlist_click(self, event: wx.Event):
        name = self.choice_playlists.GetStringSelection()
        if name == "เพลงสำหรับไลฟ์":
            self.reader.announce_text("ไม่สามารถลบเพลย์ลิสต์หลัก เพลงสำหรับไลฟ์ ได้ค่ะ", 8)
            return

        dlg = wx.MessageDialog(self, f"คุณแน่ใจหรือไม่ที่จะลบเพลย์ลิสต์ '{name}' และรายการเพลงทั้งหมดในนี้?", "ยืนยันการลบ", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
        if dlg.ShowModal() == wx.ID_YES:
            self.music.delete_playlist(name)
            self._load_playlists_combo()
            self.music.current_playlist_name = "เพลงสำหรับไลฟ์"
            self.choice_playlists.SetStringSelection("เพลงสำหรับไลฟ์")
            self.music.current_song_idx = 0
            self._update_song_list()
            self.reader.announce_text(f"ลบเพลย์ลิสต์ {name} สำเร็จแล้วและสลับกลับสู่เพลย์ลิสต์เริ่มต้นค่ะ", 8)
        dlg.Destroy()

    def _on_add_songs_click(self, event: wx.Event):
        playlist_name = self.choice_playlists.GetStringSelection()
        dlg = wx.FileDialog(
            self, message="เลือกไฟล์เพลงเพื่อเพิ่มเข้าเพลย์ลิสต์",
            defaultFile="",
            wildcard="Audio files (*.mp3;*.wav;*.ogg)|*.mp3;*.wav;*.ogg",
            style=wx.FD_OPEN | wx.FD_MULTIPLE
        )
        if dlg.ShowModal() == wx.ID_OK:
            paths = dlg.GetPaths()
            for p in paths:
                self.music.add_track_to_playlist(playlist_name, p)
            self._update_song_list()
            self.reader.announce_text(f"เพิ่มเพลง {len(paths)} เพลงเข้าสู่เพลย์ลิสต์เรียบร้อยแล้วค่ะ", 8)
        dlg.Destroy()

    def _on_del_song_click(self, event: wx.Event):
        idx = self.list_songs.GetSelection()
        if idx == wx.NOT_FOUND:
            self.reader.announce_text("กรุณาเลือกเพลงที่จะลบจากรายการก่อนค่ะ", 8)
            return

        playlist_name = self.choice_playlists.GetStringSelection()
        tracks = self.music.playlists.get(playlist_name, [])
        if 0 <= idx < len(tracks):
            removed_song = os.path.basename(tracks[idx])
            tracks.pop(idx)
            self.music.save_all_playlists()
            self._update_song_list()
            self.reader.announce_text(f"ลบเพลง {removed_song[:-4] if '.' in removed_song else removed_song} สำเร็จแล้วค่ะ", 8)

    def _update_request_list_heartbeat(self):
        """เช็คเพื่อดึงค่าประวัติคำขอแชท (Heartbeat)"""
        self._update_request_list()

    def _on_close(self, event: wx.CloseEvent):
        self.timer.Stop()
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
                self.SetSize((800, 850))
            else:
                self.SetSize((650, 700))
                
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

