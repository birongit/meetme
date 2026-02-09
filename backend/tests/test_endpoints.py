from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

def test_get_preferences():
    mock_prefs = {"no_meetings": [], "batch_meetings": True}
    with patch("app.api.routes.PreferencesService.get_preferences", return_value=mock_prefs):
        response = client.get("/preferences")
        assert response.status_code == 200
        assert response.json() == mock_prefs

def test_update_preferences():
    new_prefs = {"no_meetings": [{"days": ["Monday"], "start": "09:00", "end": "10:00"}]}
    with patch("app.api.routes.PreferencesService.update_preferences", return_value=new_prefs):
        response = client.post("/preferences", json=new_prefs)
        assert response.status_code == 200
        assert response.json()["preferences"] == new_prefs

def test_get_calendar_events():
    mock_events = [{"summary": "Test Event", "start": {"dateTime": "2025-01-01T10:00:00Z"}, "end": {"dateTime": "2025-01-01T11:00:00Z"}}]
    with patch("app.api.routes.CalendarService.get_events", return_value=mock_events):
        response = client.get("/calendar/events")
        assert response.status_code == 200
        assert response.json() == {"events": mock_events}

def test_get_calendar_events_error():
    with patch("app.api.routes.CalendarService.get_events", side_effect=Exception("API Error")):
        response = client.get("/calendar/events")
        assert response.status_code == 500
        assert "API Error" in response.json()["error"]

def test_suggest_booking_ai():
    mock_slots = [{"start": "2025-01-02T10:00:00Z", "end": "2025-01-02T11:00:00Z"}]
    mock_ai_result = {
        "suggested_slots": mock_slots,
        "ai_message": "Here are some slots.",
        "raw_llm_output": "..."
    }
    
    # Mock both the calendar service (to get legal slots) and AI service (to rank them)
    with patch("app.api.routes.CalendarService.get_available_slots", return_value=mock_slots), \
         patch("app.api.routes.AIService.rank_slots", return_value=mock_ai_result):
        
        payload = {"timezone": "UTC", "user_feedback": "mornings please"}
        response = client.post("/booking/suggest-ai", json=payload)
        
        assert response.status_code == 200
        assert response.json()["suggested_slots"] == mock_slots
        assert response.json()["ai_message"] == "Here are some slots."

def test_suggest_booking_ai_test_mode():
    # Test the built-in test mode which bypasses services
    payload = {"test_mode": True}
    response = client.post("/booking/suggest-ai", json=payload)
    assert response.status_code == 200
    assert len(response.json()["suggested_slots"]) > 0
    assert "mock message" in response.json()["ai_message"]

def test_book_meeting_success():
    mock_event = {"id": "123", "summary": "Booked Meeting"}
    slot_data = {"start": "2025-01-02T10:00:00Z", "end": "2025-01-02T11:00:00Z", "email": "test@example.com"}
    
    with patch("app.api.routes.CalendarService.book_slot", return_value=mock_event):
        response = client.post("/booking/book", json=slot_data)
        assert response.status_code == 200
        assert response.json()["event"] == mock_event

def test_book_meeting_invalid_email():
    # The validation happens in the service, so we mock the service raising ValueError
    slot_data = {"start": "2025-01-02T10:00:00Z", "end": "2025-01-02T11:00:00Z", "email": "invalid-email"}
    
    with patch("app.api.routes.CalendarService.book_slot", side_effect=ValueError("Invalid email address provided.")):
        response = client.post("/booking/book", json=slot_data)
        assert response.status_code == 400
        assert "Invalid email" in response.json()["error"]
