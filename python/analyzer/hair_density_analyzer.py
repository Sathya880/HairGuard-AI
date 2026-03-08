import numpy as np
import cv2
from PIL import Image, ImageOps


IMG_SIZE = 256
CLASSES = ["normal", "moderate", "severe"]


# ───────────────────────── FEATURE EXTRACTION ─────────────────────────

def extract_features(image):

    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    image = image.resize((IMG_SIZE, IMG_SIZE))

    img = np.array(image)

    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    H, W = gray.shape

    # Crown region
    r1, r2 = int(H * 0.15), int(H * 0.55)
    c1, c2 = int(W * 0.25), int(W * 0.75)

    crown = gray[r1:r2, c1:c2]

    if crown.size == 0:
        crown = gray

    # Smooth lighting
    crown = cv2.GaussianBlur(crown, (5, 5), 0)

    # Hair strand edges
    edges = cv2.Canny(crown, 40, 120)

    edge_density = np.mean(edges > 0)

    # Scalp brightness
    brightness = crown.mean()

    # Hair darkness ratio
    dark_ratio = np.mean(crown < 80)

    return edge_density, dark_ratio, brightness


# ───────────────────────── CLASSIFIER ─────────────────────────

def classify(edge_density, dark_ratio, brightness):

    score = (
        dark_ratio * 0.6 +
        edge_density * 0.3 +
        (1 - brightness / 255) * 0.1
    )

    if score > 0.45:
        label = "normal"
    elif score > 0.28:
        label = "moderate"
    else:
        label = "severe"

    return CLASSES.index(label), score


# ───────────────────────── ANALYZER CLASS ─────────────────────────

class HairDensityAnalyzer:

    def analyze(self, image):

        if not isinstance(image, Image.Image):
            image = Image.fromarray(image)

        edge_density, dark_ratio, brightness = extract_features(image)

        pred, _ = classify(edge_density, dark_ratio, brightness)

        return {
            "success": True,
            "prediction": CLASSES[pred],
        }