"""File storage service."""
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from app.config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE


def get_file_type(filename: str) -> Optional[str]:
    """Determine file type category from filename extension."""
    ext = Path(filename).suffix.lower()

    for file_type, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return file_type

    return None


def validate_file(file: UploadFile) -> tuple[bool, str]:
    """Validate an uploaded file."""
    # Check file type
    file_type = get_file_type(file.filename)
    if file_type is None:
        allowed = []
        for exts in ALLOWED_EXTENSIONS.values():
            allowed.extend(exts)
        return False, f"File type not allowed. Allowed types: {', '.join(allowed)}"

    return True, file_type


async def save_file(file: UploadFile, category: str) -> tuple[str, int]:
    """
    Save an uploaded file to the filesystem.

    Returns:
        tuple: (relative_path, file_size)
    """
    # Generate unique filename
    ext = Path(file.filename).suffix.lower()
    unique_name = f"{uuid.uuid4()}{ext}"

    # Determine subdirectory based on category
    if category == "excel":
        subdir = "reports"
    elif category == "presentation":
        subdir = "presentations"
    else:
        subdir = "articles"

    # Full path
    file_path = UPLOAD_DIR / subdir / unique_name

    # Read and save file
    contents = await file.read()
    file_size = len(contents)

    # Check file size
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"File too large. Maximum size is {MAX_FILE_SIZE // 1024 // 1024}MB")

    with open(file_path, "wb") as f:
        f.write(contents)

    # Return relative path for storage in database
    relative_path = f"{subdir}/{unique_name}"

    return relative_path, file_size


def delete_file(relative_path: str) -> bool:
    """Delete a file from the filesystem."""
    file_path = UPLOAD_DIR / relative_path

    if file_path.exists():
        os.remove(file_path)
        return True

    return False


def get_file_path(relative_path: str) -> Path:
    """Get the full path to a file."""
    return UPLOAD_DIR / relative_path
