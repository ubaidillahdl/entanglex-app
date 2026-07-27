import os
import time

import requests
from flask import Flask, jsonify, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

# State internal untuk fallback jika SRS API tidak bisa diakses
stream_state = {"is_online": False, "stream_name": "", "start_time": None}

SRS_API_URL = "http://127.0.0.1:1985/api/v1/streams/"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/srs/on_publish", methods=["POST"])
def on_publish():
    """Callback SRS ketika stream mulai - update state dan return '0'"""
    data = request.get_json(force=True) if request.is_json else request.form
    stream_state["is_online"] = True
    stream_state["stream_name"] = data.get("stream", "")
    stream_state["start_time"] = time.time()
    print(f"[SRS Callback] Stream started: {stream_state['stream_name']}")

    return "0", 200, {"Content-Type": "text/plain"}


@app.route("/api/srs/on_unpublish", methods=["POST"])
def on_unpublish():
    """Callback SRS ketika stream berhenti - reset state dan return '0'"""
    stream_state["is_online"] = False
    stream_state["stream_name"] = ""
    stream_state["start_time"] = None
    print("[SRS Callback] Stream stopped")

    return "0", 200, {"Content-Type": "text/plain"}


@app.route("/api/status")
def status():
    """Endpoint status streaming - ambil data dari SRS API atau fallback ke state internal"""
    try:
        r = requests.get(SRS_API_URL, timeout=1).json()
        streams = r.get("streams", [])

        if not streams:
            stream_state["is_online"] = False
            stream_state["stream_name"] = ""
            stream_state["start_time"] = None
            return jsonify({"online": False})

        s = streams[0]
        publish_data = s.get("publish") or {}
        is_publishing = publish_data.get("active", False)

        if not is_publishing:
            stream_state["is_online"] = False
            stream_state["stream_name"] = ""
            stream_state["start_time"] = None
            return jsonify({"online": False})

        # Ekstrak data stream dari response SRS
        kbps_data = s.get("kbps") or {}
        kbps = int(kbps_data.get("recv_30s", 0))

        video_data = s.get("video") or {}
        audio_data = s.get("audio") or {}

        fps = int(video_data.get("fps", 0)) if isinstance(video_data, dict) else 0
        if fps == 0 and kbps > 0:
            fps = 30

        width = video_data.get("width", 0) if isinstance(video_data, dict) else 0
        height = video_data.get("height", 0) if isinstance(video_data, dict) else 0
        resolution = f"{width}x{height}" if width and height else "Auto/1080p"

        v_codec = (
            video_data.get("codec", "H.264")
            if isinstance(video_data, dict)
            else "H.264"
        )
        a_codec = (
            audio_data.get("codec", "AAC")
            if isinstance(audio_data, dict) and audio_data.get("codec")
            else "AAC / None"
        )

        # Hitung uptime dari SRS atau fallback ke state internal
        live_ms = publish_data.get("live_ms", 0)
        if live_ms and live_ms > 0:
            uptime = int(live_ms / 1000)
        elif stream_state["start_time"]:
            uptime = int(time.time() - stream_state["start_time"])
        else:
            uptime = 0

        client_ip = str(publish_data.get("cid", "Connected"))
        stream_name = s.get("name") or stream_state.get("stream_name") or "drone"

        return jsonify(
            {
                "online": True,
                "stream_name": stream_name,
                "bitrate": kbps,
                "fps": fps,
                "resolution": resolution,
                "v_codec": v_codec,
                "a_codec": a_codec,
                "uptime": uptime,
                "client_ip": client_ip,
            }
        )
    except requests.RequestException:
        # Jika SRS API tidak bisa diakses, gunakan state internal
        pass

    # Fallback jika SRS API gagal dipanggil
    if stream_state["is_online"] and stream_state["start_time"]:
        return jsonify(
            {
                "online": True,
                "stream_name": stream_state["stream_name"] or "drone",
                "bitrate": 0,
                "fps": 0,
                "resolution": "Auto/1080p",
                "v_codec": "H.264",
                "a_codec": "AAC",
                "uptime": int(time.time() - stream_state["start_time"]),
                "client_ip": "Connected",
            }
        )

    return jsonify({"online": False})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
