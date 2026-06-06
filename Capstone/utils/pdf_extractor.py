"""
PDF text extraction with OCR fallback for scanned/image-based documents.
Cascade: pdfplumber → pypdf → pytesseract OCR
"""
import io
import platform
from pathlib import Path
from loguru import logger

# ── Windows paths — update these if your install location is different ──────
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
POPPLER_PATH   = r'C:\poppler\Library\bin'

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    logger.warning("pdfplumber not installed")

try:
    from pdf2image import convert_from_bytes
    import pytesseract
    from PIL import Image

    # Set tesseract path directly — no need for system PATH on Windows
    if platform.system() == "Windows":
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    logger.warning("OCR dependencies missing: pdf2image / pytesseract / Pillow")

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False
    logger.warning("pypdf not installed")


class PDFExtractor:
    """
    Extracts text from PDF files.
    Cascade: pdfplumber → pypdf → pytesseract OCR.
    """
    MIN_TEXT_LENGTH = 20

    def extract_text(self, pdf_source: bytes | str | Path) -> str:
        if isinstance(pdf_source, (str, Path)):
            with open(pdf_source, "rb") as f:
                pdf_bytes = f.read()
        else:
            pdf_bytes = pdf_source

        # Step 1: pdfplumber
        text = self._extract_with_pdfplumber(pdf_bytes)

        # Step 2: pypdf fallback
        if len(text.strip()) < self.MIN_TEXT_LENGTH:
            logger.info("pdfplumber yielded little text, trying pypdf...")
            text = self._extract_with_pypdf(pdf_bytes)

        # Step 3: OCR fallback
        if len(text.strip()) < self.MIN_TEXT_LENGTH:
            logger.info("Native extraction insufficient, falling back to OCR...")
            text = self._extract_with_ocr(pdf_bytes)

        if len(text.strip()) < self.MIN_TEXT_LENGTH:
            logger.error(
                "All extraction methods returned minimal text. "
                "Check TESSERACT_PATH and POPPLER_PATH in pdf_extractor.py"
            )

        return text.strip()

    def _extract_with_pdfplumber(self, pdf_bytes: bytes) -> str:
        if not HAS_PDFPLUMBER:
            return ""
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}")
            return ""

    def _extract_with_pypdf(self, pdf_bytes: bytes) -> str:
        if not HAS_PYPDF:
            return ""
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            logger.warning(f"pypdf failed: {e}")
            return ""

    def _extract_with_ocr(self, pdf_bytes: bytes) -> str:
        if not HAS_OCR:
            logger.error(
                "OCR not available.\n"
                "Install: pip install pdf2image pytesseract Pillow\n"
                "Download Tesseract: https://github.com/UB-Mannheim/tesseract/wiki\n"
                "Download Poppler:   https://github.com/oschwartz10612/poppler-windows/releases"
            )
            return ""
        try:
            # Pass poppler_path only on Windows
            poppler_path = POPPLER_PATH if platform.system() == "Windows" else None

            logger.info("Running OCR on PDF pages...")
            images = convert_from_bytes(pdf_bytes, dpi=300, poppler_path=poppler_path)

            texts = []
            for i, img in enumerate(images):
                page_text = pytesseract.image_to_string(img, lang='eng')
                logger.info(f"OCR page {i+1}: {len(page_text)} chars extracted")
                texts.append(page_text)

            return "\n".join(texts)
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""