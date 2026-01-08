import os
import stat
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

class LocalSecretStore:
    """
    Manages secrets stored as local files in a designated directory.
    Enforces restricted file permissions (0600).
    """
    def __init__(self, base_path: str = "/jaynowman/northstar-keys"):
        self.base_path = Path(base_path)
        self._ensure_storage_ready()

    def _ensure_storage_ready(self):
        """Ensure the directory exists and has restricted permissions."""
        if not self.base_path.exists():
            self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Ensure directory is 0700 (rwx------)
        current_mode = stat.S_IMODE(os.stat(self.base_path).st_mode)
        if current_mode != 0o700:
            os.chmod(self.base_path, 0o700)

    def _get_secret_path(self, name: str) -> Path:
        # Prevent directory traversal
        safe_name = Path(name).name
        return self.base_path / safe_name

    def put_secret(self, name: str, value: str) -> None:
        """Save a secret to a file with 0600 permissions."""
        self._ensure_storage_ready()
        path = self._get_secret_path(name)
        
        # Write file
        path.write_text(value, encoding="utf-8")
        
        # Enforce 0600 (rw-------)
        os.chmod(path, 0o600)

    def get_secret(self, name: str) -> Optional[str]:
        """Read a secret from disk. Returns None if not found."""
        path = self._get_secret_path(name)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def has_secret(self, name: str) -> Dict[str, bool]:
        """Check if secret exists without revealing it."""
        path = self._get_secret_path(name)
        exists = path.exists()
        return {
            "present": exists,
            # We could add last_modified here if needed
        }
