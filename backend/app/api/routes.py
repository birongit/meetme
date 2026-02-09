import logging

from fastapi import APIRouter, Request, Body
from fastapi.responses import RedirectResponse, JSONResponse
from typing import Dict, Any

from app.services.google_auth import GoogleAuthService
from app.services.calendar import CalendarService
from app.services.preferences import PreferencesService
from app.services.ai_service import AIService
from app.models.schemas import BookingRequest

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/")
def read_root():
    return {"message": "Booking backend is running (Modular Version)."}

@router.get("/authorize")
def authorize():
    authorization_url = GoogleAuthService.get_authorization_url()
    return RedirectResponse(authorization_url)

@router.get("/oauth2callback")
def oauth2callback(request: Request):
    code = request.query_params.get('code')
    if not code:
        return JSONResponse({"error": "Missing authorization code in callback."}, status_code=400)
    try:
        creds = GoogleAuthService.fetch_token(code)
        GoogleAuthService.save_credentials(creds)
        return JSONResponse({"message": "Tokens saved successfully."})
    except Exception as e:
        return JSONResponse({"error": f"OAuth2 callback failed: {str(e)}"}, status_code=500)

@router.get("/calendar/events")
def get_calendar_events():
    try:
        events = CalendarService.get_events()
        return {"events": events}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.get("/preferences")
def get_preferences():
    try:
        return PreferencesService.get_preferences()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.post("/preferences")
def update_preferences(prefs: Dict[str, Any] = Body(...)):
    try:
        updated = PreferencesService.update_preferences(prefs)
        return {"message": "Preferences updated.", "preferences": updated}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)



@router.post("/booking/suggest-ai")
async def suggest_booking_ai(request: Request):
    try:
        body = await request.json()
        user_tz = body.get("timezone")
        user_feedback = body.get("user_feedback")
        test_mode = body.get("test_mode")

        if test_mode:
             return {
                "suggested_slots": [
                    {"start": "2025-12-02T19:00:00-08:00", "end": "2025-12-02T20:00:00-08:00"},
                    {"start": "2025-12-03T19:00:00-08:00", "end": "2025-12-03T20:00:00-08:00"}
                ],
                "ai_message": "This is a mock message for testing purposes."
            }

        # 1. Get all legal slots
        legal_slots = CalendarService.get_available_slots(user_tz)
        
        # 2. Rank with AI
        result = AIService.rank_slots(legal_slots, user_feedback)
        
        if "error" in result:
             return JSONResponse(result, status_code=500)
             
        return result

    except Exception as e:
        logger.exception("Error in /booking/suggest-ai")
        return JSONResponse({"error": str(e)}, status_code=500)

@router.post("/booking/book")
def book_meeting(booking_request: BookingRequest):
    try:
        event = CalendarService.book_slot(booking_request.model_dump())
        return {"message": "Meeting booked!", "event": event}
    except ValueError as ve:
        return JSONResponse({"error": str(ve)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
