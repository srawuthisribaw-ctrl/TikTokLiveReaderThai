import wx
from typing import Callable, Dict

class HotkeyManager:
    """
    คลาสสำหรับจัดการลงทะเบียนปุ่มลัดระบบ (Global Hotkeys) บนระบบปฏิบัติการ Windows
    เพื่อให้ผู้จัดไลฟ์ตาบอดสามารถควบคุมโปรแกรมได้โดยไม่ต้องสลับหน้าจอ (Minimize Mode)
    """
    # นิยามโค้ดปุ่มลัด
    HOTKEYS = {
        101: (wx.MOD_NONE, wx.WXK_F1, "F1: อ่านสถานะ"),
        102: (wx.MOD_NONE, wx.WXK_F2, "F2: เริ่มเชื่อมต่อ"),
        103: (wx.MOD_NONE, wx.WXK_F3, "F3: หยุดเชื่อมต่อ"),
        104: (wx.MOD_NONE, wx.WXK_F4, "F4: สลับอ่านแชท"),
        105: (wx.MOD_NONE, wx.WXK_F5, "F5: สลับอ่านคนเข้า"),
        106: (wx.MOD_NONE, wx.WXK_F6, "F6: สลับอ่านกิฟต์"),
        107: (wx.MOD_NONE, wx.WXK_F7, "F7: อ่านอันดับผู้ชม"),
        108: (wx.MOD_NONE, wx.WXK_F8, "F8: อ่านตัวเลขสถิติ"),
        109: (wx.MOD_NONE, wx.WXK_F9, "F9: ตั้งค่าเสียง"),
        110: (wx.MOD_NONE, wx.WXK_F10, "F10: ตั้งค่าโปรแกรม"),
        111: (wx.MOD_NONE, wx.WXK_F11, "F11: บันทึก Log ไลฟ์"),
        112: (wx.MOD_NONE, wx.WXK_F12, "F12: อ่านสรุปไลฟ์สด"),
        113: (wx.MOD_CONTROL | wx.MOD_SHIFT, ord('A'), "Ctrl+Shift+A: ถามผู้ช่วย AI"),
        114: (wx.MOD_CONTROL | wx.MOD_SHIFT, ord('S'), "Ctrl+Shift+S: อ่านสถิติสดด่วน"),
        # Music Player
        115: (wx.MOD_CONTROL, ord('P'), "Ctrl+P: เล่น/หยุดเพลง"),
        116: (wx.MOD_CONTROL, ord('N'), "Ctrl+N: เพลงถัดไป"),
        117: (wx.MOD_CONTROL, ord('B'), "Ctrl+B: เพลงก่อนหน้า"),
        118: (wx.MOD_CONTROL, ord('M'), "Ctrl+M: ปิดเสียงเพลง"),
        119: (wx.MOD_CONTROL | wx.MOD_SHIFT, ord('M'), "Ctrl+Shift+M: จัดการเพลย์ลิสต์"),
        # Soundboard (Alt+F1 - Alt+F10)
        120: (wx.MOD_ALT, wx.WXK_F1, "Alt+F1: หัวเราะ"),
        121: (wx.MOD_ALT, wx.WXK_F2, "Alt+F2: ปรบมือ"),
        122: (wx.MOD_ALT, wx.WXK_F3, "Alt+F3: เชียร์"),
        123: (wx.MOD_ALT, wx.WXK_F4, "Alt+F4: ว้าว"),
        124: (wx.MOD_ALT, wx.WXK_F5, "Alt+F5: ตึ่งโป๊ะ"),
        125: (wx.MOD_ALT, wx.WXK_F6, "Alt+F6: กลองม้วน"),
        126: (wx.MOD_ALT, wx.WXK_F7, "Alt+F7: ชนะ"),
        127: (wx.MOD_ALT, wx.WXK_F8, "Alt+F8: แพ้"),
        128: (wx.MOD_ALT, wx.WXK_F9, "Alt+F9: สุ่มเสียง"),
        129: (wx.MOD_ALT, wx.WXK_F10, "Alt+F10: เปิดหน้าต่างซาวด์บอร์ด"),
        130: (wx.MOD_CONTROL | wx.MOD_SHIFT, ord('R'), "Ctrl+Shift+R: เปิดเครื่องเล่นวิทยุ")
    }

    def __init__(self, frame: wx.Frame):
        self.frame = frame
        self.callbacks: Dict[int, Callable[[], None]] = {}
        
        # ผูกเหตุการณ์คีย์ลัดเข้ากับระบบ wx
        self.frame.Bind(wx.EVT_HOTKEY, self._on_hotkey_triggered)

    def register_all_hotkeys(self, callbacks_map: Dict[int, Callable[[], None]]):
        """
        ลงทะเบียนปุ่มคีย์ลัดทั้งหมดในระบบหลัก
        callbacks_map: แผนผังแมปจาก hotkey_id ไปยังฟังก์ชัน Callback
        """
        self.callbacks = callbacks_map
        
        for hotkey_id, (modifiers, vk_code, desc) in self.HOTKEYS.items():
            success = self.frame.RegisterHotKey(hotkey_id, modifiers, vk_code)
            if not success:
                print(f"Failed to register global hotkey: {desc}")

    def unregister_all_hotkeys(self):
        """ยกเลิกการลงทะเบียนปุ่มลัดเมื่อปิดโปรแกรม"""
        for hotkey_id in self.HOTKEYS:
            try:
                self.frame.UnregisterHotKey(hotkey_id)
            except Exception:
                pass

    def _on_hotkey_triggered(self, event: wx.Event):
        """ประมวลผลเมื่อมีการกดปุ่มลัดตรง"""
        hotkey_id = event.GetId()
        if hotkey_id in self.callbacks:
            try:
                # เรียกใช้ Callback
                self.callbacks[hotkey_id]()
            except Exception as e:
                print(f"Error executing hotkey callback: {e}")
        event.Skip()
