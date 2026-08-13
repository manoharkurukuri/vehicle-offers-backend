"""Uploads generated Excel workbooks to Cloudinary and returns their URL.

Cloudinary stores non-image assets (like .xlsx) under ``resource_type="raw"``.
The backend keeps only the returned secure URL + public_id in the database; no
file is retained on the server.
"""

import cloudinary
import cloudinary.uploader

from app.core.config import settings
from app.core.exceptions import FileStorageError


class CloudinaryStorageService:
    def __init__(self) -> None:
        if not (
            settings.cloudinary_cloud_name
            and settings.cloudinary_api_key.get_secret_value()
            and settings.cloudinary_api_secret.get_secret_value()
        ):
            raise FileStorageError(
                "Cloudinary is not configured. Set CLOUDINARY_CLOUD_NAME, "
                "CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET."
            )

        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key.get_secret_value(),
            api_secret=settings.cloudinary_api_secret.get_secret_value(),
            secure=True,
        )

    def upload(self, file_path: str, file_name: str) -> tuple[str, str]:
        """Upload a local file and return (secure_url, public_id)."""
        try:
            result = cloudinary.uploader.upload(
                file_path,
                resource_type="raw",
                folder=settings.cloudinary_folder,
                public_id=file_name,
                use_filename=True,
                unique_filename=True,
                overwrite=False,
            )
        except Exception as exc:
            raise FileStorageError(
                f"Failed to upload workbook to Cloudinary: {exc}"
            ) from exc

        secure_url = result.get("secure_url")
        public_id = result.get("public_id")
        if not secure_url or not public_id:
            raise FileStorageError(
                "Cloudinary upload returned no secure_url/public_id."
            )
        return secure_url, public_id

    def delete(self, public_id: str) -> None:
        """Best-effort removal of an uploaded asset (used on DB rollback)."""
        try:
            cloudinary.uploader.destroy(public_id, resource_type="raw")
        except Exception:
            pass
