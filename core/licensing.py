import os
import sys
import json
import winreg
import base64
import wx
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization

PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDWBkrw6g8/LU0Ehipe6zojbfN7
jfDFWvyxuNRiy4vcM64cczVF0h/xn9LP1S9YYBRG6T4ij8/2VSmxr9r/6P7S55tO
HD6IzhjPLNFn8C9oT2mdghuFbZyhYt925LiEjTDIo4OK0vXJf/RUuJw51Nj7ocse
cx2woZ+AivB6qd3LLQIDAQAB
-----END PUBLIC KEY-----"""

def speak_out(text):
    try:
        import win32com.client
        voice = win32com.client.Dispatch("SAPI.SpVoice")
        voice.Speak(text)
    except Exception:
        pass

def get_machine_guid() -> str:
    try:
        registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
        value, regtype = winreg.QueryValueEx(registry_key, "MachineGuid")
        winreg.CloseKey(registry_key)
        return str(value).strip().lower()
    except Exception:
        # Fallback to UUID node if registry access fails
        import uuid
        return str(uuid.getnode()).strip().lower()

def verify_key(machine_id: str, activation_key: str) -> bool:
    try:
        public_key = serialization.load_pem_public_key(PUBLIC_KEY_PEM.encode())
        sig_bytes = base64.b64decode(activation_key.strip())
        public_key.verify(
            sig_bytes,
            machine_id.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False

class ActivationDialog(wx.Dialog):
    def __init__(self, parent, machine_id):
        super().__init__(parent, title="การเปิดใช้งานโปรแกรม (Product Activation)", size=(500, 320))
        self.machine_id = machine_id
        self.activation_successful = False
        
        self.InitUI()
        self.Centre()
        
        # ประกาศเสียงพูดแจ้งเตือนเมื่อหน้าต่างเปิด
        wx.CallAfter(speak_out, "โปรแกรมนี้ยังไม่ได้เปิดใช้งาน กรุณาคัดลอกรหัสประจำเครื่องส่งให้ผู้พัฒนาเพื่อรับรหัสเปิดใช้งานค่ะ")

    def InitUI(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # คำอธิบาย
        lbl_info = wx.StaticText(panel, label="โปรแกรมยังไม่ได้เปิดใช้งาน กรุณาส่งรหัสประจำเครื่องให้ผู้พัฒนาเพื่อขอรหัสเปิดใช้งาน")
        vbox.Add(lbl_info, 0, wx.ALL | wx.EXPAND, 15)

        # รหัสประจำเครื่อง (Machine ID)
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        lbl_mid = wx.StaticText(panel, label="รหัสประจำเครื่อง:")
        hbox1.Add(lbl_mid, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        
        self.txt_mid = wx.TextCtrl(panel, value=self.machine_id, style=wx.TE_READONLY)
        hbox1.Add(self.txt_mid, 1, wx.EXPAND)
        
        btn_copy = wx.Button(panel, label="คัดลอกรหัสประจำเครื่อง")
        btn_copy.Bind(wx.EVT_BUTTON, self.OnCopy)
        hbox1.Add(btn_copy, 0, wx.LEFT, 10)
        vbox.Add(hbox1, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 15)

        # ช่องใส่รหัสเปิดใช้งาน (Activation Key)
        vbox.AddSpacer(15)
        lbl_key = wx.StaticText(panel, label="กรอกรหัสเปิดใช้งาน (Activation Key):")
        vbox.Add(lbl_key, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 15)
        
        self.txt_key = wx.TextCtrl(panel, style=wx.TE_MULTILINE, size=(-1, 60))
        vbox.Add(self.txt_key, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 15)

        # ปุ่มตกลงและยกเลิก
        vbox.AddSpacer(20)
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        
        btn_activate = wx.Button(panel, label="เปิดใช้งาน")
        btn_activate.Bind(wx.EVT_BUTTON, self.OnActivate)
        hbox2.Add(btn_activate, 0, wx.RIGHT, 15)
        
        btn_exit = wx.Button(panel, label="ปิดโปรแกรม")
        btn_exit.Bind(wx.EVT_BUTTON, self.OnExit)
        hbox2.Add(btn_exit, 0)
        
        vbox.Add(hbox2, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 15)

        panel.SetSizer(vbox)

    def OnCopy(self, event):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.machine_id))
            wx.TheClipboard.Close()
            speak_out("คัดลอกรหัสประจำเครื่องลงคลิปบอร์ดแล้วค่ะ")
            wx.MessageBox("คัดลอกรหัสประจำเครื่องลงคลิปบอร์ดเรียบร้อยแล้ว", "สำเร็จ", wx.OK | wx.ICON_INFORMATION)

    def OnActivate(self, event):
        key = self.txt_key.GetValue().strip()
        if not key:
            speak_out("กรุณากรอกรหัสเปิดใช้งานค่ะ")
            wx.MessageBox("กรุณากรอกรหัสเปิดใช้งาน", "ข้อผิดพลาด", wx.OK | wx.ICON_WARNING)
            return

        if verify_key(self.machine_id, key):
            self.activation_successful = True
            speak_out("เปิดใช้งานโปรแกรมสำเร็จแล้วค่ะ ยินดีต้อนรับเข้าใช้งานค่ะ")
            wx.MessageBox("เปิดใช้งานโปรแกรมสำเร็จแล้ว! ขอบคุณที่สนับสนุนครับ", "สำเร็จ", wx.OK | wx.ICON_INFORMATION)
            self.EndModal(wx.ID_OK)
        else:
            speak_out("รหัสเปิดใช้งานไม่ถูกต้อง กรุณาตรวจสอบรหัสหรือติดต่อผู้พัฒนาค่ะ")
            wx.MessageBox("รหัสเปิดใช้งานไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง", "ข้อผิดพลาด", wx.OK | wx.ICON_ERROR)

    def OnExit(self, event):
        self.EndModal(wx.ID_CANCEL)

class LicenseManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.machine_id = get_machine_guid()

    def is_activated(self) -> bool:
        # ตรวจสอบว่ามีคีย์เปิดใช้งานที่ถูกต้องบันทึกอยู่หรือไม่
        activation_key = ""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                activation_key = cfg.get("activation_key", "")
            except Exception:
                pass
        return bool(activation_key and verify_key(self.machine_id, activation_key))

    def check_activation_flow(self) -> bool:
        # 1. โหลดคีย์เดิมจาก config.dat
        activation_key = ""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                activation_key = cfg.get("activation_key", "")
            except Exception:
                pass

        # 2. ตรวจสอบคีย์เดิม
        if activation_key and verify_key(self.machine_id, activation_key):
            return True

        # 3. หากคีย์ไม่ถูกต้องหรือไม่มี ให้ขึ้นหน้าจอลงทะเบียน
        dialog = ActivationDialog(None, self.machine_id)
        result = dialog.ShowModal()
        
        if result == wx.ID_OK and dialog.activation_successful:
            # บันทึกคีย์ใหม่ลง config.dat
            try:
                cfg = {}
                if os.path.exists(self.config_path):
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                
                cfg["activation_key"] = dialog.txt_key.GetValue().strip()
                
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=4, ensure_ascii=False)
                return True
            except Exception as e:
                wx.MessageBox(f"เกิดข้อผิดพลาดในการบันทึกรหัสเปิดใช้งาน: {e}", "ข้อผิดพลาด", wx.OK | wx.ICON_ERROR)
                return False
        
        return False
