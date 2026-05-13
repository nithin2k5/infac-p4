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

        12 MP USB cameras often produce blurry frames when forced to 1920×1080
        because the driver uses lossy digital downscaling.  Setting 1280×720
        matches a native sensor mode on most such cameras and gives sharp,
        artefact-free frames at >30 fps.

        Additional V4L2 / DirectShow properties reduce motion blur and improve
        sharpness for industrial close-up inspection.
        """
        # ── Resolution: use a clean native sensor mode ───────────────────────
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT,  720)
        cap.set(cv2.CAP_PROP_FPS, 30)

        # ── Buffer: keep only the freshest frame ─────────────────────────────
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # ── Sharpness / focus (supported on most UVC cameras) ────────────────
        # Disable auto-focus so the lens doesn't hunt and blur mid-inspection
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        # Request maximum sharpness (range 0–255 on most drivers)
        cap.set(cv2.CAP_PROP_SHARPNESS, 200)

        # ── Exposure: manual mode prevents auto-brightness flicker ───────────
        # 0.25 = manual exposure on V4L2 / DirectShow (driver-dependent)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        # A moderate exposure value; tweak if the scene is too dark/bright
        cap.set(cv2.CAP_PROP_EXPOSURE, -6)

        # ── Contrast / brightness ────────────────────────────────────────────
        cap.set(cv2.CAP_PROP_BRIGHTNESS, 128)
        cap.set(cv2.CAP_PROP_CONTRAST,   128)

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

        # Warm-up: discard the first few frames which can be dark/blurry
        for _ in range(3):
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
