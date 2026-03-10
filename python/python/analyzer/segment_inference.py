import cv2
import torch
import joblib
import numpy as np
from PIL import Image
from torchvision import transforms

from segmentation.attention_unet import AttentionUNet

# =====================================================
# DEVICE
# =====================================================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# =====================================================
# LOAD MODELS
# =====================================================
seg_model = AttentionUNet().to(device)
seg_model.load_state_dict(
    torch.load("weights/attention_unet_hair.pth", map_location=device)
)
seg_model.eval()

severity_model = joblib.load("weights/severity_model.pkl")

# =====================================================
# TRANSFORM (MATCH TRAINING)
# =====================================================
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

# =====================================================
# PREPROCESS (EXACT COPY OF WORKING SCRIPT)
# =====================================================
def preprocess(img, zoom_factor=1.2):
    img = np.array(img)

    # --- CLAHE ---
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(2.0, (8, 8))
    l = clahe.apply(l)

    img = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2RGB)

    # --- CENTER ZOOM ---
    h, w = img.shape[:2]
    cx, cy = w // 2, h // 2
    nw, nh = int(w / zoom_factor), int(h / zoom_factor)

    x1, y1 = max(cx - nw // 2, 0), max(cy - nh // 2, 0)
    x2, y2 = min(x1 + nw, w), min(y1 + nh, h)

    img = cv2.resize(img[y1:y2, x1:x2], (w, h))

    # --- SMOOTH ---
    img = cv2.GaussianBlur(img, (3, 3), 0)

    return Image.fromarray(img)

# =====================================================
# FEATURE EXTRACTION (EXACT)
# =====================================================
def _extract_features(mask, orig):
    mask_bool = mask > 0
    if np.sum(mask_bool) == 0:
        return None

    hsv = cv2.cvtColor(orig, cv2.COLOR_RGB2HSV)
    _, s, v = cv2.split(hsv)

    scalp_pixels = (v > 160) & (s < 60) & mask_bool
    scalp_ratio = np.sum(scalp_pixels) / np.sum(mask_bool)

    contours, _ = cv2.findContours(
        mask.astype(np.uint8),
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    areas = [cv2.contourArea(c) for c in contours]

    return np.array([[
        scalp_ratio,
        len(contours),
        max(areas) if areas else 0,
        np.mean(v[mask_bool]),
        np.mean(s[mask_bool])
    ]])

# =====================================================
# OVERLAY CREATION (SAFE)
# =====================================================
def _make_overlay(orig, mask, severity_idx):
    color_map = {
        0: (0, 255, 255),   # mild
        1: (0, 165, 255),   # moderate
        2: (0, 0, 255),     # severe
        3: (0, 0, 139),     # very severe
    }

    temp = np.zeros_like(orig)
    temp[mask > 0] = color_map.get(severity_idx, (160, 160, 160))

    return cv2.addWeighted(orig, 0.6, temp, 0.4, 0)

# =====================================================
# PUBLIC API (MEMORY ONLY)
# =====================================================
def process_single_image(image):
    """
    image: PIL.Image or numpy RGB
    """

    if isinstance(image, Image.Image):
        orig = np.array(image)
    elif isinstance(image, np.ndarray):
        orig = image
    else:
        raise TypeError("Expected PIL.Image or numpy.ndarray")

    h, w = orig.shape[:2]

    # --- PREPROCESS ---
    img_p = preprocess(image)
    x = transform(img_p).unsqueeze(0).to(device)

    # --- SEGMENTATION ---
    with torch.no_grad():
        prob = torch.sigmoid(seg_model(x))[0, 0].cpu().numpy()

    prob = cv2.resize(prob, (w, h))
    mask = (prob > 0.35).astype(np.uint8) * 255

    # --- MORPHOLOGY ---
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    # --- SEVERITY ---
    feats = _extract_features(mask, orig)

    if feats is None:
        return {
            "severity": "unknown",
            "overlay_image": None,
        }

    pred = int(severity_model.predict(feats)[0])
    severity_labels = ["mild", "moderate", "severe", "very_severe"]

    overlay = _make_overlay(orig, mask, pred)

    return {
        "severity": severity_labels[pred],
        "overlay_image": overlay,
    }
