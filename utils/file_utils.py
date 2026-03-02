"""File operation utilities."""
import shutil
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

def ensure_directory(directory: str) -> Path:
    """Ensure directory exists, create if it doesn't.

    Args:
        directory: Directory path

    Returns:
        Path object
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path

def backup_file(source: str, backup_dir: str = "backups") -> str:
    """Create a backup of a file with timestamp.

    Args:
        source: Source file path
        backup_dir: Backup directory

    Returns:
        Path to backup file
    """
    source_path = Path(source)
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    backup_path = ensure_directory(backup_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{source_path.stem}_{timestamp}{source_path.suffix}"
    backup_file_path = backup_path / backup_filename

    shutil.copy2(source, backup_file_path)
    logger.info(f"Backup created: {backup_file_path}")

    return str(backup_file_path)

def restore_file(backup: str, destination: str) -> None:
    """Restore a file from backup.

    Args:
        backup: Backup file path
        destination: Destination file path
    """
    backup_path = Path(backup)
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup}")

    shutil.copy2(backup, destination)
    logger.info(f"File restored from backup: {backup} -> {destination}")
