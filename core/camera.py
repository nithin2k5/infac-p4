import cv2
import threading
import queue
import time
import platform


class CameraManager:
    def __init__(self):
        self.cap = None
        self.is_running = False
        self.is_video_file = False
        self.is_paused = False
        self.frame_queue = queue.Queue(maxsize=1)
        self.capture_thread = None

        self.fps = 0.0
        self.fps_frame_count = 0
        self.last_fps_time = time.time()
        self.frame_count = 0
        self.filename = ""

    # ─────────────────────────────────────────────────────
    #  Camera open helpers
    # ─────────────────────────────────────────────────────

    @staticmethod
    def _configure_capture(cap):
        """Apply resolution and image-quality settings to an open capture.

        For proper/high-quality cameras, we request the full 1920×1080 native
        resolution and let the camera's own ISP handle white-balance, focus,
        and exposure.  Only the buffer size and codec are forced so we always
        get the freshest frame without USB bandwidth issues.
        """
        # ── Resolution: request full HD — camera driver will use best match ──
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        cap.set(cv2.CAP_PROP_FPS, 30)

        # ── Buffer: keep only the freshest frame ─────────────────────────────
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # ── Focus: let the camera's autofocus work for sharpest results ──────
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)

        # ── Exposure / WB: leave on AUTO so the camera ISP manages them ──────
        # (Manual overrides hurt quality on cameras with good hardware ISPs)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)  # 0.75 = auto on V4L2

        # ── Codec: prefer MJPEG which avoids USB bandwidth issues ────────────
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

    # ─────────────────────────────────────────────────────
    #  Public API
    # ─────────────────────────────────────────────────────

    def start_camera(self, cam_idx, on_success, on_fail):
        """Open camera on the calling (main) thread, then spin capture loop.

        On macOS, cv2.VideoCapture uses AVFoundation which requires the main
        thread.  We therefore open the capture handle here synchronously and
        only move the *reading* loop to a daemon thread.
        """
        self.filename = f"Camera {cam_idx}"
        self.is_video_file = False

        if platform.system() == "Windows":
            cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(cam_idx)

        self._configure_capture(cap)

        if not cap.isOpened():
            cap.release()
            on_fail()
            return

        # Warm-up: discard the first several frames so the camera ISP can
        # settle its auto-exposure and auto-focus before we start using frames.
        for _ in range(10):
            cap.read()

        self.cap = cap
        self.is_running = True
        self.is_paused = False

        # Reset stats
        self.fps_frame_count = 0
        self.last_fps_time = time.time()
        self.frame_count = 0

        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()

        width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        on_success(width, height)

    def start_video(self, filepath):
        self.cap = cv2.VideoCapture(filepath)
        if not self.cap.isOpened():
            return None, None

        self.is_running = True
        self.is_video_file = True
        self.is_paused = False
        self.filename = filepath.replace("/", "\\").split("\\")[-1]

        self.fps_frame_count = 0
        self.last_fps_time = time.time()
        self.frame_count = 0
        width  = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return width, height

    def stop(self):
        self.is_running = False
        self.is_video_file = False
        self.is_paused = False
        if self.cap:
            self.cap.release()
            self.cap = None

    # ─────────────────────────────────────────────────────
    #  Internal
    # ─────────────────────────────────────────────────────

    def _capture_loop(self):
        while self.is_running and self.cap and self.cap.isOpened():
            if self.is_video_file:
                time.sleep(0.05)
                continue

            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            # Drop stale frames so consumers always get the latest
            if not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
            self.frame_queue.put(frame)

    def read_frame(self):
        """Returns (frame, is_video_end). frame is None if no frame available."""
        if not self.is_running or not self.cap or self.is_paused:
            return None, False

        if self.is_video_file:
            ret, frame = self.cap.read()
            if not ret:
                return None, True   # Video ended
            self._update_fps()
            return frame, False
        else:
            try:
                frame = self.frame_queue.get_nowait()
                self._update_fps()
                return frame, False
            except queue.Empty:
                return None, False

    def _update_fps(self):
        self.frame_count += 1
        self.fps_frame_count += 1
        now = time.time()
        elapsed = now - self.last_fps_time
        if elapsed >= 1.0:
            self.fps = self.fps_frame_count / elapsed
            self.fps_frame_count = 0
            self.last_fps_time = now
