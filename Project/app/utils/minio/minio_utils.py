"""
Utility functions for uploading and retrieving files from MinIO.

This module provides:
- upload_to_minio: Upload raw file bytes to a MinIO bucket.
- get_minio_file_url: Generate a presigned URL for retrieving an object.
"""

from datetime import timedelta
from app.extensions import init_minio

MINIO_BUCKET = "gofood-images"


def upload_to_minio(vendor_name, file_bytes, filename, content_type):
    """
    Upload a file to MinIO and return its object name.

    Parameters
    ----------
    vendor_name : str
        The vendor's folder name used as the MinIO directory.
    file_bytes : bytes
        Raw binary content of the file.
    filename : str
        The file name to save on MinIO.
    content_type : str
        MIME type of the file (e.g. "image/png").

    Returns
    -------
    str
        The full object name stored in the MinIO bucket.
    """
    object_name = f"{vendor_name}/{filename}"

    init_minio.put_object(
        bucket_name=MINIO_BUCKET,
        object_name=object_name,
        data=file_bytes,
        length=len(file_bytes),
        content_type=content_type,
    )

    return object_name


def get_minio_file_url(vendor_name, filename, expires=timedelta(hours=1)):
    """
    Generate a presigned URL to access a MinIO file.

    Parameters
    ----------
    vendor_name : str
        Name of vendor directory.
    filename : str
        Exact file name under the vendor's folder.
    expires : timedelta, optional
        Duration before the presigned URL expires. Default is 1 hour.

    Returns
    -------
    str
        A presigned URL string that grants temporary access to the object.
    """
    object_name = f"{vendor_name}/{filename}"

    return init_minio.presigned_get_object(
        bucket_name=MINIO_BUCKET,
        object_name=object_name,
        expires=expires
    )
