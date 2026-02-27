"""
InFac P4 — Industrial Inspection System
Single-page live camera detection application using OpenCV + Tkinter.
"""

import tkinter as tk
from tkinter import ttk
import cv2
import numpy as np
import time
import threading
from PIL import Image, ImageTk
from datetime import datetime
from ui.theme import Colors, Fonts, Dimensions, configure_styles
from ui.components import StyledButton, ToggleSwitch


class InFacApp(tk.Tk):
    """Single-page industrial inspection application with live camera feed."""

    def __init__(self):
        super().__init__()

        # ── Window Setup ─────────────────────────────────
        self.title("InFac P4 — Industrial Inspection System")
        self.configure(bg=Colors.BG_DARKEST)
        self.minsize(1200, 750)

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = max(1280, int(screen_w * 0.85))
        win_h = max(800, int(screen_h * 0.85))
        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")

        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        configure_styles(self)

        # ── State ────────────────────────────────────────
        self.cap = None
        self.is_running = False
        self.is_detecting = False
        self.frame_count = 0
        self.fps = 0.0
        self.last_fps_time = time.time()
        self.fps_frame_count = 0
        self.detections = []
        self.detection_log = []
        self.total_inspected = 0
        self.total_defects = 0
        self.confidence_threshold = 0.65
        self.current_frame = None
        self._photo_ref = None  # prevent GC

        # ── Build UI ─────────────────────────────────────
        self._build_ui()

        # ── Protocol ─────────────────────────────────────
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ═════════════════════════════════════════════════════
    #  UI CONSTRUCTION
    # ═════════════════════════════════════════════════════

    def _build_ui(self):
        """Build the single-page layout."""

        # ── Top Bar ──────────────────────────────────────
        topbar = tk.Frame(self, bg=Colors.BG_DARKEST, height=50)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        # Brand
        brand = tk.Frame(topbar, bg=Colors.BG_DARKEST)
        brand.pack(side="left", padx=20)
        tk.Label(brand, text="🏭", font=("Segoe UI", 18),
                 bg=Colors.BG_DARKEST, fg=Colors.PRIMARY).pack(side="left", padx=(0, 10))
        tk.Label(brand, text="InFac P4", font=("Segoe UI", 14, "bold"),
                 bg=Colors.BG_DARKEST, fg=Colors.TEXT_PRIMARY).pack(side="left")
        tk.Label(brand, text="Industrial Inspection System", font=Fonts.SMALL,
                 bg=Colors.BG_DARKEST, fg=Colors.TEXT_MUTED).pack(side="left", padx=(12, 0))

        # Right side status
        right = tk.Frame(topbar, bg=Colors.BG_DARKEST)
        right.pack(side="right", padx=20)

        self.cam_status_label = tk.Label(right, text="● Camera Disconnected",
                                          font=Fonts.SMALL_BOLD,
                                          bg=Colors.BG_DARKEST, fg=Colors.DANGER)
        self.cam_status_label.pack(side="left", padx=(0, 20))

        self.model_status_label = tk.Label(right, text="● Model Idle",
                                            font=Fonts.SMALL_BOLD,
                                            bg=Colors.BG_DARKEST, fg=Colors.TEXT_MUTED)
        self.model_status_label.pack(side="left", padx=(0, 20))

        self.time_label = tk.Label(right, text="", font=Fonts.MONO_SMALL,
                                    bg=Colors.BG_DARKEST, fg=Colors.TEXT_SECONDARY)
        self.time_label.pack(side="left")
        self._update_clock()

        # Separator
        tk.Frame(self, bg=Colors.BORDER, height=1).pack(fill="x")

        # ── Main Body ────────────────────────────────────
        body = tk.Frame(self, bg=Colors.BG_DARK)
        body.pack(fill="both", expand=True)

        # Left: Camera + Controls
        left_panel = tk.Frame(body, bg=Colors.BG_DARK)
        left_panel.pack(side="left", fill="both", expand=True, padx=(16, 8), pady=16)

        self._build_camera_section(left_panel)
        self._build_controls_bar(left_panel)
        self._build_stats_row(left_panel)

        # Right: Settings + Detection Log
        right_panel = tk.Frame(body, bg=Colors.BG_CARD, width=340)
        right_panel.pack(side="right", fill="y", padx=(8, 16), pady=16)
        right_panel.pack_propagate(False)

        self._build_right_panel(right_panel)

    def _build_camera_section(self, parent):
        """Camera feed area with header."""
        # Header
        cam_header = tk.Frame(parent, bg=Colors.BG_DARK)
        cam_header.pack(fill="x", pady=(0, 8))

        tk.Label(cam_header, text="📷  Live Camera Feed", font=Fonts.SUBHEADING,
                 bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY).pack(side="left")

        info_frame = tk.Frame(cam_header, bg=Colors.BG_DARK)
        info_frame.pack(side="right")

        self.fps_label = tk.Label(info_frame, text="FPS: --", font=Fonts.MONO_SMALL,
                                   bg=Colors.BG_DARK, fg=Colors.SUCCESS)
        self.fps_label.pack(side="left", padx=(0, 16))

        self.res_label = tk.Label(info_frame, text="-- × --", font=Fonts.MONO_SMALL,
                                   bg=Colors.BG_DARK, fg=Colors.TEXT_MUTED)
        self.res_label.pack(side="left", padx=(0, 16))

        self.frame_label = tk.Label(info_frame, text="Frame: 0", font=Fonts.MONO_SMALL,
                                     bg=Colors.BG_DARK, fg=Colors.TEXT_MUTED)
        self.frame_label.pack(side="left")

        # Camera canvas
        cam_container = tk.Frame(parent, bg="#0a0a0a", highlightbackground=Colors.BORDER,
                                  highlightthickness=1)
        cam_container.pack(fill="both", expand=True)

        self.camera_canvas = tk.Canvas(cam_container, bg="#0a0a0a",
                                        highlightthickness=0, cursor="crosshair")
        self.camera_canvas.pack(fill="both", expand=True)

        # Draw initial placeholder
        self.camera_canvas.bind("<Configure>", self._draw_placeholder)

    def _build_controls_bar(self, parent):
        """Control buttons bar."""
        controls = tk.Frame(parent, bg=Colors.BG_MEDIUM)
        controls.pack(fill="x", pady=(8, 8))

        inner = tk.Frame(controls, bg=Colors.BG_MEDIUM)
        inner.pack(pady=10, padx=16)

        self.start_btn = StyledButton(
            inner, text="▶  Start Camera", bg_color=Colors.SUCCESS_DIM,
            hover_color=Colors.SUCCESS, width=150, height=40,
            command=self._toggle_camera, font=Fonts.BUTTON)
        self.start_btn.pack(side="left", padx=4)

        self.detect_btn = StyledButton(
            inner, text="🔍  Start Detection", bg_color=Colors.PRIMARY_DIM,
            hover_color=Colors.PRIMARY, width=160, height=40,
            command=self._toggle_detection, font=Fonts.BUTTON)
        self.detect_btn.pack(side="left", padx=4)

        StyledButton(
            inner, text="📸  Capture", bg_color=Colors.BG_CARD,
            hover_color=Colors.BG_CARD_HOVER, width=120, height=40,
            command=self._capture_frame, font=Fonts.BUTTON).pack(side="left", padx=4)

        StyledButton(
            inner, text="🔄  Reset Stats", bg_color=Colors.BG_CARD,
            hover_color=Colors.BG_CARD_HOVER, width=130, height=40,
            command=self._reset_stats, font=Fonts.BUTTON).pack(side="left", padx=4)

    def _build_stats_row(self, parent):
        """Stats cards row below controls."""
        stats = tk.Frame(parent, bg=Colors.BG_DARK)
        stats.pack(fill="x", pady=(0, 0))

        cards_data = [
            ("🔬", "Total Inspected", "total_inspected_val", "0", Colors.PRIMARY),
            ("⚠️", "Defects Found", "defects_val", "0", Colors.DANGER),
            ("✅", "Pass Rate", "pass_rate_val", "100.0%", Colors.SUCCESS),
            ("🎯", "Avg Confidence", "avg_conf_val", "-- %", Colors.WARNING),
            ("⚡", "FPS", "fps_stat_val", "--", Colors.INFO),
        ]

        self.stat_labels = {}
        for i, (icon, label, key, default, color) in enumerate(cards_data):
            card = tk.Frame(stats, bg=Colors.BG_CARD)
            card.pack(side="left", fill="x", expand=True,
                      padx=(0 if i == 0 else 4, 0 if i == len(cards_data)-1 else 4))

            inner = tk.Frame(card, bg=Colors.BG_CARD, padx=12, pady=10)
            inner.pack(fill="both", expand=True)

            top = tk.Frame(inner, bg=Colors.BG_CARD)
            top.pack(fill="x")
            tk.Label(top, text=icon, font=("Segoe UI", 12),
                     bg=Colors.BG_CARD, fg=color).pack(side="left")
            tk.Label(top, text=label, font=Fonts.TINY,
                     bg=Colors.BG_CARD, fg=Colors.TEXT_MUTED).pack(side="left", padx=(6, 0))

            accent = tk.Frame(inner, bg=color, height=2)
            accent.pack(fill="x", pady=(6, 4))

            val = tk.Label(inner, text=default, font=("Segoe UI", 18, "bold"),
                           bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY)
            val.pack(anchor="w")
            self.stat_labels[key] = val

    def _build_right_panel(self, parent):
        """Right sidebar with settings and detection log."""

        # ── Detection Settings ───────────────────────────
        tk.Label(parent, text="⚙️  Detection Settings", font=Fonts.SUBHEADING,
                 bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY).pack(
            anchor="w", padx=16, pady=(16, 12))

        # Confidence threshold
        thresh_frame = tk.Frame(parent, bg=Colors.BG_CARD)
        thresh_frame.pack(fill="x", padx=16, pady=(0, 8))

        top = tk.Frame(thresh_frame, bg=Colors.BG_CARD)
        top.pack(fill="x")
        tk.Label(top, text="Confidence Threshold", font=Fonts.SMALL_BOLD,
                 bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY).pack(side="left")
        self.conf_display = tk.Label(top, text="65%", font=Fonts.MONO_SMALL,
                                      bg=Colors.BG_CARD, fg=Colors.PRIMARY)
        self.conf_display.pack(side="right")

        self.conf_var = tk.DoubleVar(value=0.65)
        ttk.Scale(thresh_frame, from_=0.1, to=1.0, variable=self.conf_var,
                  orient="horizontal",
                  command=self._on_threshold_change).pack(fill="x", pady=(4, 0))

        # Camera source
        cam_frame = tk.Frame(parent, bg=Colors.BG_CARD)
        cam_frame.pack(fill="x", padx=16, pady=(4, 8))
        tk.Label(cam_frame, text="Camera Source", font=Fonts.SMALL_BOLD,
                 bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY).pack(anchor="w")
        self.cam_combo = ttk.Combobox(cam_frame, values=["Camera 0", "Camera 1", "Camera 2"],
                                       state="readonly", font=Fonts.SMALL)
        self.cam_combo.set("Camera 0")
        self.cam_combo.pack(fill="x", pady=(4, 0))

        # Toggles
        toggles = [("Show Bounding Boxes", True), ("Show Confidence", True),
                    ("Show Grid Overlay", False), ("Auto-capture Defects", False)]
        for label, initial in toggles:
            row = tk.Frame(parent, bg=Colors.BG_CARD)
            row.pack(fill="x", padx=16, pady=3)
            tk.Label(row, text=label, font=Fonts.SMALL,
                     bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY).pack(side="left")
            ToggleSwitch(row, initial=initial, bg=Colors.BG_CARD).pack(side="right")

        # Separator
        tk.Frame(parent, bg=Colors.BORDER, height=1).pack(fill="x", padx=16, pady=12)

        # ── Detection Log ────────────────────────────────
        log_header = tk.Frame(parent, bg=Colors.BG_CARD)
        log_header.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(log_header, text="📋  Detection Log", font=Fonts.SUBHEADING,
                 bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY).pack(side="left")
        self.log_count_label = tk.Label(log_header, text="0 items", font=Fonts.TINY,
                                         bg=Colors.BG_CARD, fg=Colors.TEXT_MUTED)
        self.log_count_label.pack(side="right")

        # Scrollable log
        log_container = tk.Frame(parent, bg=Colors.BG_CARD)
        log_container.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.log_canvas = tk.Canvas(log_container, bg=Colors.BG_CARD,
                                     highlightthickness=0)
        log_scrollbar = ttk.Scrollbar(log_container, orient="vertical",
                                       command=self.log_canvas.yview)
        self.log_frame = tk.Frame(self.log_canvas, bg=Colors.BG_CARD)

        self.log_frame.bind("<Configure>",
            lambda e: self.log_canvas.configure(scrollregion=self.log_canvas.bbox("all")))
        self.log_canvas.create_window((0, 0), window=self.log_frame, anchor="nw")
        self.log_canvas.configure(yscrollcommand=log_scrollbar.set)

        self.log_canvas.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")

        # Empty state
        self.empty_label = tk.Label(self.log_frame,
                                     text="No detections yet.\nStart the camera and detection\nto see results here.",
                                     font=Fonts.SMALL, bg=Colors.BG_CARD,
                                     fg=Colors.TEXT_MUTED, justify="center")
        self.empty_label.pack(pady=40)

    # ═════════════════════════════════════════════════════
    #  CAMERA OPERATIONS
    # ═════════════════════════════════════════════════════

    def _toggle_camera(self):
        if self.is_running:
            self._stop_camera()
        else:
            self._start_camera()

    def _start_camera(self):
        cam_idx = int(self.cam_combo.get().replace("Camera ", ""))
        self.cap = cv2.VideoCapture(cam_idx)

        if not self.cap.isOpened():
            self.cam_status_label.configure(text="● Camera Error", fg=Colors.DANGER)
            return

        self.is_running = True
        self.cam_status_label.configure(text="● Camera Connected", fg=Colors.SUCCESS)

        # Update button text
        self.start_btn.itemconfig(self.start_btn._text_id, text="⏹  Stop Camera")
        self.start_btn.bg_color = Colors.DANGER_DIM
        self.start_btn.hover_color = Colors.DANGER
        self.start_btn.itemconfig(self.start_btn._bg_id, fill=Colors.DANGER_DIM)

        # Get resolution
        w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.res_label.configure(text=f"{w} × {h}")

        self.last_fps_time = time.time()
        self.fps_frame_count = 0
        self._update_frame()

    def _stop_camera(self):
        self.is_running = False
        self.is_detecting = False
        if self.cap:
            self.cap.release()
            self.cap = None

        self.cam_status_label.configure(text="● Camera Disconnected", fg=Colors.DANGER)
        self.model_status_label.configure(text="● Model Idle", fg=Colors.TEXT_MUTED)

        self.start_btn.itemconfig(self.start_btn._text_id, text="▶  Start Camera")
        self.start_btn.bg_color = Colors.SUCCESS_DIM
        self.start_btn.hover_color = Colors.SUCCESS
        self.start_btn.itemconfig(self.start_btn._bg_id, fill=Colors.SUCCESS_DIM)

        self.detect_btn.itemconfig(self.detect_btn._text_id, text="🔍  Start Detection")
        self.detect_btn.bg_color = Colors.PRIMARY_DIM
        self.detect_btn.hover_color = Colors.PRIMARY
        self.detect_btn.itemconfig(self.detect_btn._bg_id, fill=Colors.PRIMARY_DIM)

        self.fps_label.configure(text="FPS: --")
        self.frame_label.configure(text="Frame: 0")
        self.frame_count = 0

        self.camera_canvas.delete("all")
        self.camera_canvas.bind("<Configure>", self._draw_placeholder)
        self._draw_placeholder()

    def _update_frame(self):
        if not self.is_running or not self.cap:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.after(30, self._update_frame)
            return

        self.frame_count += 1
        self.fps_frame_count += 1
        self.current_frame = frame.copy()

        # Calculate FPS
        now = time.time()
        elapsed = now - self.last_fps_time
        if elapsed >= 1.0:
            self.fps = self.fps_frame_count / elapsed
            self.fps_frame_count = 0
            self.last_fps_time = now
            self.fps_label.configure(text=f"FPS: {self.fps:.1f}")
            self.stat_labels["fps_stat_val"].configure(text=f"{self.fps:.0f}")

        self.frame_label.configure(text=f"Frame: {self.frame_count:,}")

        # TODO: Run detection through Roboflow here when integrated
        # For now, just display the frame
        display_frame = frame.copy()

        # Add overlay info
        if self.is_detecting:
            # Draw crosshair at center
            h, w = display_frame.shape[:2]
            cx, cy = w // 2, h // 2
            cv2.line(display_frame, (cx - 20, cy), (cx + 20, cy), (88, 166, 255), 1)
            cv2.line(display_frame, (cx, cy - 20), (cx, cy + 20), (88, 166, 255), 1)

            # Timestamp overlay
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            cv2.putText(display_frame, ts, (10, h - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (138, 148, 158), 1)

            # Detection mode indicator
            cv2.circle(display_frame, (w - 30, 25), 8, (0, 0, 255), -1)
            cv2.putText(display_frame, "DETECTING", (w - 130, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # Convert BGR → RGB → Tkinter PhotoImage
        rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)

        # Resize to fit canvas
        canvas_w = self.camera_canvas.winfo_width()
        canvas_h = self.camera_canvas.winfo_height()
        if canvas_w > 10 and canvas_h > 10:
            img_w, img_h = img.size
            scale = min(canvas_w / img_w, canvas_h / img_h)
            new_w, new_h = int(img_w * scale), int(img_h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)

        photo = ImageTk.PhotoImage(image=img)
        self._photo_ref = photo  # prevent GC
        self.camera_canvas.delete("all")
        self.camera_canvas.create_image(canvas_w // 2, canvas_h // 2,
                                         image=photo, anchor="center")

        self.after(15, self._update_frame)

    def _toggle_detection(self):
        if not self.is_running:
            return

        self.is_detecting = not self.is_detecting

        if self.is_detecting:
            self.model_status_label.configure(text="● Detecting", fg=Colors.SUCCESS)
            self.detect_btn.itemconfig(self.detect_btn._text_id, text="⏸  Pause Detection")
            self.detect_btn.bg_color = Colors.WARNING_DIM
            self.detect_btn.hover_color = Colors.WARNING
            self.detect_btn.itemconfig(self.detect_btn._bg_id, fill=Colors.WARNING_DIM)
        else:
            self.model_status_label.configure(text="● Model Paused", fg=Colors.WARNING)
            self.detect_btn.itemconfig(self.detect_btn._text_id, text="🔍  Start Detection")
            self.detect_btn.bg_color = Colors.PRIMARY_DIM
            self.detect_btn.hover_color = Colors.PRIMARY
            self.detect_btn.itemconfig(self.detect_btn._bg_id, fill=Colors.PRIMARY_DIM)

    def _capture_frame(self):
        if self.current_frame is not None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.jpg"
            cv2.imwrite(filename, self.current_frame)
            self._add_log_entry("📸 Capture", f"Saved: {filename}",
                                Colors.PRIMARY, "--")

    def _reset_stats(self):
        self.total_inspected = 0
        self.total_defects = 0
        self.detection_log.clear()
        self.stat_labels["total_inspected_val"].configure(text="0")
        self.stat_labels["defects_val"].configure(text="0")
        self.stat_labels["pass_rate_val"].configure(text="100.0%")
        self.stat_labels["avg_conf_val"].configure(text="-- %")

        for widget in self.log_frame.winfo_children():
            widget.destroy()
        self.empty_label = tk.Label(self.log_frame,
                                     text="No detections yet.\nStart the camera and detection\nto see results here.",
                                     font=Fonts.SMALL, bg=Colors.BG_CARD,
                                     fg=Colors.TEXT_MUTED, justify="center")
        self.empty_label.pack(pady=40)
        self.log_count_label.configure(text="0 items")

    # ═════════════════════════════════════════════════════
    #  DETECTION LOG
    # ═════════════════════════════════════════════════════

    def _add_log_entry(self, label, detail, color, confidence):
        """Add an entry to the detection log panel."""
        # Remove empty state
        if hasattr(self, 'empty_label') and self.empty_label.winfo_exists():
            self.empty_label.destroy()

        item = tk.Frame(self.log_frame, bg=Colors.BG_MEDIUM)
        item.pack(fill="x", pady=2, padx=2)

        indicator = tk.Frame(item, width=3, bg=color)
        indicator.pack(side="left", fill="y")

        info = tk.Frame(item, bg=Colors.BG_MEDIUM)
        info.pack(side="left", fill="x", expand=True, padx=10, pady=6)

        top_row = tk.Frame(info, bg=Colors.BG_MEDIUM)
        top_row.pack(fill="x")
        tk.Label(top_row, text=label, font=Fonts.SMALL_BOLD,
                 bg=Colors.BG_MEDIUM, fg=color).pack(side="left")
        tk.Label(top_row, text=confidence, font=Fonts.MONO_SMALL,
                 bg=Colors.BG_MEDIUM, fg=Colors.TEXT_SECONDARY).pack(side="right")

        tk.Label(info, text=detail, font=Fonts.TINY,
                 bg=Colors.BG_MEDIUM, fg=Colors.TEXT_MUTED).pack(anchor="w")

        self.detection_log.append(item)
        self.log_count_label.configure(text=f"{len(self.detection_log)} items")

        # Auto-scroll to bottom
        self.log_canvas.update_idletasks()
        self.log_canvas.yview_moveto(1.0)

    # ═════════════════════════════════════════════════════
    #  HELPERS
    # ═════════════════════════════════════════════════════

    def _on_threshold_change(self, value):
        pct = int(float(value) * 100)
        self.confidence_threshold = float(value)
        self.conf_display.configure(text=f"{pct}%")

    def _update_clock(self):
        now = datetime.now().strftime("%H:%M:%S")
        self.time_label.configure(text=now)
        self.after(1000, self._update_clock)

    def _draw_placeholder(self, event=None):
        c = self.camera_canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 50 or h < 50:
            return

        # Grid
        for x in range(0, w, 40):
            c.create_line(x, 0, x, h, fill="#1a1a2e", width=1)
        for y in range(0, h, 40):
            c.create_line(0, y, w, y, fill="#1a1a2e", width=1)

        # Center icon and text
        c.create_text(w // 2, h // 2 - 30, text="📷", font=("Segoe UI", 36),
                      fill=Colors.TEXT_MUTED)
        c.create_text(w // 2, h // 2 + 20, text="Camera feed will appear here",
                      font=Fonts.BODY, fill=Colors.TEXT_MUTED)
        c.create_text(w // 2, h // 2 + 45,
                      text="Click \"Start Camera\" to begin",
                      font=Fonts.SMALL, fill=Colors.TEXT_MUTED)

    def _on_close(self):
        self.is_running = False
        if self.cap:
            self.cap.release()
        self.destroy()
