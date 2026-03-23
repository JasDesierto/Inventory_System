import os
from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


class UploadError(ValueError):
    pass


def _allowed_file(filename):
    extension = filename.rsplit(".", 1)[-1].lower()
    return extension in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def save_uploaded_image(file_storage: FileStorage):
    if not file_storage or not file_storage.filename:
        raise UploadError("An image file is required.")

    filename = secure_filename(file_storage.filename)
    if "." not in filename or not _allowed_file(filename):
        raise UploadError("Upload a valid image file: png, jpg, jpeg, gif, or webp.")

    file_storage.stream.seek(0, os.SEEK_END)
    file_size = file_storage.stream.tell()
    file_storage.stream.seek(0)

    if file_size <= 0:
        raise UploadError("The uploaded image is empty.")
    if file_size > current_app.config["MAX_CONTENT_LENGTH"]:
        raise UploadError("The uploaded image is too large.")

    unique_name = f"{uuid4().hex}_{filename}"
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    absolute_path = upload_dir / unique_name
    file_storage.save(absolute_path)
    return f"uploads/{unique_name}"


def delete_uploaded_image(relative_path):
    if not relative_path:
        return
    if relative_path == current_app.config["DEFAULT_PHOTO_PATH"]:
        return
    absolute_path = Path(current_app.static_folder) / relative_path
    if absolute_path.exists():
        absolute_path.unlink()
