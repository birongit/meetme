# Booking Backend

This is the backend for the Booking Page application, built with FastAPI.

## Structure

- `app/`: Main application package.
  - `api/`: API route definitions.
  - `core/`: Core configuration (settings, secrets).
  - `models/`: Pydantic data models.
  - `services/`: Business logic (Google Calendar, AI, Preferences).
  - `main.py`: Application entry point.

## Configuration

The application uses `pydantic-settings` for configuration.
It prioritizes Environment Variables (for Heroku) over local files.

- **Local Development**:
  - `secrets.json`: Contains Google Client secrets.
  - `tokens.json`: Contains Google User tokens (generated after auth).
  - `preferences.json`: User preferences for booking slots.

- **Production (Heroku)**:
  - Set `GOOGLE_SECRETS_JSON` env var with the content of `secrets.json`.
  - Set `GOOGLE_TOKEN_JSON` env var with the content of `tokens.json` (after initial local auth, or implement a DB storage).
  - Set `GOOGLE_AI_API_KEY` env var (for Gemini AI slot ranking).

## Running Locally

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install dependencies (if not already installed):
   ```bash
   pip install -r ../requirements.txt
   ```

3. Run the server:
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`.
Docs are available at `http://localhost:8000/docs`.
