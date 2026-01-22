import imghdr
import os

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
MAX_FILE_SIZE_MB = 5  # maximum file size in MB


def allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_image(file_storage):
    """
    Validate uploaded image file type and size from a FileStorage object.
    
    Raises:
        ValueError: If the file is invalid.
    """
    filename = file_storage.filename
    if not allowed_file(filename):
        raise ValueError("Unsupported file type")

    file_storage.seek(0, os.SEEK_END)
    size_mb = file_storage.tell() / (1024 * 1024)
    file_storage.seek(0)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError("File too large (max 5MB)")

    # Check file signature
    header = file_storage.read(512)
    file_storage.seek(0)
    if not imghdr.what(None, header):
        raise ValueError("File is not a valid image")

    return True


def validate_image_bytes(file_bytes: bytes, filename: str):
    """
    Validate image bytes for type and size.
    
    Args:
        file_bytes (bytes): Image content.
        filename (str): Name of the file to check extension.
    
    Raises:
        ValueError: If file is invalid.
    """
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file type")

    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError("File too large (max 5MB)")

    header = file_bytes[:512]
    if not imghdr.what(None, header):
        raise ValueError("File is not a valid image")

    return True


def save_account_number_to_env(account_number, key="ADMIN_ACCOUNT_NUMBER", env_path=".env"):
    # Read current .env, update or add the key, write back.
    try:
        # Read existing .env to memory if exists
        lines = []
        updated = False
        try:
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith(f"{key}="):
                        lines.append(f"{key}={account_number}\n")
                        updated = True
                    else:
                        lines.append(line)
        except FileNotFoundError:
            pass  # .env doesn't exist yet; we'll create it

        if not updated:
            lines.append(f"{key}={account_number}\n")

        with open(env_path, "w") as f:
            f.writelines(lines)

        print(f"Saved {key} to {env_path}")
    except Exception as ex:
        print(f"Error updating .env: {ex}")
