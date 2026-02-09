import json
import logging
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from app.core.config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events"
]

class GoogleAuthService:
    @staticmethod
    def get_flow(redirect_uri: str = None):
        """Creates a Google Auth Flow instance."""
        # If we have the secrets loaded in settings (from env or file)
        # We need to construct the client config dictionary expected by Flow.from_client_config
        
        # We need to ensure we have client_id and client_secret
        creds = settings.resolve_google_credentials()
        if not creds:
             raise ValueError("Google Credentials not found. Please set GOOGLE_CLIENT_ID/SECRET or secrets.json")

        # If creds came from resolve_google_credentials, it might be the full web config or just parts
        # But Flow.from_client_config expects the full dict structure {"web": ...}
        
        # If resolve_google_credentials returned the full dict (from file or env json)
        if "web" in creds or "installed" in creds:
            client_config = creds
        else:
            # Construct it manually if we only have ID/Secret (though resolve_google_credentials handles this)
            # But let's be safe
            client_config = {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            }
        
        return Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri or settings.GOOGLE_REDIRECT_URI
        )

    @staticmethod
    def get_authorization_url():
        flow = GoogleAuthService.get_flow()
        authorization_url, state = flow.authorization_url(
            access_type='offline', 
            include_granted_scopes='true'
        )
        return authorization_url

    @staticmethod
    def fetch_token(code: str):
        flow = GoogleAuthService.get_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials
        return credentials

    @staticmethod
    def save_credentials(credentials):
        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes
        }
        
        token_path = settings.get_file_path(settings.TOKEN_FILE)
        with open(token_path, "w") as f:
            json.dump(token_data, f)
        return token_data

    @staticmethod
    def load_credentials():
        """Loads credentials from storage (Env or File) and refreshes if needed."""
        token_data = None
        
        # 1. Try Env Var (Production/Heroku)
        if settings.GOOGLE_TOKEN_JSON:
            try:
                token_data = json.loads(settings.GOOGLE_TOKEN_JSON)
            except json.JSONDecodeError:
                logger.error("Error decoding GOOGLE_TOKEN_JSON")

        # 2. Try File (Local Dev)
        token_path = settings.get_file_path(settings.TOKEN_FILE)
        if not token_data and token_path.exists():
            with open(token_path, "r") as f:
                token_data = json.load(f)
        
        if not token_data:
            return None

        creds = Credentials(
            token=token_data["token"],
            refresh_token=token_data.get("refresh_token"),
            client_id=token_data["client_id"],
            client_secret=token_data["client_secret"],
            token_uri=token_data["token_uri"],
            scopes=SCOPES
        )

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(GoogleRequest())
                # Save refreshed token
                GoogleAuthService.save_credentials(creds)
            except Exception as e:
                logger.error("Error refreshing token: %s", e)
                return None
                
        return creds
