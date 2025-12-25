from fastapi import FastAPI, WebSocket, HTTPException
from pydantic import BaseModel
import downloader

app = FastAPI()

class ExtractRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    url: str
    format_id: str
    folder: str = "downloads"

@app.post("/extract")
def extract(data: ExtractRequest):
    import yt_dlp
    try:
        with yt_dlp.YoutubeDL({"skip_download": True}) as ydl:
            info = ydl.extract_info(data.url, download=False)
    except Exception as e:
        # Retourne une erreur claire au client Flutter
        raise HTTPException(status_code=400, detail=f"yt-dlp error: {str(e)}")

    entries = info.get("entries", [info])
    result = []
    for e in entries:
        formats = [
            {"format_id": f["format_id"], "ext": f["ext"], "resolution": f.get("resolution")}
            for f in e["formats"] if f.get("vcodec") != "none"
        ]
        result.append({
            "title": e["title"],
            "thumbnail": e.get("thumbnail"),
            "formats": formats,
            "url": e.get("webpage_url")
        })
    return {"videos": result}

@app.post("/download")
def download(data: DownloadRequest):
    downloader.add_to_queue(data.url, data.format_id, data.folder)
    return {"status": "added to queue"}

@app.post("/stop")
def stop():
    downloader.stop_download()
    return {"status": "stopped"}

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    downloader.clients.add(ws)
    try:
        while True:
            await ws.receive_text()  # keep connection alive
    except:
        downloader.clients.remove(ws)
