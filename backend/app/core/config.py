import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    PROJECT_NAME: str = "Booking Assistant"
    
    # Base Dir: backend/
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    # Google
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None
    
    GOOGLE_SECRETS_JSON: Optional[str] = None
    GOOGLE_TOKEN_JSON: Optional[str] = None
    
    # Google AI (Gemini)
    GOOGLE_AI_API_KEY: Optional[str] = None
    
    # Files (Legacy/Local)
    SECRETS_FILE: str = "secrets.json"
    TOKEN_FILE: str = "tokens.json"
    PREFERENCES_FILE: str = "preferences.json"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def get_file_path(self, filename: str) -> Path:
        return self.BASE_DIR / filename

    def resolve_google_credentials(self) -> Dict[str, Any]:
        """
        Try to load from env vars first, then fallback to secrets.json
        """
        # Priority 1: Explicit Env Vars for ID/Secret
        if self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET:
            return {
                "web": {
                    "client_id": self.GOOGLE_CLIENT_ID,
                    "client_secret": self.GOOGLE_CLIENT_SECRET,
                    "redirect_uris": [self.GOOGLE_REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            }
            
        # Priority 2: JSON Blob in Env Var (Heroku style)
        if self.GOOGLE_SECRETS_JSON:
            return json.loads(self.GOOGLE_SECRETS_JSON)
            
        # Priority 3: Local File
        secrets_path = self.get_file_path(self.SECRETS_FILE)
        if secrets_path.exists():
            try:
                with open(secrets_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Error reading secrets file: %s", e)
        
        return {}

settings = Settings()
