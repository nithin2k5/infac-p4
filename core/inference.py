import cv2
import numpy as np
import os
import sys


# ═════════════════════════════════════════════════════════
#  LOCAL YOLO INFERENCE  (weights-6.pt)
# ═════════════════════════════════════════════════════════

def _resolve_weights_path(filename="weights-6.pt"):
    """Locate weights file relative to the app bundle or source root."""
    # PyInstaller bundle: files are next to the executable
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        # Source: two levels up from core/inference.py → project root
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, filename)


WEIGHTS_PATH = _resolve_weights_path("weights-6.pt")


class InferenceEngine:
    """Inference engine using local YOLOv8 weights (weights-6.pt)."""

    def __init__(self, model_path=None):
        self._model = None
        self._loaded = False
        self._weights = model_path or WEIGHTS_PATH

    # ─────────────────────────────────────────────────────
    #  Model loading
    # ─────────────────────────────────────────────────────

    def load_model(self):
        """Load YOLO model from weights-6.pt.  Safe to call from any thread."""
        try:
            from ultralytics import YOLO
            if not os.path.exists(self._weights):
                print(f"[InferenceEngine] Weights not found: {self._weights}")
                self._loaded = False
                return False

            print(f"[InferenceEngine] Loading model: {self._weights}")
            self._model = YOLO(self._weights)
            # Warm-up pass so the first real inference is fast
            dummy = np.zeros((64, 64, 3), dtype=np.uint8)
            self._model.predict(dummy, verbose=False, conf=0.5)
            self._loaded = True
            print("[InferenceEngine] Model loaded and warmed up ✓")
            return True
        except Exception as e:
            print(f"[InferenceEngine] Failed to load model: {e}")
            self._loaded = False
            return False

    def is_loaded(self):
        return self._loaded

    # ─────────────────────────────────────────────────────
    #  Inference
    # ─────────────────────────────────────────────────────

    def infer(self, frame, confidence_threshold=0.40, roi=None):
        """Run local YOLO inference and return predictions in unified format."""
        if not self._loaded or self._model is None:
            return []

        # ROI cropping
        if roi is not None:
            rx, ry, rw, rh = roi
            img_h, img_w = frame.shape[:2]
            y1 = max(0, int(ry))
            y2 = min(img_h, int(ry + rh))
            x1 = max(0, int(rx))
            x2 = min(img_w, int(rx + rw))
            inference_frame = frame[y1:y2, x1:x2]
            offset_x, offset_y = x1, y1
        else:
            inference_frame = frame
            offset_x, offset_y = 0, 0

        try:
            results = self._model.predict(
                inference_frame,
                conf=confidence_threshold,
                verbose=False,
                imgsz=640,
            )
        except Exception as e:
            print(f"[InferenceEngine] Inference error: {e}")
            return []

        raw_predictions = []
        if results and len(results) > 0:
            result = results[0]
            names = result.names  # {int: class_name}
            boxes = result.boxes

            if boxes is not None:
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    conf   = float(box.conf[0].item())
                    # box.xywh: center-x, center-y, width, height (in pixels)
                    xywh = box.xywh[0].tolist()
                    cx, cy, bw, bh = xywh

                    raw_predictions.append({
                        "x": cx + offset_x,
                        "y": cy + offset_y,
                        "width": bw,
                        "height": bh,
                        "class": names[cls_id].lower(),
                        "confidence": conf,
                    })

        return self.apply_nms(raw_predictions, iou_threshold=0.45)

    # ─────────────────────────────────────────────────────
    #  NMS (unchanged)
    # ─────────────────────────────────────────────────────

    def apply_nms(self, predictions, iou_threshold=0.45):
        """Apply Non-Maximum Suppression to filter overlapping boxes."""
        if not predictions:
            return []

        by_class = {}
        for p in predictions:
            by_class.setdefault(p["class"], []).append(p)

        final_preds = []

        for cls_name, preds in by_class.items():
            preds.sort(key=lambda x: x["confidence"], reverse=True)
            keep = []
            for p in preds:
                x1_a = p["x"] - p["width"] / 2
                y1_a = p["y"] - p["height"] / 2
                x2_a = p["x"] + p["width"] / 2
                y2_a = p["y"] + p["height"] / 2
                area_a = p["width"] * p["height"]

                overlap = False
                for k in keep:
                    x1_b = k["x"] - k["width"] / 2
                    y1_b = k["y"] - k["height"] / 2
                    x2_b = k["x"] + k["width"] / 2
                    y2_b = k["y"] + k["height"] / 2
                    area_b = k["width"] * k["height"]

                    inter_x1 = max(x1_a, x1_b)
                    inter_y1 = max(y1_a, y1_b)
                    inter_x2 = min(x2_a, x2_b)
                    inter_y2 = min(y2_a, y2_b)

                    if inter_x2 > inter_x1 and inter_y2 > inter_y1:
                        inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
                        union_area = area_a + area_b - inter_area
                        iou = inter_area / union_area
                        if iou > iou_threshold:
                            overlap = True
                            break

                if not overlap:
                    keep.append(p)

            final_preds.extend(keep)

        return final_preds
