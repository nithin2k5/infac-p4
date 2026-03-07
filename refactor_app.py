import re

with open(r"c:\Users\ntbm8\Desktop\developer\python\infac-p4\app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Imports
content = re.sub(
    r"import os\n\nfrom ultralytics import YOLO",
    "import os\n\nfrom core.camera import CameraManager\nfrom core.inference import InferenceEngine\nfrom core.inspection import InspectionManager",
    content
)

# 2. Init state
state_replace = """        self.camera = CameraManager()
        self.inference = InferenceEngine(MODEL_PATH)
        self.inspection = InspectionManager()
        
        self.inspection.on_log_result = self._add_log_entry
        self.inspection.on_stats_update = self._update_stats_ui

        self.is_detecting = False
        self.current_detections = []
        self.detection_log_items = []
        self.confidence_threshold = 0.65
        self._photo_ref = None

        threading.Thread(target=self.inference.load_model, daemon=True).start()"""

content = re.sub(
    r"        self.cap = None.*?self.model = None",
    state_replace,
    content,
    flags=re.DOTALL
)

# 3. Add Auto-Inspect UI and ROI UI
ui_replace = """        self.cam_combo.set("Camera 0")
        self.cam_combo.pack(fill="x", pady=(4, 0))

        # Auto-Inspect
        auto_frame = tk.Frame(parent, bg=Colors.BG_CARD)
        auto_frame.pack(fill="x", padx=16, pady=(4, 8))
        tk.Label(auto_frame, text="Auto-Inspect", font=Fonts.SMALL_BOLD, bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY).pack(side="left")
        self.auto_var = tk.BooleanVar(value=False)
        auto_cb = ttk.Checkbutton(auto_frame, variable=self.auto_var, command=self._on_auto_toggle)
        auto_cb.pack(side="right")
        
        # ROI Crop slider (Vertical height crop)
        roi_frame = tk.Frame(parent, bg=Colors.BG_CARD)
        roi_frame.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(roi_frame, text="ROI Zoom (Center)", font=Fonts.SMALL_BOLD, bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY).pack(anchor="w")
        self.roi_var = tk.DoubleVar(value=1.0)
        ttk.Scale(roi_frame, from_=0.3, to=1.0, variable=self.roi_var, orient="horizontal").pack(fill="x", pady=(4, 0))"""

content = re.sub(
    r"        self.cam_combo.set\(\"Camera 0\"\)\n        self.cam_combo.pack\(fill=\"x\", pady=\(4, 0\)\)",
    ui_replace,
    content
)

# 4. _toggle_camera
content = content.replace("self.is_running", "self.camera.is_running")
content = content.replace("getattr(self, \"is_paused\", False)", "self.camera.is_paused")
content = content.replace("self.camera_canvas.unbind(\"<Configure>\")", "self.camera_canvas.unbind(\"<Configure>\")\n            self.camera.is_paused = False\n            self.is_detecting = True")

# 5. _start_camera -> replace entirely
start_cam = """    def _start_camera(self):
        cam_idx = int(self.cam_combo.get().replace("Camera ", ""))
        self.cam_status_label.configure(text="● Connecting...", fg=Colors.WARNING)
        self.start_btn.itemconfig(self.start_btn._text_id, text="⏳  Connecting...")
        self.update_idletasks()
        
        self.camera.start_camera(cam_idx, self._on_camera_opened, self._on_camera_open_failed)

    def _on_camera_open_failed(self):
        self.after(0, lambda: self.cam_status_label.configure(text="● Camera Error", fg=Colors.DANGER))
        self.after(0, lambda: self.start_btn.itemconfig(self.start_btn._text_id, text="▶  Start Camera"))
        self.start_btn.bg_color = Colors.SUCCESS_DIM
        self.start_btn.hover_color = Colors.SUCCESS
        self.start_btn.itemconfig(self.start_btn._bg_id, fill=Colors.SUCCESS_DIM)

    def _on_camera_opened(self, w, h):
        self._static_frame = None
        self._static_predictions = []
        self.camera_canvas.unbind("<Configure>")
        
        self.is_detecting = True
        self.cam_status_label.configure(text="● Camera Connected", fg=Colors.SUCCESS)
        self.model_status_label.configure(text="● Detecting", fg=Colors.SUCCESS)
        
        self.start_btn.itemconfig(self.start_btn._text_id, text="⏹  Stop Camera")
        self.start_btn.bg_color = Colors.DANGER_DIM
        self.start_btn.hover_color = Colors.DANGER
        self.start_btn.itemconfig(self.start_btn._bg_id, fill=Colors.DANGER_DIM)
        
        self.res_label.configure(text=f"{w} × {h}")
        self._detect_interval = 0
        self._inference_busy = False
        
        self._update_frame()
"""
content = re.sub(r"    def _start_camera\(self\):.*?def _stop_camera\(self\):", start_cam + "\n    def _stop_camera(self):", content, flags=re.DOTALL)

# 6. _stop_camera
content = content.replace("self.is_detecting = False\n        self.is_video_file = False\n        self.is_paused = False\n        if self.cap:\n            self.cap.release()\n            self.cap = None", "self.is_detecting = False\n        self.camera.stop()")

# 7. _update_frame
update_frame = """    def _update_frame(self):
        frame, is_end = self.camera.read_frame()
        
        if is_end:
            self._stop_camera()
            self.cam_status_label.configure(text="● Video Ended", fg=Colors.TEXT_MUTED)
            return

        if frame is None:
            if self.camera.is_running:
                self.after(10, self._update_frame)
            return

        self.current_frame = frame.copy()
        
        self.fps_label.configure(text=f"FPS: {self.camera.fps:.1f}")
        self.stat_labels["fps_stat_val"].configure(text=f"{self.camera.fps:.0f}")
        self.frame_label.configure(text=f"Frame: {self.camera.frame_count:,}")

        # Provide ROI to inference based on slider
        roi_scale = self.roi_var.get()
        h_frame, w_frame = frame.shape[:2]
        new_w, new_h = int(w_frame * roi_scale), int(h_frame * roi_scale)
        rx, ry = (w_frame - new_w) // 2, (h_frame - new_h) // 2
        
        roi = None if roi_scale >= 0.99 else (rx, ry, new_w, new_h)

        if self.is_detecting:
            self._detect_interval += 1
            if self._detect_interval >= 2 and not getattr(self, '_inference_busy', False):
                self._detect_interval = 0
                self._inference_busy = True
                
                # Run inference in background
                def _bg_infer():
                    preds = self.inference.infer(frame.copy(), self.confidence_threshold, roi)
                    self.after(0, self._on_live_inference_result, preds)
                
                threading.Thread(target=_bg_infer, daemon=True).start()

        display_frame = frame.copy()

        # Draw ROI Box if scaled
        if roi:
            cv2.rectangle(display_frame, (rx, ry), (rx + new_w, ry + new_h), (255, 255, 255), 2, cv2.LINE_DASH)
            cv2.putText(display_frame, "ROI Mask", (rx + 5, ry + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        if self.is_detecting:
            dets = list(self.current_detections)
            for det in dets:
                x1 = int(det["x"] - det["width"] / 2)
                y1 = int(det["y"] - det["height"] / 2)
                x2 = int(det["x"] + det["width"] / 2)
                y2 = int(det["y"] + det["height"] / 2)
                conf = det["confidence"]
                cls_name = det["class"]
                color_bgr = (0, 255, 0) if conf >= 0.8 else (0, 255, 255) if conf >= 0.5 else (0, 0, 255)
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color_bgr, 3)
                
                # Bold corner accents
                corner_len = min(20, min(max(1, x2-x1), max(1, y2-y1)) // 3)
                for cx, cy, dx, dy in [(x1, y1, 1, 1), (x2, y1, -1, 1),
                                        (x1, y2, 1, -1), (x2, y2, -1, -1)]:
                    cv2.line(display_frame, (cx, cy), (cx + corner_len*dx, cy), color_bgr, 4)
                    cv2.line(display_frame, (cx, cy), (cx, cy + corner_len*dy), color_bgr, 4)

                label_text = f"{cls_name} {conf:.0%}"
                (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.rectangle(display_frame, (x1, y1 - th - 14), (x1 + tw + 14, y1), color_bgr, -1)
                cv2.putText(display_frame, label_text, (x1 + 7, y1 - 7),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2, cv2.LINE_AA)

            cx, cy = w_frame // 2, h_frame // 2
            cv2.line(display_frame, (cx-20, cy), (cx+20, cy), (88, 166, 255), 1)
            cv2.line(display_frame, (cx, cy-20), (cx, cy+20), (88, 166, 255), 1)

            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            cv2.putText(display_frame, ts, (10, h_frame - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (138, 148, 158), 1)

            cv2.circle(display_frame, (w_frame - 30, 25), 8, (0, 0, 255), -1)
            cv2.putText(display_frame, "DETECTING", (w_frame - 130, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        canvas_w = self.camera_canvas.winfo_width()
        canvas_h = self.camera_canvas.winfo_height()
        if canvas_w > 10 and canvas_h > 10:
            img_w, img_h = img.size
            scale = min(canvas_w / img_w, canvas_h / img_h)
            new_w, new_h = int(img_w * scale), int(img_h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)
        photo = ImageTk.PhotoImage(image=img)
        self._photo_ref = photo
        self.camera_canvas.delete("all")
        self.camera_canvas.create_image(canvas_w // 2, canvas_h // 2,
                                         image=photo, anchor="center")
        self.after(15, self._update_frame)

    def _on_live_inference_result(self, predictions):
        self._inference_busy = False
        if not self.is_detecting:
            return
            
        self.current_detections = predictions
        
        # Pass to inspection logic for glowing PASS/FAIL indicators and Auto-Inspect
        pcb_detected, solder_count = self.inspection.process_live_frame(predictions)
        
        if pcb_detected or solder_count > 0:
            if solder_count >= 2:
                self.pass_frame.configure(bg=Colors.SUCCESS)
                self.pass_label.configure(bg=Colors.SUCCESS, fg=Colors.BG_DARKEST)
                self.ng_frame.configure(bg=Colors.BG_MEDIUM)
                self.ng_label.configure(bg=Colors.BG_MEDIUM, fg=Colors.TEXT_MUTED)
                self.model_status_label.configure(text="● PASS - Detected", fg=Colors.SUCCESS)
            else:
                self.pass_frame.configure(bg=Colors.BG_MEDIUM)
                self.pass_label.configure(bg=Colors.BG_MEDIUM, fg=Colors.TEXT_MUTED)
                self.ng_frame.configure(bg=Colors.DANGER)
                self.ng_label.configure(bg=Colors.DANGER, fg=Colors.TEXT_PRIMARY)
                self.model_status_label.configure(text="● NG - Inspecting", fg=Colors.DANGER)
        else:
            self.pass_frame.configure(bg=Colors.BG_MEDIUM)
            self.pass_label.configure(bg=Colors.BG_MEDIUM, fg=Colors.TEXT_MUTED)
            self.ng_frame.configure(bg=Colors.BG_MEDIUM)
            self.ng_label.configure(bg=Colors.BG_MEDIUM, fg=Colors.TEXT_MUTED)
            self.model_status_label.configure(text="● Detecting", fg=Colors.SUCCESS)

    def _on_auto_toggle(self):
        self.inspection.auto_inspect_enabled = self.auto_var.get()
"""

# Completely override everything from _update_frame down to _upload_media
content = re.sub(r"    def _update_frame\(self\):.*?def _upload_media\(self\):", update_frame + "\n    def _upload_media(self):", content, flags=re.DOTALL)

# Refactor static video/media
start_video = """    def _start_video_file(self, filepath):
        w, h = self.camera.start_video(filepath)
        if w is None:
            self.model_status_label.configure(text="● Failed to load video", fg=Colors.DANGER)
            return

        self._static_frame = None
        self._static_predictions = []
        self.camera_canvas.unbind("<Configure>")

        self.is_detecting = True
        filename = filepath.replace("/", "\\").split("\\")[-1]
        self.cam_status_label.configure(text=f"● Video: {filename}", fg=Colors.PRIMARY)

        self.start_btn.itemconfig(self.start_btn._text_id, text="⏹  Stop Video")
        self.start_btn.bg_color = Colors.DANGER_DIM
        self.start_btn.hover_color = Colors.DANGER
        self.start_btn.itemconfig(self.start_btn._bg_id, fill=Colors.DANGER_DIM)

        self.res_label.configure(text=f"{w} × {h}")
        self._detect_interval = 0
        self._update_frame()"""
content = re.sub(r"    def _start_video_file\(self, filepath\):.*?def _load_static_image\(self, filepath\):", start_video + "\n    def _load_static_image(self, filepath):", content, flags=re.DOTALL)


# _load_static_image
load_img = """    def _load_static_image(self, filepath):
        frame = cv2.imread(filepath)
        if frame is None:
            self.model_status_label.configure(text="● Failed to load image", fg=Colors.DANGER)
            return

        self.current_frame = frame.copy()
        self._static_frame = frame.copy()
        self._static_predictions = []

        self.camera_canvas.unbind("<Configure>")
        self.camera_canvas.bind("<Configure>", self._redraw_static)

        h_img, w_img = frame.shape[:2]
        self.res_label.configure(text=f"{w_img} × {h_img}")
        self.cam_status_label.configure(text="● Image Loaded", fg=Colors.PRIMARY)
        self.model_status_label.configure(text="● Running inference...", fg=Colors.WARNING)
        self.update_idletasks()

        self._display_static_frame(frame.copy(), [])

        def _bg_static():
            if not self.inference.is_loaded():
                self.after(0, lambda: self.model_status_label.configure(text="● Model not loaded", fg=Colors.DANGER))
                return
            try:
                # Use current ROI slider value
                roi_scale = self.roi_var.get()
                roi = None if roi_scale >= 0.99 else ((w_img - int(w_img * roi_scale)) // 2, (h_img - int(h_img * roi_scale)) // 2, int(w_img * roi_scale), int(h_img * roi_scale))

                predictions = self.inference.infer(frame, self.confidence_threshold, roi)
                self.after(0, self._on_static_result, frame.copy(), filepath, predictions)
            except Exception as e:
                print(e)
                self.after(0, lambda: self.model_status_label.configure(text="● Inference Error", fg=Colors.DANGER))
                
        threading.Thread(target=_bg_static, daemon=True).start()
        
    def _on_static_result(self, frame, filepath, predictions):
        self._static_predictions = predictions
        self._display_static_frame(frame.copy(), predictions)
        
        filename = filepath.replace("/", "\\").split("\\")[-1]
        self.inspection.process_test_snapshot(predictions, filename)"""
content = re.sub(r"    def _load_static_image\(self, filepath\):.*?def _redraw_static\(self, event=None\):", load_img + "\n    def _redraw_static(self, event=None):", content, flags=re.DOTALL)

# Test detection
test_dec = """    def _test_detect(self):
        if self.current_frame is None:
            return

        frame = self.current_frame.copy()

        if self.camera.is_running:
            self.camera.is_paused = True
            if self.is_detecting:
                self.is_detecting = False
                self.model_status_label.configure(text="● Model Paused", fg=Colors.WARNING)
                self.current_detections = []

            self.start_btn.itemconfig(self.start_btn._text_id, text="▶  Resume Camera")
            self.start_btn.bg_color = Colors.SUCCESS_DIM
            self.start_btn.hover_color = Colors.SUCCESS
            self.start_btn.itemconfig(self.start_btn._bg_id, fill=Colors.SUCCESS_DIM)

        self._static_frame = frame.copy()
        self._static_predictions = []
        self.camera_canvas.unbind("<Configure>")
        self.camera_canvas.bind("<Configure>", self._redraw_static)

        h_img, w_img = frame.shape[:2]
        self.res_label.configure(text=f"{w_img} × {h_img}")
        self.cam_status_label.configure(text="● Test Snapshot", fg=Colors.INFO)
        self.model_status_label.configure(text="● Running inference...", fg=Colors.WARNING)
        self.update_idletasks()

        self._display_static_frame(frame.copy(), [])

        def _run():
            if not self.inference.is_loaded():
                self.after(0, lambda: self.model_status_label.configure(text="● Model not loaded", fg=Colors.DANGER))
                return
            try:
                roi_scale = self.roi_var.get()
                roi = None if roi_scale >= 0.99 else ((w_img - int(w_img * roi_scale)) // 2, (h_img - int(h_img * roi_scale)) // 2, int(w_img * roi_scale), int(h_img * roi_scale))

                predictions = self.inference.infer(frame, self.confidence_threshold, roi)
                self.after(0, self._on_test_result, frame, predictions)
            except Exception as e:
                print(f"Test inference error: {e}")
                self.after(0, lambda: self.model_status_label.configure(text="● Inference Error", fg=Colors.DANGER))

        threading.Thread(target=_run, daemon=True).start()

    def _on_test_result(self, frame, predictions):
        self._static_predictions = predictions
        self._display_static_frame(frame.copy(), predictions)
        self.inspection.process_test_snapshot(predictions, "Test snapshot")
"""
content = re.sub(r"    def _test_detect\(self\):.*?def _reset_stats\(self\):", test_dec + "\n    def _reset_stats(self):", content, flags=re.DOTALL)


content = content.replace("        self.total_inspected = 0\n        self.total_defects = 0\n        self.all_confidences.clear()\n", "        self.inspection.reset_stats()\n")

# Need _update_stats_ui
update_stats_ui = """    def _update_stats_ui(self):
        stats = self.inspection.get_stats()
        self.stat_labels["total_inspected_val"].configure(text=str(stats["inspected"]))
        self.stat_labels["defects_val"].configure(text=str(stats["defects"]))
        self.stat_labels["pass_rate_val"].configure(text=f"{stats['pass_rate']:.1f}%")
        self.stat_labels["avg_conf_val"].configure(text=f"{stats['avg_conf']:.1%}")
"""
content = re.sub(r"    def _add_log_entry\(self, label, detail, color, confidence\):", update_stats_ui + "\n    def _add_log_entry(self, label, detail, color, confidence):", content)

# Remove `_infer_with_roi` and `_apply_nms` and `_update_result_indicators`
content = re.sub(r"    # ═════════════════════════════════════════════════════\n    #  HELPERS\n    # ═════════════════════════════════════════════════════\n\n    def _infer_with_roi.*?(?=    def _on_threshold_change)", "    # ═════════════════════════════════════════════════════\n    #  HELPERS\n    # ═════════════════════════════════════════════════════\n\n", content, flags=re.DOTALL)

# Remove `is_running` directly checked
content = content.replace("self.is_running = False\n        if self.cap:\n            self.cap.release()", "self.camera.stop()")

with open(r"c:\Users\ntbm8\Desktop\developer\python\infac-p4\app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("done")
