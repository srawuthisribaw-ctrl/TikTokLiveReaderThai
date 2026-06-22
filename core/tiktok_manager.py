import asyncio
import sys
import threading
import time
import re
import os
import json
import importlib.util
from typing import List, Dict, Any, Optional
from TikTokLive import TikTokLiveClient
from TikTokLive.events import (
    ConnectEvent, CommentEvent, JoinEvent, GiftEvent, 
    DisconnectEvent, LikeEvent, ShareEvent, SubscribeEvent, FollowEvent
)
import urllib.parse as urllib
import requests

from database.db_helper import DatabaseHelper
from tts.audio_queue import AudioQueue
from services.point_service import PointService
from services.game_service import GameService
from services.music_service import MusicService
from services.radio_service import RadioService
from services.soundboard_service import SoundboardService
from services.ai_service import AIService
from core.command_handler import CommandHandler
from plugins.base_plugin import BasePlugin
from core.i18n import get_language, tr

GIFT_TRANSLATIONS = {
    'Rose': 'ดอกกุหลาบ',
    'Love Letter': 'จดหมายรัก',
    'GG': 'เก่งมาก',
    'Coffee': 'กาแฟ',
    'Ice Cream Cone': 'ไอศกรีมโคน',
    'Finger Heart': 'ชูนิ้วทำรูปหัวใจ',
    'Donut': 'โดนัท',
    'I Love You': 'ฉันรักคุณ',
    'Confetti': 'พลุกระดาษ',
    'Bear Love': 'หมีแห่งความรัก',
    'Butterfly': 'ผีเสื้อ',
    'Puppy Love': 'รักลูกหมา',
    'Hearts': 'หัวใจ',
    'Magic Potion': 'ยาวิเศษ',
    'Money Rain': 'ฝนเงิน',
    'Spaghetti Kiss': 'จูบเส้นสปาเก็ตตี้',
    'Fireworks': 'ดอกไม้ไฟ',
    'Red Sports Car': 'รถสปอร์ตสีแดง',
    'Yacht': 'เรือยอชต์',
    'Diamond Ring': 'แหวนเพชร',
    'Gold Necklace': 'สร้อยทอง',
    'Lipstick': 'ลิปสติก',
    'Sunglasses': 'แว่นกันแดด',
    'Paper Crane': 'นกกระเรียนกระดาษ',
    'Lollipop': 'อมยิ้ม',
    'Flowers': 'ดอกไม้',
    'Mic': 'ไมโครโฟน',
    'Football': 'ลูกฟุตบอล',
    'Capybara': 'คาปิบารา',
    'Panda': 'แพนด้า',
    'Tiny Dino': 'ไดโนเสาร์ตัวเล็ก',
    'Perfume': 'น้ำหอม',
    'Coral': 'ปะการัง',
    'Travel Trolley': 'กระเป๋าเดินทาง',
    'Witch’s Hat': 'หมวกแม่มด',
    "Witch's Hat": 'หมวกแม่มด',
    'Ski Goggles': 'แว่นสกี',
    'Lightning Bolt': 'สายฟ้า',
    'Mini Speaker': 'ลำโพงเล็ก',
    'Weights': 'ดัมเบล',
    'Origami': 'โอริกามิ',
    'Glow Stick': 'แท่งไฟ',
    'Chili': 'พริก',
    'Wishing Bottle': 'ขวดอธิษฐาน',
    'Hand Hearts': 'มินิฮาร์ท',
    'Money Gun': 'ปืนฉีดเงิน',
    'Leon': 'สิงโตลีออน',
    'Lion': 'สิงโต',
    'Crown': 'มงกุฎ',
    'Diamond': 'เพชร',
    'Castle': 'ปราสาท',
    'Universe': 'จักรวาล',
    'Rocket': 'จรวด',
    'Ferris Wheel': 'ชิงช้าสวรรค์',
    'Train': 'รถไฟ',
    'Dragon': 'มังกร',
    'Phoenix': 'นกฟีนิกซ์',
    'Swan': 'หงส์',
    'Whale': 'ปลาวาฬ',
    'Octopus': 'ปลาหมึก',
    'Submarine': 'เรือดำน้ำ',
    'TikTok': 'ติ๊กต็อก',
    'Motorcycle': 'มอเตอร์ไซค์',
    'Airplane': 'เครื่องบิน'
}
GIFT_TRANSLATIONS_LOWER = {k.lower(): v for k, v in GIFT_TRANSLATIONS.items()}

class TikTokManager:
    """
    คลาสควบคุมและจัดการการเชื่อมต่อห้อง TikTok Live
    พร้อมระบบคัดกรองเสียงมิกเซอร์ ซาวด์บอร์ด เอฟเฟกต์อัตโนมัติ และปลั๊กอินเสริม
    """
    def __init__(self, config_path: str, audio_queue: AudioQueue, ui_callback: Any):
        self.config_path = config_path
        self.audio = audio_queue
        self.ui_callback = ui_callback  # ใช้สะท้อนประวัติกลับสู่หน้าต่าง UI
        
        self.db = DatabaseHelper()
        self.points = PointService()
        self.games = GameService()
        self.music = MusicService(config_path, self.audio.add_to_queue)
        self.soundboard = SoundboardService(config_path, self.audio.add_to_queue)
        self.radio = RadioService(config_path)
        self.ai = AIService(config_path)
        self.commands = CommandHandler(config_path, self.points, self.games, self.music, self.ai)
        
        self.client: Optional[TikTokLiveClient] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self.is_connected = False
        self.room_id = ""
        # โหลดยอดไลก์สะสมจากฐานข้อมูลเพื่อป้องกันค่าเป็น 0 ทุกครั้งที่เปิดโปรแกรมใหม่
        try:
            total_likes_rows = self.db.execute_query("SELECT SUM(CAST(value AS INTEGER)) as total_l FROM statistics WHERE metric_name = 'likes'")
            self.total_likes = int(total_likes_rows[0]["total_l"]) if total_likes_rows and total_likes_rows[0]["total_l"] else 0
        except Exception:
            self.total_likes = 0
        
        # เก็บประวัติเพื่อเช็คสแปม
        self.last_comment_text = ""
        self.last_comment_time = 0
        self.last_join_user = ""
        self.last_join_time = 0
        self.connect_time = 0.0
        
        # ปลั๊กอินสะสม
        self.plugins: List[BasePlugin] = []
        self.load_plugins()

        # สร้างแฟร็กควบคุมงานเบื้องหลัง
        self.stop_bg_tasks = False
        self.bg_thread: Optional[threading.Thread] = None

    def load_plugins(self):
        """โหลดไฟล์ Python ปลั๊กอินเพิ่มเติมจากโฟลเดอร์ plugins/"""
        if getattr(sys, 'frozen', False):
            plugins_dir = os.path.join(os.path.dirname(sys.executable), "plugins")
        else:
            plugins_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugins")
        if not os.path.exists(plugins_dir):
            os.makedirs(plugins_dir)
            return

        for fname in os.listdir(plugins_dir):
            if fname.endswith(".py") and fname != "base_plugin.py" and not fname.startswith("__"):
                path = os.path.join(plugins_dir, fname)
                try:
                    spec = importlib.util.spec_from_file_location(fname[:-3], path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr != BasePlugin:
                                plugin_instance = attr()
                                plugin_instance.on_load(self)
                                self.plugins.append(plugin_instance)
                                print(f"Loaded Plugin: {plugin_instance.name}")
                except Exception as e:
                    print(f"Failed to load plugin {fname}: {e}")

    def connect_live(self, tiktok_id: str):
        """เริ่มเธรดเชื่อมต่อและรัน TikTokLiveClient"""
        if self.is_connected or (self.thread and self.thread.is_alive()):
            return
            
        self.room_id = tiktok_id
        self.stop_bg_tasks = False
        self.thread = threading.Thread(target=self._run_async_client, daemon=True)
        self.thread.start()
        
        self.bg_thread = threading.Thread(target=self._run_periodic_announcements, daemon=True)
        self.bg_thread.start()

    def disconnect_live(self):
        """หยุดการเชื่อมต่อ TikTok Live"""
        self.stop_bg_tasks = True
        if self.client and self.loop:
            try:
                asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)
            except Exception as e:
                print(f"Error stopping client: {e}")
        self.is_connected = False
        self.audio.add_to_queue(tr("MSG_DISCONNECTING"), 8, channel="tts")

    def _run_async_client(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        max_retries = 3
        retry_delay = 2.0
        
        try:
            for attempt in range(1, max_retries + 1):
                if self.stop_bg_tasks:
                    break
                    
                try:
                    print(f"Attempting to connect TikTok Live (Attempt {attempt}/{max_retries})...")
                    self.client = TikTokLiveClient(unique_id=self.room_id)
                    self._register_events()
                    
                    # Resolve room ID via API first (more reliable), then HTML
                    resolved_room_id = None
                    try:
                        resolved_room_id = int(self.loop.run_until_complete(self.client.web.fetch_room_id_from_api(self.client.unique_id)))
                        print(f"API resolved room ID: {resolved_room_id}")
                    except Exception as api_err:
                        print(f"API room ID resolution failed: {api_err}")
                        try:
                            resolved_room_id = int(self.loop.run_until_complete(self.client.web.fetch_room_id_from_html(self.client.unique_id)))
                            print(f"HTML resolved room ID: {resolved_room_id}")
                        except Exception as html_err:
                            print(f"HTML room ID resolution failed: {html_err}")
                    
                    # Set connect_time right before connecting
                    self.connect_time = time.time()
                    
                    # Connect using the resolved room ID to skip HTML scraping if successful
                    if resolved_room_id:
                        self.loop.run_until_complete(self.client.connect(room_id=resolved_room_id, process_connect_events=False))
                    else:
                        self.loop.run_until_complete(self.client.connect(process_connect_events=False))
                    
                    # If connected and exited normally, break retry loop
                    break
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    print(f"TikTok Live Connection Error (Attempt {attempt}/{max_retries}): {e}")
                    
                    if attempt == max_retries or self.stop_bg_tasks:
                        self.is_connected = False
                        self.ui_callback("connection_failed", str(e))
                    else:
                        time.sleep(retry_delay)
        finally:
            try:
                self.loop.close()
            except Exception:
                pass

    def _is_historical_event(self, event) -> bool:
        if not hasattr(event, 'base_message') or not event.base_message:
            return False
        ts = event.base_message.create_time
        if not ts:
            return False
        event_time = ts / 1000.0 if ts > 2000000000 else ts
        return event_time < self.connect_time - 2.0

    def _register_events(self):
        """ผูกความสัมพันธ์เข้ากับ Event Handlers ของ TikTok Live"""
        
        @self.client.on(ConnectEvent)
        async def on_connect(event: ConnectEvent):
            self.is_connected = True
            self.connect_time = time.time()
            self.audio.add_to_queue(tr("STATUS_CONNECTED_ROOM").format(room=self.room_id), 10, "sfx_join", channel="tts")
            self.ui_callback("connected", self.room_id)
            self.db.save_live_metric("live_start", time.strftime("%Y-%m-%d %H:%M:%S"))

        @self.client.on(CommentEvent)
        async def on_comment(event: CommentEvent):
            if self._is_historical_event(event):
                return
            user_id = event.user.unique_id
            nickname = event.user.nickname or "Guest"
            comment = event.comment
            
            # บันทึกลงฐานข้อมูลคอมเมนต์
            self.db.add_comment(user_id, nickname, comment)
            
            # รันปลั๊กอิน
            for plugin in self.plugins:
                if plugin.enabled:
                    try:
                        plugin.on_comment(user_id, nickname, comment)
                    except:
                        pass
            
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                read_comment = config.get("Settings", {}).get("read_comment", True)
                filter_badwords = config.get("Settings", {}).get("filter_badwords", True)
                filter_spam = config.get("Settings", {}).get("filter_spam", True)
                blacklist = config.get("Settings", {}).get("blacklist", [])
            except Exception:
                read_comment = True
                filter_badwords = True
                filter_spam = True
                blacklist = []

            # 1. กรองสแปม
            now = time.time()
            if filter_spam:
                if comment == self.last_comment_text and now - self.last_comment_time < 2.0:
                    return
            self.last_comment_text = comment
            self.last_comment_time = now

            # 2. กรองคำต้องห้าม
            if filter_badwords:
                badwords = ["ควย", "เย็ด", "มึง", "กู", "เหี้ย", "สัส"] + blacklist
                if any(w in comment for w in badwords):
                    return

            # 3. จัดการแต้มผู้ใช้ และเช็คเลเวลอัป/ทำภารกิจสำเร็จ
            ann_lvl, level_up, mission_completed = self.points.process_viewer_interaction(user_id, nickname, "comment")
            if ann_lvl:
                self.audio.add_to_queue(ann_lvl, 8, channel="comment")
                if level_up:
                    self.soundboard.trigger_event_effect("level_up", nickname)
                if mission_completed:
                    self.soundboard.trigger_event_effect("win_game", nickname)

            # 4. ประมวลผลคำสั่งแชทด่วน (!ช่วยเหลือ, !คะแนน ฯลฯ)
            cmd_res = self.commands.handle_chat_command(user_id, nickname, comment)
            if cmd_res:
                ans_text, sfx_k, prio = cmd_res
                # บันทึกเป็นช่อง AI หรือคอมเมนต์ตามเนื้อความ
                self.audio.add_to_queue(ans_text, prio, sfx_k, channel="ai" if ("AI ตอบ" in ans_text or "AI answered" in ans_text) else "comment")
                bot_prefix = "[Bot]" if get_language() == "en" else "[บอท]"
                self.ui_callback("history", f"{bot_prefix}: {ans_text}")
                return

            # 5. อ่านออกเสียงคอมเมนต์ปกติ
            if read_comment:
                processed_comment = comment
                fmt = config.get("Settings", {}).get("msg_comment", "{user} พิมพ์ว่า {comment}")
                
                # Dynamic override if default th template is found in en mode
                lang = get_language()
                if lang == "en" and fmt == "{user} พิมพ์ว่า {comment}":
                    fmt = "{user} says {comment}"
                elif lang == "th" and fmt == "{user} says {comment}":
                    fmt = "{user} พิมพ์ว่า {comment}"
                    
                speak_text = fmt.replace("{user}", nickname).replace("{comment}", processed_comment)
                
                self.audio.add_to_queue(speak_text, 5, "sfx_comment", channel="comment")
                self.ui_callback("history", f"{nickname}: {comment}")

        @self.client.on(JoinEvent)
        async def on_join(event: JoinEvent):
            if self._is_historical_event(event):
                return
            user_id = event.user.unique_id
            nickname = event.user.nickname or "Guest"
            
            self.db.add_viewer_log(user_id, nickname)
            
            for plugin in self.plugins:
                if plugin.enabled:
                    try:
                        plugin.on_join(user_id, nickname)
                    except:
                        pass
                        
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                read_join = config.get("Settings", {}).get("read_join", False)
                freq_limit = config.get("Settings", {}).get("viewer_frequency_limit", 1.5)
            except Exception:
                read_join = False
                freq_limit = 1.5

            now = time.time()
            if nickname == self.last_join_user and now - self.last_join_time < freq_limit:
                return
            self.last_join_user = nickname
            self.last_join_time = now

            self.points.process_viewer_interaction(user_id, nickname, "join")

            if read_join:
                fmt = config.get("Settings", {}).get("msg_join", "{user} เข้ามารับชมไลฟ์")
                
                lang = get_language()
                if lang == "en" and fmt == "{user} เข้ามารับชมไลฟ์":
                    fmt = "{user} joined the live"
                elif lang == "th" and fmt == "{user} joined the live":
                    fmt = "{user} เข้ามารับชมไลฟ์"
                    
                speak_text = fmt.replace("{user}", nickname)
                self.audio.add_to_queue(speak_text, 2, "sfx_join", channel="comment")
                
                history_msg = f"--- {nickname} joined ---" if lang == "en" else f"--- {nickname} เข้าร่วมไลฟ์ ---"
                self.ui_callback("history", history_msg)

        @self.client.on(GiftEvent)
        async def on_gift(event: GiftEvent):
            if self._is_historical_event(event):
                return
            # Skip intermediate streak events to avoid double counting
            if event.streaking:
                return
                
            user_id = event.user.unique_id
            nickname = event.user.nickname or "Guest"
            
            diamonds = event.gift.diamond_count if event.gift else 1
            count = event.repeat_count if event.repeat_count > 0 else 1
            gift_name = event.gift.name if event.gift and event.gift.name else "ของขวัญ"
            
            self.db.add_gift(user_id, nickname, gift_name, count, diamonds)
            
            for plugin in self.plugins:
                if plugin.enabled:
                    try:
                        plugin.on_gift(user_id, nickname, gift_name, count, diamonds)
                    except:
                        pass

            ann_msg, level_up, _ = self.points.process_viewer_interaction(user_id, nickname, "gift", diamonds)
            if ann_msg:
                self.audio.add_to_queue(ann_msg, 8, channel="gift")
                if level_up:
                    self.soundboard.trigger_event_effect("level_up", nickname)

            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                read_gift = config.get("Settings", {}).get("read_gift", True)
            except Exception:
                read_gift = True

            if read_gift:
                lang = get_language()
                if lang == "en":
                    final_gname = gift_name
                else:
                    gname_lower = gift_name.lower().strip()
                    final_gname = GIFT_TRANSLATIONS_LOWER.get(gname_lower, gift_name)
                
                fmt = config.get("Settings", {}).get("msg_gift", "{user} ส่ง {gift} จำนวน {count} ชิ้น")
                if lang == "en" and fmt == "{user} ส่ง {gift} จำนวน {count} ชิ้น":
                    fmt = "{user} sent {gift} x{count}"
                elif lang == "th" and fmt == "{user} sent {gift} x{count}":
                    fmt = "{user} ส่ง {gift} จำนวน {count} ชิ้น"
                    
                speak_text = fmt.replace("{user}", nickname).replace("{gift}", final_gname).replace("{count}", str(count))
                
                # หากได้รับของขวัญมูลค่าสูง
                if diamonds * count >= 100:
                    self.soundboard.trigger_event_effect("large_gift", nickname)
                else:
                    self.soundboard.trigger_event_effect("gift", nickname)
                    
                self.audio.add_to_queue(speak_text, 10, None, channel="gift")
                
                gift_prefix = "[Gift]" if lang == "en" else "[ของขวัญ]"
                gift_action = "sent" if lang == "en" else "ส่ง"
                self.ui_callback("history", f"{gift_prefix} {nickname}: {gift_action} {final_gname} x{count}")

        @self.client.on(LikeEvent)
        async def on_like(event: LikeEvent):
            if self._is_historical_event(event):
                return
            user_id = event.user.unique_id
            nickname = event.user.nickname or "Guest"
            
            like_count = getattr(event, 'likeCount', getattr(event, 'like_count', 1))
            self.total_likes += like_count
            self.db.save_live_metric("likes", str(like_count))
            
            for plugin in self.plugins:
                if plugin.enabled:
                    try:
                        plugin.on_like(user_id, nickname, like_count)
                    except:
                        pass

            self.points.process_viewer_interaction(user_id, nickname, "like")

            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                read_like = config.get("Settings", {}).get("read_like", False)
            except Exception:
                read_like = False

            if read_like:
                fmt = config.get("Settings", {}).get("msg_like", "{user} ส่งไลก์")
                
                lang = get_language()
                if lang == "en" and fmt == "{user} ส่งไลก์":
                    fmt = "{user} sent likes"
                elif lang == "th" and fmt == "{user} sent likes":
                    fmt = "{user} ส่งไลก์"
                    
                speak_text = fmt.replace("{user}", nickname)
                
                if self.total_likes % 500 == 0:
                    if lang == "en":
                        speak_text += f" Total likes: {self.total_likes}"
                    else:
                        speak_text += f" ยอดไลก์รวม {self.total_likes}"
                    
                self.audio.add_to_queue(speak_text, 2, "sfx_like", channel="comment")
                
                if lang == "en":
                    self.ui_callback("history", f"♥ {nickname} liked (Total {self.total_likes})")
                else:
                    self.ui_callback("history", f"♥ {nickname} กดถูกใจ (ยอดรวม {self.total_likes})")

        @self.client.on(ShareEvent)
        async def on_share(event: ShareEvent):
            if self._is_historical_event(event):
                return
            user_id = event.user.unique_id
            nickname = event.user.nickname or "Guest"
            
            self.db.add_follower(user_id, nickname)
            
            for plugin in self.plugins:
                if plugin.enabled:
                    try:
                        plugin.on_share(user_id, nickname)
                    except:
                        pass

            self.points.process_viewer_interaction(user_id, nickname, "share")

            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                read_share = config.get("Settings", {}).get("read_share", True)
            except Exception:
                read_share = True

            if read_share:
                fmt = config.get("Settings", {}).get("msg_share", "{user} แชร์ไลฟ์ของคุณ")
                
                lang = get_language()
                if lang == "en" and fmt == "{user} แชร์ไลฟ์ของคุณ":
                    fmt = "{user} shared your live"
                elif lang == "th" and fmt == "{user} shared your live":
                    fmt = "{user} แชร์ไลฟ์ของคุณ"
                    
                speak_text = fmt.replace("{user}", nickname)
                self.audio.add_to_queue(speak_text, 8, "sfx_share", channel="comment")
                
                if lang == "en":
                    self.ui_callback("history", f"↗ {nickname} shared live stream")
                else:
                    self.ui_callback("history", f"↗ {nickname} แชร์ไลฟ์สด")

        @self.client.on(SubscribeEvent)
        async def on_subscription(event: SubscribeEvent):
            if self._is_historical_event(event):
                return
            user_id = event.user.unique_id
            nickname = event.user.nickname or "Guest"
            
            self.points.db.update_activity_count(user_id, nickname, "shares_count")

            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                read_vip = config.get("Settings", {}).get("read_vip", True)
            except Exception:
                read_vip = True

            if read_vip:
                fmt = config.get("Settings", {}).get("msg_vip", "{user} สมัครสมาชิกช่อง")
                
                lang = get_language()
                if lang == "en" and fmt == "{user} สมัครสมาชิกช่อง":
                    fmt = "{user} subscribed to the channel"
                elif lang == "th" and fmt == "{user} subscribed to the channel":
                    fmt = "{user} สมัครสมาชิกช่อง"
                    
                speak_text = fmt.replace("{user}", nickname)
                self.audio.add_to_queue(speak_text, 8, "sfx_gift", channel="gift")
                
                if lang == "en":
                    self.ui_callback("history", f"★ VIP {nickname} subscribed")
                else:
                    self.ui_callback("history", f"★ VIP {nickname} สมัครสมาชิกช่อง")

        @self.client.on(FollowEvent)
        async def on_follow(event: FollowEvent):
            """ผู้ติดตามใหม่"""
            if self._is_historical_event(event):
                return
            user_id = event.user.unique_id
            nickname = event.user.nickname or "Guest"
            
            self.db.add_follower(user_id, nickname)
            self.points.process_viewer_interaction(user_id, nickname, "share") # บันทึกเทียบเท่าแชร์
            
            # เล่นเอฟเฟกต์เสียงและอ่านเสียงแจ้งเตือนผ่าน Soundboard
            self.soundboard.trigger_event_effect("new_follower", nickname)
            
            lang = get_language()
            if lang == "en":
                self.ui_callback("history", f"➕ {nickname} followed you")
            else:
                self.ui_callback("history", f"➕ {nickname} กดติดตามคุณแล้ว")

        @self.client.on(DisconnectEvent)
        async def on_disconnect(event: DisconnectEvent):
            self.is_connected = False
            self.ui_callback("disconnected", self.room_id)
            self.audio.add_to_queue(tr("MSG_DISCONNECTED"), 8, channel="tts")
            self.db.save_live_metric("live_end", time.strftime("%Y-%m-%d %H:%M:%S"))

    def _run_periodic_announcements(self):
        """ลูปเบื้องหลังเพื่อแจกแจงประกาศอัตโนมัติทุกๆ 10 นาที และแจ้งสถานะทุกๆ 5 นาที"""
        last_5min = time.time()
        last_10min = time.time()

        while not self.stop_bg_tasks:
            time.sleep(5)
            if not self.is_connected:
                continue

            now = time.time()

            # 1. รายงานสถานะผู้จัดไลฟ์ตาบอด ทุกๆ 5 นาที (Blind Streamer Helper)
            if now - last_5min >= 300:
                try:
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    announce_stats = config.get("AI", {}).get("announce_stats_enabled", True)
                except Exception:
                    announce_stats = True

                if announce_stats:
                    stats = self.db.get_summary_statistics()
                    
                    if get_language() == "en":
                        announcement = (
                            f"Streamer Report: Currently there are {stats['total_viewers']} total viewers, "
                            f"received {stats['total_followers']} new followers, "
                            f"total likes {self.total_likes}, "
                            f"and {stats['total_comments']} new comments in the system."
                        )
                    else:
                        announcement = (
                            f"รายงานผู้จัดไลฟ์: ขณะนี้มีผู้ชมสะสม {stats['total_viewers']} คน, "
                            f"ได้รับผู้ติดตามใหม่ {stats['total_followers']} คน, "
                            f"ยอดไลก์สะสม {self.total_likes} ครั้ง, "
                            f"มีข้อความคอมเมนต์ใหม่ในระบบ {stats['total_comments']} ข้อความค่ะ"
                        )
                    self.audio.add_to_queue(announcement, 8, channel="tts")
                last_5min = now

            # 2. กิจกรรมเอฟเฟกต์ข้อความเสียงตลกอัตโนมัติ (Custom Interval)
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                auto_cfg = config.get("AutoAnnouncements", {})
                interval = auto_cfg.get("interval_sec", 180)
                enabled = auto_cfg.get("enabled", True)
            except Exception:
                interval = 180
                enabled = True

            if enabled and now - last_10min >= interval:
                # สุ่มข้อความตลก
                text = self.soundboard.get_random_funny_announcement()
                self.audio.add_to_queue(text, 5, channel="tts")
                last_10min = now

            # 3. รันติ๊กเกอร์ของปลั๊กอินย่อย
            for plugin in self.plugins:
                if plugin.enabled:
                    try:
                        plugin.on_tick()
                    except:
                        pass
