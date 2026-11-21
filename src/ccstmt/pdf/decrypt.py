"""PDF decryption with password handling."""

from pathlib import Path

import pikepdf


def decrypt_pdf(
    pdf_path: Path, password: str = ""
) -> bytes:
    """Decrypt PDF and return decrypted bytes.

    Tries empty password first, then uses provided password.
    Raises ValueError if decryption fails.
    """
    try:
        # Try without password first
        with pikepdf.open(str(pdf_path)) as pdf:
            if pdf.is_encrypted:
                # Try with provided password
                try:
                    pdf.save("/dev/null")  # Test if password works
                except pikepdf.PdfError:
                    if password:
                        pdf = pikepdf.open(str(pdf_path), password=password)
                    else:
                        raise ValueError("PDF is encrypted but no password provided")

            # Read the decrypted PDF into memory
            with pikepdf.open(str(pdf_path), password=password) as decrypted_pdf:
                return decrypted_pdf.write()

    except pikepdf.PdfError as e:
        raise ValueError(f"Failed to decrypt PDF: {e}") from e
    except Exception as e:
        raise ValueError(f"PDF processing error: {e}") from e
