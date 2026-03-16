import os
from PIL import Image

# Redirect caches to USB
os.environ["HF_HOME"] = r"D:\NAVSYS_USB\models\huggingface"
os.environ["TRANSFORMERS_CACHE"] = r"D:\NAVSYS_USB\models\huggingface"
os.environ["TORCH_HOME"] = r"D:\NAVSYS_USB\models\torch"
os.environ["XDG_CACHE_HOME"] = r"D:\NAVSYS_USB\models\cache"

from surya.foundation import FoundationPredictor
from surya.recognition import RecognitionPredictor
from surya.detection import DetectionPredictor

IMAGE_PATH = r"D:\NAVSYS_USB\sample_passport_page1.png"

def main():
    print("Initializing Surya foundation...")
    foundation = FoundationPredictor()

    print("Initializing detection...")
    detection_predictor = DetectionPredictor()

    print("Initializing recognition...")
    recognition_predictor = RecognitionPredictor(foundation)

    print("Loading image...")
    image = Image.open(IMAGE_PATH).convert("RGB")

    print("Running OCR...")
    predictions = recognition_predictor([image], det_predictor=detection_predictor)

    page = predictions[0]

    print("\n--- TEXT LINES ---\n")
    for line in page.text_lines:
        print(line.text)

if __name__ == "__main__":
    main()