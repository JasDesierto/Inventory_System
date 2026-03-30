import base64
import binascii
import re
from pathlib import Path
from uuid import uuid4

from flask import current_app, url_for
from werkzeug.datastructures import FileStorage
from werkzeug.utils import safe_join, secure_filename


class UploadError(ValueError):
    pass


CAPTURED_IMAGE_TYPES = {
    "image/gif": "gif",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

STATIC_UPLOAD_EXCLUSIONS = {
    "placeholder-supply.svg",
    "seed-paper.svg",
    "seed-toner.svg",
    "seed-writing.svg",
}


def _allowed_file(filename):
    extension = filename.rsplit(".", 1)[-1].lower()
    return extension in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def _ensure_file_size(file_size):
    if file_size <= 0:
        raise UploadError("The uploaded image is empty.")
    if file_size > current_app.config["MAX_CONTENT_LENGTH"]:
        raise UploadError("The uploaded image is too large.")


def _detect_image_extension(image_bytes):
    # Signature checks stop renamed non-image files from being stored as trusted photos.
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if image_bytes.startswith((b"\xff\xd8\xff\xe0", b"\xff\xd8\xff\xe1", b"\xff\xd8\xff\xe8", b"\xff\xd8\xff\xdb")):
        return "jpg"
    if image_bytes.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "webp"
    return None


def _extension_matches(expected_extension, detected_extension):
    normalized_expected = expected_extension.lower()
    if normalized_expected == "jpeg":
        normalized_expected = "jpg"
    return normalized_expected == detected_extension


def _protected_prefix():
    return current_app.config["PROTECTED_UPLOAD_PREFIX"]


def is_protected_upload(relative_path):
    return bool(relative_path and relative_path.startswith(_protected_prefix()))


def _resolve_protected_path(relative_path):
    filename = relative_path.removeprefix(_protected_prefix())
    resolved_path = safe_join(current_app.config["UPLOAD_FOLDER"], filename)
    if not resolved_path:
        raise UploadError("The stored image path is invalid.")
    return Path(resolved_path)


def _store_image_bytes(image_bytes, extension, original_name=None):
    # Uploaded filenames are never trusted directly; a random name is generated
    # and the original name is kept only as a sanitized suffix.
    _ensure_file_size(len(image_bytes))

    detected_extension = _detect_image_extension(image_bytes)
    if not detected_extension:
        raise UploadError("Upload a real image file: png, jpg, jpeg, gif, or webp.")
    if not _extension_matches(extension, detected_extension):
        raise UploadError("The uploaded image file does not match its file type.")

    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = secure_filename(original_name or "")
    suffix = f"_{safe_name}" if safe_name else ""
    unique_name = f"{uuid4().hex}{suffix}.{detected_extension}"
    absolute_path = upload_dir / unique_name
    absolute_path.write_bytes(image_bytes)
    return f"{_protected_prefix()}{unique_name}"


def photo_url_for(photo_path):
    # Protected uploads are served through an authenticated Flask route, while
    # bundled placeholder/seed assets still come from /static.
    if is_protected_upload(photo_path):
        filename = photo_path.removeprefix(_protected_prefix())
        return url_for("inventory.uploaded_photo", filename=filename)

    filename = photo_path or current_app.config["DEFAULT_PHOTO_PATH"]
    return url_for("static", filename=filename)


def save_uploaded_image(file_storage: FileStorage):
    if not file_storage or not file_storage.filename:
        raise UploadError("An image file is required.")

    filename = secure_filename(file_storage.filename)
    if "." not in filename or not _allowed_file(filename):
        raise UploadError("Upload a valid image file: png, jpg, jpeg, gif, or webp.")

    image_bytes = file_storage.read()
    return _store_image_bytes(
        image_bytes,
        filename.rsplit(".", 1)[-1],
        original_name=filename.rsplit(".", 1)[0],
    )


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
    # Add-supply accepts either a traditional file upload or a camera capture
    # from the browser, but never both as independent records.
    if file_storage and file_storage.filename:
        return save_uploaded_image(file_storage)
    if captured_data:
        return save_captured_image(captured_data)
    raise UploadError("An image file or camera capture is required.")


def delete_uploaded_image(relative_path):
    if not relative_path or relative_path == current_app.config["DEFAULT_PHOTO_PATH"]:
        return

    if is_protected_upload(relative_path):
        absolute_path = _resolve_protected_path(relative_path)
    else:
        static_path = safe_join(current_app.static_folder, relative_path)
        if not static_path:
            return
        absolute_path = Path(static_path)

    if absolute_path.exists():
        absolute_path.unlink()


def migrate_public_uploads(db, supply_model):
    moved_any = False

    # Seed artwork stays in the public static directory, but user-uploaded photos move to protected storage.
    for supply in supply_model.query.all():
        photo_path = supply.photo_path or ""
        if not photo_path.startswith("uploads/"):
            continue

        filename = Path(photo_path).name
        if filename in STATIC_UPLOAD_EXCLUSIONS:
            continue

        source_path = safe_join(current_app.static_folder, photo_path)
        if not source_path:
            continue

        source = Path(source_path)
        if not source.exists() or not source.is_file():
            continue

        image_bytes = source.read_bytes()
        detected_extension = _detect_image_extension(image_bytes)
        if not detected_extension:
            continue

        upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
        upload_dir.mkdir(parents=True, exist_ok=True)
        destination = upload_dir / filename
        if destination.exists():
            destination = upload_dir / f"{uuid4().hex}_{filename}"

        destination.write_bytes(image_bytes)
        source.unlink()

        supply.photo_path = f"{_protected_prefix()}{destination.name}"
        moved_any = True

    if moved_any:
        db.session.commit()
