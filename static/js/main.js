// Global State Tracking
let flvPlayer = null;
let isOnline = false;

function startVideoPlayer(streamName) {
  if (mpegts.isSupported()) {
    const videoElement = document.getElementById("videoElement");
    const streamUrl = `http://${window.location.hostname}:8081/live/${streamName}.flv`;

    stopVideoPlayer();

    flvPlayer = mpegts.createPlayer({
      type: "flv",
      isLive: true,
      url: streamUrl,
      enableStashBuffer: false,
      liveBufferLatencyChasing: true,
    });

    flvPlayer.attachMediaElement(videoElement);
    flvPlayer.load();
    flvPlayer.play().catch((e) => console.log("Autoplay blocked:", e));

    // Handle network error pada FLV stream
    flvPlayer.on(mpegts.Events.ERROR, (errorType, errorDetail, errorInfo) => {
      console.warn("mpegts error encountered:", errorType, errorDetail, errorInfo);
      if (errorType === mpegts.ErrorTypes.NETWORK_ERROR) {
        stopVideoPlayer();
        isOnline = false;
      }
    });

    document.getElementById("no-signal-text").style.display = "none";
  }
}

function stopVideoPlayer() {
  const videoElement = document.getElementById("videoElement");

  if (flvPlayer) {
    try {
      flvPlayer.pause();
      flvPlayer.unload();
      flvPlayer.detachMediaElement();
      flvPlayer.destroy();
    } catch (e) {
      console.warn("Error stopping flvPlayer:", e);
    }
    flvPlayer = null;
  }

  if (videoElement) {
    videoElement.pause();
    videoElement.removeAttribute("src");
    videoElement.load();
  }

  document.getElementById("no-signal-text").style.display = "flex";
}

function formatUptime(seconds) {
  if (!seconds || seconds <= 0) return "-";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);

  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

async function updateStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();

    const badge = document.getElementById("status-badge");
    const baseBadgeClass = "w-full text-center py-2 px-4 rounded-xl text-xs font-bold transition-all border shadow-sm ";

    if (data.online) {
      // Update UI status online
      badge.className = baseBadgeClass + "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
      badge.innerText = "Online";

      document.getElementById("stream-name").innerText = data.stream_name || "-";
      document.getElementById("bitrate").innerText = (data.bitrate || 0) + " Kbps";
      document.getElementById("fps").innerText = data.fps || 0;
      document.getElementById("resolution").innerText = data.resolution || "-";
      document.getElementById("v-codec").innerText = data.v_codec || "-";
      document.getElementById("a-codec").innerText = data.a_codec || "-";
      document.getElementById("uptime").innerText = formatUptime(data.uptime);
      document.getElementById("client-ip").innerText = data.client_ip || "-";

      // Jalankan player jika status online dan belum berjalan
      if (!isOnline || !flvPlayer) {
        isOnline = true;
        startVideoPlayer(data.stream_name);
      }
    } else {
      // Update UI status offline
      badge.className = baseBadgeClass + "bg-rose-500/20 text-rose-300 border-rose-500/40";
      badge.innerText = "Offline";

      document.getElementById("stream-name").innerText = "-";
      document.getElementById("bitrate").innerText = "0 Kbps";
      document.getElementById("fps").innerText = "0";
      document.getElementById("resolution").innerText = "-";
      document.getElementById("v-codec").innerText = "-";
      document.getElementById("a-codec").innerText = "-";
      document.getElementById("uptime").innerText = "-";
      document.getElementById("client-ip").innerText = "-";

      // Hentikan player jika status offline dan sedang berjalan
      if (isOnline || flvPlayer) {
        isOnline = false;
        stopVideoPlayer();
      }
    }
  } catch (e) {
    console.error("Error fetching telemetry:", e);
  }
}

// Polling status setiap 1 detik
setInterval(updateStatus, 1000);
