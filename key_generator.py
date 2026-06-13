import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization

PRIVATE_KEY_PEM = """-----BEGIN PRIVATE KEY-----
MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBANYGSvDqDz8tTQSG
Kl7rOiNt83uN8MVa/LG41GLLi9wzrhxzNUXSH/Gf0s/VL1hgFEbpPiKPz/ZVKbGv
2v/o/tLnm04cPojOGM8s0WfwL2hPaZ2CG4VtnKFi33bkuISNMMijg4rS9cl/9FS4
nDnU2Puhyx5zHbChn4CK8Hqp3cstAgMBAAECgYEAp7KAj+pmDfOZ8FyL4JnhkRc6
++nI6WqUq1COoeapbN3VpBcle9LcEsBPN2fsVAvcd3+UnxIeOf6az85iA7j1yK6t
SDedMXJA1Z0tzq0/dSFaoT8ycDZ6JMIyAk20trwUs3BlqQ8ns/AE0czMlTvrlPvS
aCW99XH8o7swkZegVCUCQQDughBQU4Zv8vjlN4gYThKoKt1N+xy8+t1zrbAUvwOH
SWiTXk7LaKX1WXsRB0hrGHqMuKz9oA+Un+7hsUk9RhznAkEA5biOm9Z26/plU+cW
X0e8Vh7d6CmGZxthaci4DWdDWdlb5lz5CwCZDR8FdRQuvqR8wg9WZyreBCixsUga
VhggywJAMEwIL6vqQksqWYg4N+u/XWxoqfzaoe4O3/jg+iJ//WpBEe57+Da1vIwl
Hpqh8IXhcxOGfEloPklwnyU+VnkXKwJBAORXAfHnSMghWcz/e55z2MIl5l+Zvw4I
Clky+bfg9/J8ervNmIMWMgv31N3elORM7fGbe0ALPSoXJSFZ0UvYqecCQDXE05Vp
0filV1SSpOw4DSYDuywu6IW6L+ohFTBni/b7It2L+8bjELG3/V3tWFCmquclYiLb
6+DXoZcntqZ16YY=
-----END PRIVATE KEY-----"""

def speak_out(text):
    try:
        import win32com.client
        voice = win32com.client.Dispatch("SAPI.SpVoice")
        voice.Speak(text)
    except Exception:
        pass

def generate_key(machine_id: str) -> str:
    machine_id = machine_id.strip().lower()
    private_key = serialization.load_pem_private_key(
        PRIVATE_KEY_PEM.encode(),
        password=None
    )
    signature = private_key.sign(
        machine_id.encode('utf-8'),
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')

def copy_to_clipboard(text: str) -> bool:
    # วิธีที่ 1: ใช้ ctypes เรียก Windows API โดยตรง (ปลอดภัยบน 64-bit และไม่ต้องลงไลบรารีเพิ่ม)
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        user32.OpenClipboard.argtypes = [wintypes.HWND]
        user32.OpenClipboard.restype = wintypes.BOOL

        user32.EmptyClipboard.argtypes = []
        user32.EmptyClipboard.restype = wintypes.BOOL

        user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        user32.SetClipboardData.restype = wintypes.HANDLE

        user32.CloseClipboard.argtypes = []
        user32.CloseClipboard.restype = wintypes.BOOL

        kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        kernel32.GlobalAlloc.restype = wintypes.HGLOBAL

        kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalLock.restype = wintypes.LPVOID

        kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalUnlock.restype = wintypes.BOOL

        GMEM_MOVEABLE = 0x0002
        CF_UNICODETEXT = 13

        if user32.OpenClipboard(None):
            try:
                user32.EmptyClipboard()
                encoded = (text + '\0').encode('utf-16le')
                h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
                if h_mem:
                    ptr = kernel32.GlobalLock(h_mem)
                    if ptr:
                        try:
                            ctypes.memmove(ptr, encoded, len(encoded))
                        finally:
                            kernel32.GlobalUnlock(h_mem)
                        if user32.SetClipboardData(CF_UNICODETEXT, h_mem):
                            user32.CloseClipboard()
                            return True
            finally:
                user32.CloseClipboard()
    except Exception:
        pass

    # วิธีที่ 2: ใช้ win32clipboard (หากมี pywin32 ในเครื่อง)
    try:
        import win32clipboard
        import win32con
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        return True
    except Exception:
        pass

    # วิธีที่ 3: เรียกใช้ clip.exe ของ Windows (ไม่ต้องใช้ shell=True เพื่อความปลอดภัยและเสถียรภาพ)
    try:
        import subprocess
        subprocess.run(['clip'], input=text.encode('utf-8'), check=True, creationflags=0x08000000) # CREATE_NO_WINDOW
        return True
    except Exception:
        pass

    # วิธีที่ 4: ใช้ tkinter เผื่อกรณีอื่นๆ (แต่ต้องระวังปัญหากล่องข้อความหายเมื่อปิดหน้าต่าง)
    try:
        import tkinter as tk
        r = tk.Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text)
        r.update()
        # ไม่ทำ r.destroy() ทันทีเพื่อให้ระบบปฏิบัติการดึงข้อมูลจากคลิปบอร์ดได้ทัน
        # แต่เพื่อความปลอดภัยเราจะปล่อยไว้สักครู่แล้วค่อยปิด หรือไม่ทำลายจนกว่าจะจบโปรแกรม
        return True
    except Exception:
        pass

    return False

def main():
    print("=== โปรแกรมสร้างรหัสเปิดใช้งาน (Activation Key Generator) ===")
    speak_out("โปรแกรมสร้างรหัสเปิดใช้งาน")
    
    try:
        machine_id = input("ป้อนรหัสประจำเครื่องของลูกค้า (Machine ID): ").strip()
        if not machine_id:
            print("ข้อผิดพลาด: รหัสประจำเครื่องห้ามว่างเปล่า")
            speak_out("รหัสประจำเครื่องห้ามว่างเปล่าค่ะ")
            return
            
        activation_key = generate_key(machine_id)
        
        print("\n------------------------------------------------------------")
        print("รหัสเปิดใช้งาน (Activation Key) สำหรับลูกค้า:")
        print(activation_key)
        print("------------------------------------------------------------\n")
        
        # คัดลอกลงคลิปบอร์ด
        if copy_to_clipboard(activation_key):
            print("คัดลอกรหัสเปิดใช้งานลงในคลิปบอร์ดให้เรียบร้อยแล้ว!")
            speak_out("สร้างรหัสและคัดลอกลงคลิปบอร์ดสำเร็จแล้วค่ะ")
        else:
            print("กรุณาคัดลอกรหัสเปิดใช้งานด้านบนส่งให้ลูกค้าด้วยตัวเอง")
            speak_out("สร้างรหัสสำเร็จแล้วค่ะ กรุณาคัดลอกด้วยตัวเองค่ะ")
            
    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {e}")
        speak_out("เกิดข้อผิดพลาดในการสร้างรหัสค่ะ")
    finally:
        # ป้องกันไม่ให้หน้าต่างหน้าจอ Command Prompt ปิดตัวลงทันทีในระบบ Windows
        input("\nกดปุ่ม Enter เพื่อปิดโปรแกรม...")

if __name__ == "__main__":
    main()
