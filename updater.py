import os
import sys
import time
import requests
import zipfile
import subprocess
import shutil

UPDATE_URL = "https://is.gd/ttupdate"
DOWNLOAD_EXE_URL = "https://github.com/ekarinyuri/TiktokUtilities/releases/latest/download/TiktokUtilities.exe"

def run_update():
    """
    ระบบตรวจสอบและดาวน์โหลดการอัปเดตอัตโนมัติ (Auto Updater)
    ดาวน์โหลดและทับตัวโปรแกรมหลัก
    """
    print("=== เริ่มการตรวจสอบการอัปเดตระบบ ===")
    time.sleep(1) # หน่วงเวลาเพื่อให้ตัวหลักปิดการทำงานเสร็จสิ้น
    
    try:
        # 1. เช็คเวอร์ชันล่าสุด
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(UPDATE_URL, headers=headers, timeout=5)
        latest_ver = response.text.strip()
        print(f"รุ่นล่าสุดที่มีอยู่: {latest_ver}")
    except Exception as e:
        print(f"ล้มเหลวในการดึงเวอร์ชันล่าสุด: {e}")
        time.sleep(3)
        return

    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    exe_name = os.path.join(base_dir, "TikTokLiveReaderThai.exe")
    backup_name = os.path.join(base_dir, "TikTokLiveReaderThai.bak")

    print("กำลังพยายามดาวน์โหลดตัวโปรแกรมรุ่นปรับปรุง...")
    try:
        # จำลองการดาวน์โหลดโปรแกรมเวอร์ชันล่าสุด
        # ในสถานการณ์จริง จะดาวน์โหลดผ่าน DOWNLOAD_EXE_URL
        r = requests.get(DOWNLOAD_EXE_URL, headers=headers, stream=True, timeout=30)
        if r.status_code == 200:
            # สำรองไฟล์ exe ตัวเดิม
            if os.path.exists(exe_name):
                if os.path.exists(backup_name):
                    os.remove(backup_name)
                os.rename(exe_name, backup_name)
                
            # บันทึกไฟล์ที่ดาวน์โหลดมาใหม่
            with open(exe_name, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print("การดาวน์โหลดเสร็จสมบูรณ์!")
            
            # ลบไฟล์สำรองออก
            if os.path.exists(backup_name):
                os.remove(backup_name)
        else:
            print(f"ล้มเหลวในการดาวน์โหลดไฟล์: HTTP {r.status_code}")
            # กู้คืนไฟล์สำรองหากมี
            if os.path.exists(backup_name) and not os.path.exists(exe_name):
                os.rename(backup_name, exe_name)
    except Exception as e:
        print(f"เกิดข้อผิดพลาดระหว่างดาวน์โหลด: {e}")
        # กู้คืนไฟล์สำรองหากมี
        if os.path.exists(backup_name) and not os.path.exists(exe_name):
            os.rename(backup_name, exe_name)
        time.sleep(3)
        return

    # 3. รันตัวโปรแกรมหลักใหม่หลังอัปเดตเสร็จ
    if os.path.exists(exe_name):
        print("กำลังบูตเปิดโปรแกรมหลังอัปเดต...")
        subprocess.Popen([exe_name])
    else:
        # สำหรับโหมดโค้ดต้นฉบับ รัน main.py แทน
        print("บูตในโหมดนักพัฒนาซอร์สโค้ด...")
        subprocess.Popen([sys.executable, os.path.join(base_dir, "main.py")])
        
    print("อัปเดตเสร็จสิ้น!")

if __name__ == "__main__":
    run_update()
