import json
import logging
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class PreferencesService:
    @staticmethod
    def get_preferences() -> Dict[str, Any]:
        prefs_path = settings.get_file_path(settings.PREFERENCES_FILE)
        if not prefs_path.exists():
            return {}
        try:
            with open(prefs_path, "r") as f:
                return json.load(f)
        except Exception:
            logger.warning("Failed to read preferences file, returning empty defaults")
            return {}

    @staticmethod
    def update_preferences(prefs: Dict[str, Any]):
        prefs_path = settings.get_file_path(settings.PREFERENCES_FILE)
        with open(prefs_path, "w") as f:
            json.dump(prefs, f, indent=2)
        return prefs
