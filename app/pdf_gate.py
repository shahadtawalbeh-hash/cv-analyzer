from pathlib import Path

MAX_UPLOAD_BYTES = 6 * 1024 * 1024
_PDF_MAGIC = b"%PDF"


class PdfRejected(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def validate_pdf_upload(original_name: str, raw_bytes: bytes) -> None:
    if not raw_bytes:
        raise PdfRejected("The uploaded file was empty.")
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise PdfRejected("PDF is too large. Keep it under 6 MB.")
    if not raw_bytes.startswith(_PDF_MAGIC):
        raise PdfRejected("This does not look like a real PDF (header check failed).")

    safe = Path(original_name).name
    if safe != original_name or ".." in safe:
        raise PdfRejected("Invalid file name.")
    lowered = safe.lower()
    if not lowered.endswith(".pdf"):
        raise PdfRejected("Only PDF files are accepted.")
    stem = Path(safe).stem
    if stem.lower().endswith(".pdf"):
        raise PdfRejected("File names like 'file.pdf.pdf' are blocked.")
