from PIL import Image

from surya.foundation import FoundationPredictor
from surya.detection import DetectionPredictor
from surya.recognition import RecognitionPredictor


IMAGE_PATH = r"D:\NAVSYS_USB\sample_passport_page1.png"


def main():

    print("Initializing Surya foundation...")
    foundation = FoundationPredictor()

    print("Initializing detection...")
    detector = DetectionPredictor(foundation)

    print("Initializing recognition...")
    recognizer = RecognitionPredictor(foundation)

    print("Loading image...")
    image = Image.open(IMAGE_PATH).convert("RGB")

    print("Running detection...")
    det = detector([image])

    print("Running recognition...")
    rec = recognizer([image], det)

    page = rec[0]

    print("\n--- TEXT LINES ---\n")

    for line in page.text_lines:
        print(line.text)


if __name__ == "__main__":
    main()