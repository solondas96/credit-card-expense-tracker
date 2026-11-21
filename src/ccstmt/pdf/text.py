"""PDF text extraction with layout preservation."""

from pathlib import Path

import pdfplumber


def extract_text(pdf_path: Path) -> tuple[str, bool]:
    """Extract text from PDF with layout preservation.

    Returns (text, is_scanned):
    - text: Full extracted text from all pages
    - is_scanned: True if PDF appears to be scanned (image-only, no text)
    """
    all_text = []
    page_count = 0
    empty_page_count = 0

    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            page_count = len(pdf.pages)

            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)
                else:
                    empty_page_count += 1

        full_text = "\n\n".join(all_text)

        # Detect scanned PDF: if more than 50% of pages have no text
        is_scanned = (empty_page_count / max(page_count, 1)) > 0.5

        # Also check if total extracted text is very small
        if len(full_text.strip()) < 100:
            is_scanned = True

        return full_text, is_scanned

    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {e}") from e
