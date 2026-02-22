# Booking Page Application

A full-stack application for booking meetings, powered by AI.

## Project Structure

- `backend/`: FastAPI application handling calendar logic and AI integration.
- `frontend/`: React application for the user interface.

## Quick Start

### 1. Start the Backend

```bash
# Set up virtual environment (one-time, from repo root)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Activate venv (each session)
source venv/bin/activate

# Run server
cd backend && uvicorn app.main:app --reload
```

The backend runs on `http://localhost:8000`.

### 2. Start the Frontend

Open a new terminal:

```bash
cd frontend
# Install dependencies
npm install
# Run app
npm start
```

The frontend runs on `http://localhost:3000`.

## Features

- **AI Slot Ranking**: Uses LangChain and Google Gemini to rank meeting slots based on user preferences.
- **Google Calendar Integration**: Fetches real-time availability and books events.
- **Modern UI**: Clean React interface with debug mode for inspecting AI logic.
