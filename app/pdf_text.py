from io import BytesIO

from pypdf import PdfReader


def extract_pdf_text(raw_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(raw_bytes))
    chunks: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        chunks.append(text)
    joined = "\n".join(chunks).strip()
    if len(joined) < 40:
        return joined + "\n\nLittle text was extracted; the PDF may be image-only."
    return joined
