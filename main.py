import wx
import os
import sys

# ดึงตำแหน่งโฟลเดอร์หลัก
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.dat")

def ensure_folders_exist():
    """สร้างโฟลเดอร์ที่จำเป็นทั้งหมดหากยังไม่มี"""
    if getattr(sys, 'frozen', False):
        target_dir = os.path.join(BASE_DIR, "_internal")
    else:
        target_dir = BASE_DIR
        
    folders = ["logs", "plugins"]
    for folder in folders:
        path = os.path.join(target_dir, folder)
        if not os.path.exists(path):
            os.makedirs(path)

def main():
    # 1. ตรวจสอบโฟลเดอร์ในระบบ
    ensure_folders_exist()
    
    # โหลดการตั้งค่าภาษา
    from core.i18n import load_lang_from_config, tr
    load_lang_from_config(CONFIG_FILE)
    
    # 2. เริ่มแอปพลิเคชัน wxPython
    app = wx.App()
    
    # ดึงหัวเรื่องหน้าจอหลัก
    from ui.main_window import MainWindow
    frame = MainWindow(tr("TITLE_MAIN"), CONFIG_FILE)
    
    app.MainLoop()

if __name__ == "__main__":
    main()
