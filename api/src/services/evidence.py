import hashlib
import io
import os
import uuid
import pymupdf
from PIL import Image
import imagehash
from fastapi import UploadFile, HTTPException


ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def validate_file_content(content: bytes, content_type: str) -> str:
    """Validates file magic bytes to prevent spoofing and path traversal."""
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed 10 MB limit.")

    # Check magic bytes
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    elif content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only valid PDF, JPEG, and PNG files are supported.",
        )


def compute_hashes(content: bytes, mime_type: str) -> tuple[str, str | None]:
    """Computes SHA-256 and Perceptual Hash (pHash) of the document."""
    sha256 = hashlib.sha256(content).hexdigest()
    phash_str = None

    try:
        if mime_type == "application/pdf":
            # Render first page of PDF to image to compute pHash
            doc = pymupdf.open(stream=content, filetype="pdf")
            if len(doc) > 0:
                page = doc[0]
                pix = page.get_pixmap(dpi=100)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                phash_str = str(imagehash.phash(img))
        else:
            img = Image.open(io.BytesIO(content))
            phash_str = str(imagehash.phash(img))
    except Exception:
        # If image rendering fails, phash remains None
        pass

    return sha256, phash_str


def save_upload_file(content: bytes, mime_type: str, upload_dir: str = "./uploads") -> str:
    """Saves file to upload directory using a sanitized UUID filename."""
    os.makedirs(upload_dir, exist_ok=True)
    ext = ALLOWED_MIME_TYPES.get(mime_type, ".bin")
    safe_filename = f"ev_{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, safe_filename)
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path
