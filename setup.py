import os
import sys
import shutil
import subprocess

def build_executable():
    """
    สคริปต์คอมไพล์และสร้างตัวแพ็คเกจเดี่ยว (Build Setup)
    ใช้ PyInstaller ในการคอมไพล์ main.py เป็น executable บน Windows
    และคัดลอกไฟล์ทรัพยากรที่จำเป็นไปวางเคียงข้าง
    """
    print("=== เริ่มกระบวนการคัดลอกและสร้างโปรแกรมแพ็คเกจ ===")
    
    # 1. รันคำสั่งคอมไพล์ผ่าน PyInstaller
    # --noconsole สำหรับรันเฉพาะ GUI ซ่อนหน้าจอดำ (Console)
    # --onefile สำหรับสร้างตัวโปรแกรมเดียว
    command = [
        "pyinstaller",
        "--noconsole",
        "--name=TikTokLiveReaderThai",
        "--clean",
        "-y",
        "--paths=.",
        "--hidden-import=ui.main_window",
        "--hidden-import=core.tiktok_manager",
        "--hidden-import=tts.audio_queue",
        "--hidden-import=database.db_helper",
        "--hidden-import=accessibility.hotkey_manager",
        "--hidden-import=accessibility.reader_helper",
        "--hidden-import=ui.settings_dialog",
        "--hidden-import=ui.stats_window",
        "--hidden-import=ui.music_window",
        "--hidden-import=ui.soundboard_window",
        "--hidden-import=ui.radio_window",
        "--hidden-import=services.point_service",
        "--hidden-import=services.game_service",
        "--hidden-import=services.music_service",
        "--hidden-import=services.radio_service",
        "--hidden-import=services.soundboard_service",
        "--hidden-import=services.ai_service",
        "--hidden-import=core.command_handler",
        "--hidden-import=core.licensing",
        "--hidden-import=core.i18n",
        "main.py"
    ]
    
    try:
        print(f"รันคำสั่งคอมไพล์หลัก: {' '.join(command)}")
        subprocess.check_call(command)
        print("คอมไพล์โค้ดหลักเสร็จสิ้น!")
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการรัน PyInstaller: {e}")
        print("กรุณาตรวจสอบว่าติดตั้ง pyinstaller แล้วผ่าน pip install pyinstaller")
        return False

    # 1.5 รันคำสั่งคอมไพล์สำหรับ updater.py เป็น OneFile Console
    updater_command = [
        "pyinstaller",
        "--console",
        "--onefile",
        "--name=updater",
        "--clean",
        "-y",
        "--paths=.",
        "updater.py"
    ]
    try:
        print(f"รันคำสั่งคอมไพล์ Updater: {' '.join(updater_command)}")
        subprocess.check_call(updater_command)
        print("คอมไพล์ Updater เสร็จสิ้น!")
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการรัน PyInstaller สำหรับ Updater: {e}")
        return False

    # 2. คัดลอกทรัพยากรไปวางที่โฟลเดอร์ dist/
    dist_dir = os.path.join("dist", "TikTokLiveReaderThai")
    if not os.path.exists(dist_dir):
        dist_dir = "dist"
    
    resources = [
        ("config.dat", True),
        ("symbols-en.dic", True),
        ("nvdaControllerClient_x64.dll", True),
        ("คู่มือภาษาไทย.txt", True),
        ("คู่มือคนตาบอด.txt", True),
        ("sounds", False)  # โฟลเดอร์เสียง
    ]

    print("\nคัดลอกไฟล์ระบบเคียงข้างตัวโปรแกรม .exe:")
    internal_dir = os.path.join(dist_dir, "_internal")
    
    for res_name, is_file in resources:
        src_path = res_name
        
        # คัดลอกไปที่ _internal หากเป็นไฟล์/โฟลเดอร์ระบบที่ไม่จำเป็นต้องโชว์ให้ผู้ใช้เห็น
        is_internal = res_name in ("symbols-en.dic", "nvdaControllerClient_x64.dll", "sounds")
        if is_internal and os.path.exists(internal_dir):
            dest_path = os.path.join(internal_dir, res_name)
        else:
            dest_path = os.path.join(dist_dir, res_name)
        
        if not os.path.exists(src_path):
            print(f"คำเตือน: ไม่พบไฟล์ต้นทาง {src_path} ข้ามการคัดลอก")
            continue
            
        try:
            if is_file:
                shutil.copy2(src_path, dest_path)
                print(f"  [สำเร็จ] คัดลอกไฟล์ {src_path} -> {dest_path}")
            else:
                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path)
                shutil.copytree(src_path, dest_path)
                print(f"  [สำเร็จ] คัดลอกโฟลเดอร์ {src_path} -> {dest_path}")
        except Exception as e:
            print(f"  [ล้มเหลว] ไม่สามารถคัดลอก {src_path}: {e}")

    # คัดลอก updater.exe ที่คอมไพล์แล้วเข้าไปในโฟลเดอร์ _internal
    src_updater = os.path.join("dist", "updater.exe")
    dest_updater = os.path.join(internal_dir, "updater.exe")
    if os.path.exists(src_updater) and os.path.exists(internal_dir):
        try:
            shutil.copy2(src_updater, dest_updater)
            print(f"  [สำเร็จ] คัดลอกตัวอัปเดต {src_updater} -> {dest_updater}")
            
            # ลบไฟล์ตัวเลือกจำลอง/และ build directory ที่ไม่ใช้ออกเพื่อความสะอาดของโปรเจกต์
            os.remove(src_updater)
            shutil.rmtree(os.path.join("build", "updater"), ignore_errors=True)
            shutil.rmtree(os.path.join("dist", "updater"), ignore_errors=True)
        except Exception as e:
            print(f"  [ล้มเหลว] ไม่สามารถย้ายหรือทำความสะอาดตัวอัปเดต: {e}")

    print("\n=== การแพ็คเกจเสร็จสิ้นสมบูรณ์! ===")
    print("ตัวโปรแกรมพร้อมรันและทรัพยากรทั้งหมดถูกจัดไว้ในโฟลเดอร์ dist/")
    return True

if __name__ == "__main__":
    build_executable()
