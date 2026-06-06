import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

# Windows — explicit path to tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

with open('notice_2.pdf', 'rb') as f:
    data = f.read()

print("Converting PDF pages to images...")
images = convert_from_bytes(data, dpi=300, poppler_path=r'C:\poppler\Library\bin')
print(f"Total pages: {len(images)}")

for i, img in enumerate(images):
    text = pytesseract.image_to_string(img, lang='eng')
    print(f"\nPage {i+1} ({len(text.strip())} chars):")
    print(text[:500])