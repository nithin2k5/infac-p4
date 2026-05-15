import cv2
import base64
import requests
import numpy as np


# ═════════════════════════════════════════════════════════
#  LIGHTING-INVARIANT PREPROCESSING
# ═════════════════════════════════════════════════════════

# CLAHE instance — reused across frames (thread-safe for reads)
_CLAHE = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
_SHARPEN_KERNEL = np.array([[0, -1,  0],
                             [-1,  5, -1],
                             [0, -1,  0]], dtype=np.float32)


def preprocess_frame(frame: np.ndarray) -> np.ndarray:
    """Normalise a BGR frame so inference is robust to lighting variation.

    NOTE: This function is kept for diagnostic / legacy use but is NOT called
    during normal inference.  Proper cameras already produce well-balanced
    frames and applying grey-world WB + CLAHE before sending to Roboflow
    distorts the colour information the model was trained on, reducing accuracy.

    Pipeline (if used manually):
      1. Auto white-balance  — equalise per-channel means.
      2. CLAHE on L channel  — boosts local contrast.
      3. Unsharp mask        — sharpens edges.
    """
    # ── 1. Simple auto white-balance (grey-world assumption) ─────────────
    result = frame.astype(np.float32)
    b_mean, g_mean, r_mean = (
        result[:, :, 0].mean(),
        result[:, :, 1].mean(),
        result[:, :, 2].mean(),
    )
    global_mean = (b_mean + g_mean + r_mean) / 3.0
    if b_mean > 0:
        result[:, :, 0] *= global_mean / b_mean
    if g_mean > 0:
        result[:, :, 1] *= global_mean / g_mean
    if r_mean > 0:
        result[:, :, 2] *= global_mean / r_mean
    result = np.clip(result, 0, 255).astype(np.uint8)

    # ── 2. CLAHE on the L (luminance) channel of LAB ─────────────────────
    lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l_eq = _CLAHE.apply(l)
    lab_eq = cv2.merge([l_eq, a, b])
    result = cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)

    # ── 3. Unsharp mask (sharpen edges) ──────────────────────────────────
    blurred = cv2.GaussianBlur(result, (0, 0), sigmaX=1.5)
    result = cv2.addWeighted(result, 1.5, blurred, -0.5, 0)

    return result


# ═════════════════════════════════════════════════════════
#  ROBOFLOW HOSTED INFERENCE
# ═════════════════════════════════════════════════════════

ROBOFLOW_API_KEY = "cf7X6JDorlmwhw6aqKUK"
ROBOFLOW_MODEL = "p4-kbph4"
ROBOFLOW_VERSION = "13"
ROBOFLOW_URL = (
    f"https://detect.roboflow.com/{ROBOFLOW_MODEL}/{ROBOFLOW_VERSION}"
)


class InferenceEngine:
    """Inference engine using Roboflow hosted API."""

    def __init__(self, model_path=None):
        # model_path kept for API compatibility but unused with hosted inference
        self.api_key = ROBOFLOW_API_KEY
        self.api_url = ROBOFLOW_URL
        self._loaded = False

    def load_model(self):
        """Verify API connectivity by sending a small test request."""
        try:
            # Create a tiny test image to verify the API key works
            test_img = np.zeros((64, 64, 3), dtype=np.uint8)
            _, buf = cv2.imencode(".jpg", test_img)
            img_b64 = base64.b64encode(buf).decode("utf-8")

            resp = requests.post(
                self.api_url,
                params={
                    "api_key": self.api_key,
                    "confidence": 50,
                },
                data=img_b64,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15,
            )
            if resp.status_code == 200:
                self._loaded = True
                print("Roboflow API connected successfully.")
                return True
            else:
                print(f"Roboflow API error: {resp.status_code} — {resp.text}")
                self._loaded = False
                return False
        except Exception as e:
            print(f"Roboflow API connection error: {e}")
            self._loaded = False
            return False

    def is_loaded(self):
        return self._loaded

    def infer(self, frame, confidence_threshold=0.40, roi=None):
        """Run inference via Roboflow hosted API."""
        if not self._loaded:
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

        # Encode frame as JPEG → base64
        # Send the raw frame — the camera's own ISP already handles WB,
        # sharpness, and exposure.  Avoid re-processing which distorts colour.
        _, buf = cv2.imencode(".jpg", inference_frame, [cv2.IMWRITE_JPEG_QUALITY, 97])
        img_b64 = base64.b64encode(buf).decode("utf-8")

        try:
            resp = requests.post(
                self.api_url,
                params={
                    "api_key": self.api_key,
                    "confidence": int(confidence_threshold * 100),
                },
                data=img_b64,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            if resp.status_code != 200:
                print(f"Roboflow inference error: {resp.status_code}")
                return []

            data = resp.json()
        except Exception as e:
            print(f"Roboflow inference request failed: {e}")
            return []

        # Parse Roboflow response → unified prediction format
        raw_predictions = []
        for pred in data.get("predictions", []):
            raw_predictions.append({
                "x": float(pred["x"]) + offset_x,
                "y": float(pred["y"]) + offset_y,
                "width": float(pred["width"]),
                "height": float(pred["height"]),
                "class": pred["class"].lower(),
                "confidence": float(pred["confidence"]),
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
