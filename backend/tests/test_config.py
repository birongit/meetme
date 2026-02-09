import json
import os
from unittest.mock import patch, MagicMock
from app.core.config import settings
from app.services.google_auth import GoogleAuthService

def test_resolve_google_credentials_env_var():
    # Mock environment variables
    fake_token_json = json.dumps({
        "web": {
            "client_id": "env_id",
            "client_secret": "env_sec",
            "redirect_uris": ["env_uri"],
            "auth_uri": "env_auth",
            "token_uri": "env_token"
        }
    })
    
    # We need to patch the settings object instance or the environment before settings is instantiated.
    # Since settings is already instantiated in app.core.config, we can patch the attribute on the instance.
    
    with patch.object(settings, 'GOOGLE_SECRETS_JSON', fake_token_json):
        creds = settings.resolve_google_credentials()
        assert creds["web"]["client_id"] == "env_id"

def test_resolve_google_credentials_explicit_env():
    with patch.object(settings, 'GOOGLE_CLIENT_ID', 'explicit_id'), \
         patch.object(settings, 'GOOGLE_CLIENT_SECRET', 'explicit_sec'):
        
        creds = settings.resolve_google_credentials()
        assert creds["web"]["client_id"] == "explicit_id"
        assert creds["web"]["client_secret"] == "explicit_sec"

def test_load_credentials_from_env_token():
    fake_token = {
        "token": "env_tok",
        "refresh_token": "env_ref",
        "token_uri": "env_uri",
        "client_id": "env_id",
        "client_secret": "env_sec",
        "scopes": ["scope"]
    }
    
    with patch.object(settings, 'GOOGLE_TOKEN_JSON', json.dumps(fake_token)):
        creds = GoogleAuthService.load_credentials()
        assert creds.token == "env_tok"
        assert creds.client_id == "env_id"
