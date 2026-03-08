import cv2
import timm
import torch
import numpy as np
from PIL import Image
from torchvision import transforms
import torch.nn.functional as F

# =====================================================
# DEVICE
# =====================================================
device = "cuda" if torch.cuda.is_available() else "cpu"

# =====================================================
# LOAD MODELS
# =====================================================
presence_model = timm.create_model(
    "swin_tiny_patch4_window7_224",
    pretrained=False,
    num_classes=2
)
presence_model.load_state_dict(
    torch.load("weights/swin_scalp_presence.pth", map_location=device)
)
presence_model.to(device).eval()

severity_model = timm.create_model(
    "swin_tiny_patch4_window7_224",
    pretrained=False,
    num_classes=3
)
severity_model.load_state_dict(
    torch.load("weights/swin_dandruff_severity.pth", map_location=device)
)
severity_model.to(device).eval()

# =====================================================
# TRANSFORM (MATCH TRAINING)
# =====================================================
transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
])

presence_labels = ["healthy", "dandruff"]
severity_labels = ["low", "moderate", "severe"]

# =====================================================
# PUBLIC API (MEMORY ONLY)
# =====================================================
def process_single_image(image):
    """
    image: PIL.Image or numpy.ndarray (RGB)
    """

    if isinstance(image, Image.Image):
        img = np.array(image)
    elif isinstance(image, np.ndarray):
        img = image
    else:
        raise TypeError("Expected PIL.Image or numpy.ndarray")

    tensor = transform(img).unsqueeze(0).to(device)

    # -----------------------------
    # 1️⃣ PRESENCE DETECTION
    # -----------------------------
    with torch.no_grad():
        p_logits = presence_model(tensor)
        p_probs = F.softmax(p_logits, dim=1)[0]

    p_idx = int(torch.argmax(p_probs))
    presence = presence_labels[p_idx]

    # -----------------------------
    # 2️⃣ HEALTHY SCALP → STOP
    # -----------------------------
    if presence == "healthy":
        return {
            "presence": "healthy",
            "severity": "none",
            "confidence": float(p_probs[p_idx]),  # optional, can be removed later
            "overlay_image": None,
            "message": "Your scalp has no dandruff",
        }

    # -----------------------------
    # 3️⃣ SEVERITY DETECTION
    # -----------------------------
    with torch.no_grad():
        s_logits = severity_model(tensor)
        s_probs = F.softmax(s_logits, dim=1)[0]

    s_idx = int(torch.argmax(s_probs))
    severity = severity_labels[s_idx]

    # -----------------------------
    # 4️⃣ OVERLAY (ONLY IF MASK EXISTS)
    # -----------------------------
    overlay = _make_dandruff_overlay(img, severity)

    return {
        "presence": "dandruff",
        "severity": severity,
        "overlay_image": overlay,  # may be None
    }

# =====================================================
# OVERLAY GENERATION (SAFE + ADAPTIVE)
# =====================================================
def _make_dandruff_overlay(orig, severity):
    gray = cv2.cvtColor(orig, cv2.COLOR_RGB2GRAY)

    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    lap = cv2.Laplacian(blur, cv2.CV_64F)
    lap = np.abs(lap)

    # Adaptive percentile threshold (robust)
    thresh = np.percentile(lap, 92)
    mask = lap > thresh

    # No meaningful dandruff texture → skip overlay
    if np.count_nonzero(mask) < 300:
        return None

    color_map = {
        "low": (0, 255, 255),
        "moderate": (0, 165, 255),
        "severe": (0, 0, 255),
    }

    overlay = orig.copy()
    overlay[mask] = color_map.get(severity, (180, 180, 180))

    return cv2.addWeighted(orig, 0.65, overlay, 0.35, 0)
