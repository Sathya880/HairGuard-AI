import os
import requests

BASE_URL = "https://hair-app-user-images.s3.ap-south-1.amazonaws.com/models/"

FILES = [
    "attention_unet_hair.pth",
    "severity_model.pkl",
    "swin_scalp_presence.pth",
    "swin_dandruff_severity.pth"
]

os.makedirs("weights", exist_ok=True)

for file in FILES:

    path = f"weights/{file}"

    if os.path.exists(path):
        print(f"{file} already exists")
        continue

    url = BASE_URL + file
    print(f"Downloading {url}")

    r = requests.get(url)

    with open(path, "wb") as f:
        f.write(r.content)

print("All weights downloaded")