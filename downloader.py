import yt_dlp
import threading
import asyncio
from queue import Queue

clients = set()  # WebSocket clients
download_queue = Queue()
current_thread = None
current_ydl = None

async def send_progress(data):
    for ws in clients.copy():
        try:
            await ws.send_json(data)
        except:
            clients.remove(ws)

def progress_hook(d):
    if d['status'] == 'downloading':
        data = {
            "status": "downloading",
            "title": d.get("filename"),
            "percent": d.get("_percent_str", "0%"),
            "speed": d.get("_speed_str", ""),
            "eta": d.get("_eta_str", "")
        }
        asyncio.run(send_progress(data))
    elif d['status'] == 'finished':
        asyncio.run(send_progress({"status":"finished","title":d.get("filename")}))
        start_next_download()
    elif d.get("status") == "error":
        asyncio.run(send_progress({"status":"error","message": d.get("filename","Error")}))

def download_video(url, format_id, folder="downloads"):
    global current_ydl
    ydl_opts = {
        "format": format_id,
        "outtmpl": f"{folder}/%(title)s.%(ext)s",
        "continuedl": True,
        "noplaylist": True,
        "progress_hooks": [progress_hook],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            current_ydl = ydl
            ydl.download([url])
    except Exception as e:
        asyncio.run(send_progress({"status":"error","message": str(e)}))
        start_next_download()

def start_next_download():
    if not download_queue.empty():
        url, format_id, folder = download_queue.get()
        start_download_thread(url, format_id, folder)

def start_download_thread(url, format_id, folder="downloads"):
    global current_thread
    current_thread = threading.Thread(target=download_video, args=(url, format_id, folder))
    current_thread.start()

def add_to_queue(url, format_id, folder="downloads"):
    download_queue.put((url, format_id, folder))
    if current_thread is None or not current_thread.is_alive():
        start_next_download()

def stop_download():
    global current_thread, current_ydl
    if current_thread and current_thread.is_alive():
        current_ydl._quit = True
        current_thread.join()

