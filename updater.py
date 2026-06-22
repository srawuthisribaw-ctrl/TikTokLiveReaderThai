import os
import sys
import time
import requests
import zipfile
import subprocess
import shutil

UPDATE_URL = "https://raw.githubusercontent.com/srawuthisribaw-ctrl/TikTokLiveReaderThai/main/version.txt"
DOWNLOAD_ZIP_URL = "https://github.com/srawuthisribaw-ctrl/TikTokLiveReaderThai/releases/latest/download/TikTokLiveReaderThai.zip"

def run_update():
    """
    ระบบตรวจสอบและดาวน์โหลดการอัปเดตอัตโนมัติ (Auto Updater)
    ดาวน์โหลดไฟล์ ZIP และทับตัวโปรแกรมพร้อมทรัพยากรทั้งหมด
    """
    print("=== เริ่มการตรวจสอบการอัปเดตระบบ ===")
    time.sleep(1.5) # หน่วงเวลาเพื่อให้ตัวหลักปิดการทำงานเสร็จสิ้น
    
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        # 1. เช็คเวอร์ชันล่าสุด
        response = requests.get(UPDATE_URL, headers=headers, timeout=5)
        latest_ver = response.text.strip()
        print(f"รุ่นล่าสุดที่มีอยู่: {latest_ver}")
    except Exception as e:
        print(f"ล้มเหลวในการดึงเวอร์ชันล่าสุด: {e}")
        time.sleep(3)
        return

    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
        if os.path.basename(base_dir).lower() == "_internal":
            base_dir = os.path.dirname(base_dir)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    zip_path = os.path.join(base_dir, "update.zip")
    temp_extract_dir = os.path.join(base_dir, "temp_update")

    print("กำลังดาวน์โหลดแพ็คเกจโปรแกรมรุ่นปรับปรุง...")
    try:
        r = requests.get(DOWNLOAD_ZIP_URL, headers=headers, stream=True, timeout=60)
        if r.status_code == 200:
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print("ดาวน์โหลดแพ็คเกจสำเร็จ! เริ่มทำการแตกไฟล์...")
            
            # เคลียร์โฟลเดอร์ชั่วคราวเก่าถ้ามี
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
            
            # แตกไฟล์ zip
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)
            
            # ลบไฟล์ zip ทันทีหลังแตกเสร็จ
            try:
                os.remove(zip_path)
            except Exception:
                pass
                
            # ค้นหาตำแหน่งโฟลเดอร์ต้นทางในการคัดลอก
            src_dir = temp_extract_dir
            subdirs = os.listdir(temp_extract_dir)
            if len(subdirs) == 1 and os.path.isdir(os.path.join(temp_extract_dir, subdirs[0])):
                src_dir = os.path.join(temp_extract_dir, subdirs[0])
                
            print("กำลังติดตั้งและอัปเดตไฟล์ระบบ...")
            
            # ฟังก์ชันคัดลอกทับไฟล์แบบวนซ้ำ
            def merge_dirs(src, dst):
                if os.path.isdir(src):
                    if not os.path.exists(dst):
                        os.makedirs(dst)
                    for item in os.listdir(src):
                        s = os.path.join(src, item)
                        d = os.path.join(dst, item)
                        merge_dirs(s, d)
                else:
                    # ป้องกันการคัดลอกทับตัว updater.exe ที่กำลังรันอยู่
                    if os.path.basename(src).lower() == "updater.exe":
                        return
                    try:
                        if os.path.exists(dst):
                            os.remove(dst)
                        shutil.copy2(src, dst)
                    except Exception as copy_err:
                        print(f"ข้ามไฟล์เนื่องจากมีข้อผิดพลาด: {src} -> {copy_err}")
            
            merge_dirs(src_dir, base_dir)
            
            # ลบโฟลเดอร์ชั่วคราวออก
            shutil.rmtree(temp_extract_dir, ignore_errors=True)
            print("การอัปเดตไฟล์เสร็จสมบูรณ์!")
            
        else:
            print(f"ล้มเหลวในการดาวน์โหลดไฟล์อัปเดต: HTTP {r.status_code}")
            time.sleep(3)
            return
            
    except Exception as e:
        print(f"เกิดข้อผิดพลาดระหว่างการอัปเดตระบบ: {e}")
        shutil.rmtree(temp_extract_dir, ignore_errors=True)
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except Exception:
                pass
        time.sleep(3)
        return

    # 3. รันตัวโปรแกรมหลักใหม่หลังอัปเดตเสร็จ
    exe_name = os.path.join(base_dir, "TikTokLiveReaderThai.exe")
    if os.path.exists(exe_name):
        print("กำลังบูตเปิดโปรแกรมหลักหลังอัปเดต...")
        subprocess.Popen([exe_name])
    else:
        print("บูตในโหมดนักพัฒนาซอร์สโค้ด...")
        subprocess.Popen([sys.executable, os.path.join(base_dir, "main.py")])
        
    print("อัปเดตเสร็จสิ้น!")

if __name__ == "__main__":
    run_update()
