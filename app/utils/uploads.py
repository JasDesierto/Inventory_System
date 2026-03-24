import base64
import binascii
import os
import re
from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


class UploadError(ValueError):
    pass


CAPTURED_IMAGE_TYPES = {
    "image/gif": "gif",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def _allowed_file(filename):
    extension = filename.rsplit(".", 1)[-1].lower()
    return extension in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def _ensure_file_size(file_size):
    if file_size <= 0:
        raise UploadError("The uploaded image is empty.")
    if file_size > current_app.config["MAX_CONTENT_LENGTH"]:
        raise UploadError("The uploaded image is too large.")


def _store_image_bytes(image_bytes, extension):
    _ensure_file_size(len(image_bytes))

    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    unique_name = f"{uuid4().hex}.{extension}"
    absolute_path = upload_dir / unique_name
    absolute_path.write_bytes(image_bytes)
    return f"uploads/{unique_name}"


def save_uploaded_image(file_storage: FileStorage):
    if not file_storage or not file_storage.filename:
        raise UploadError("An image file is required.")

    filename = secure_filename(file_storage.filename)
    if "." not in filename or not _allowed_file(filename):
        raise UploadError("Upload a valid image file: png, jpg, jpeg, gif, or webp.")

    file_storage.stream.seek(0, os.SEEK_END)
    file_size = file_storage.stream.tell()
    file_storage.stream.seek(0)

    _ensure_file_size(file_size)

    unique_name = f"{uuid4().hex}_{filename}"
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    absolute_path = upload_dir / unique_name
    file_storage.save(absolute_path)
    return f"uploads/{unique_name}"


def save_captured_image(data_url):
    if not data_url:
        raise UploadError("A captured image is required.")

    match = re.match(r"^data:(image\/[a-zA-Z0-9.+-]+);base64,(.+)$", data_url, re.DOTALL)
    if not match:
        raise UploadError("The captured image data is not valid.")

    mime_type = match.group(1).lower()
    extension = CAPTURED_IMAGE_TYPES.get(mime_type)
    if not extension:
        raise UploadError("Capture a valid image using png, jpg, gif, or webp.")

    try:
        image_bytes = base64.b64decode(match.group(2), validate=True)
    except (ValueError, binascii.Error) as exc:
        raise UploadError("The captured image data could not be decoded.") from exc

    return _store_image_bytes(image_bytes, extension)


def save_form_image(file_storage: FileStorage, captured_data=None):
    if file_storage and file_storage.filename:
        return save_uploaded_image(file_storage)
    if captured_data:
        return save_captured_image(captured_data)
    raise UploadError("An image file or camera capture is required.")


def delete_uploaded_image(relative_path):
    if not relative_path:
        return
    if relative_path == current_app.config["DEFAULT_PHOTO_PATH"]:
        return
    absolute_path = Path(current_app.static_folder) / relative_path
    if absolute_path.exists():
        absolute_path.unlink()
