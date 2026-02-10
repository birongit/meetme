import uuid
import re
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo
from typing import List, Dict, Optional, Any, Tuple

from googleapiclient.discovery import build
from app.services.google_auth import GoogleAuthService
from app.services.preferences import PreferencesService

class CalendarService:
    @staticmethod
    def get_service():
        creds = GoogleAuthService.load_credentials()
        if not creds:
            raise Exception("Unauthorized: No valid credentials found.")
        return build('calendar', 'v3', credentials=creds)

    @staticmethod
    def get_events(time_min: str = None, time_max: str = None, max_results: int = 10):
        service = CalendarService.get_service()
        
        kwargs = {
            'calendarId': 'primary',
            'singleEvents': True,
            'orderBy': 'startTime'
        }
        if time_min:
            kwargs['timeMin'] = time_min
        if time_max:
            kwargs['timeMax'] = time_max
        if not time_min and not time_max:
            kwargs['maxResults'] = max_results

        events_result = service.events().list(**kwargs).execute()
        return events_result.get('items', [])

    @staticmethod
    def is_slot_blocked(dt_start: datetime, dt_end: datetime, prefs: Dict[str, Any]) -> bool:
        """Checks if a slot overlaps with any blocked rules in preferences."""
        # Ensure dt_start/dt_end have timezone info for comparison
        if dt_start.tzinfo is None:
            dt_start = dt_start.replace(tzinfo=timezone.utc)
        
        # We need to check the day of the week in the user's local time or the rule's intended time.
        # The original code used the slot's timezone.
        
        for rule in prefs.get('no_meetings', []):
            if dt_start.strftime('%A') in rule['days']:
                rule_start_time = datetime.strptime(rule['start'], '%H:%M').time()
                rule_end_time = datetime.strptime(rule['end'], '%H:%M').time()

                if rule_end_time <= rule_start_time:
                    # Overnight rule (e.g. 22:00-07:00): split into two blocks
                    # Block 1: rule_start to midnight (same day)
                    b1_start = datetime.combine(dt_start.date(), rule_start_time).replace(tzinfo=dt_start.tzinfo)
                    b1_end = datetime.combine(dt_start.date() + timedelta(days=1), time(0, 0)).replace(tzinfo=dt_start.tzinfo)
                    # Block 2: midnight to rule_end (same day)
                    b2_start = datetime.combine(dt_start.date(), time(0, 0)).replace(tzinfo=dt_start.tzinfo)
                    b2_end = datetime.combine(dt_start.date(), rule_end_time).replace(tzinfo=dt_start.tzinfo)

                    if (dt_start < b1_end and dt_end > b1_start) or (dt_start < b2_end and dt_end > b2_start):
                        return True
                else:
                    block_start = datetime.combine(dt_start.date(), rule_start_time).replace(tzinfo=dt_start.tzinfo)
                    block_end = datetime.combine(dt_start.date(), rule_end_time).replace(tzinfo=dt_start.tzinfo)

                    if dt_start < block_end and dt_end > block_start:
                        return True
        return False

    @staticmethod
    def get_busy_ranges(events: List[Dict], tz: timezone) -> List[Tuple[datetime, datetime]]:
        busy = []
        for event in events:
            start = event['start'].get('dateTime') or event['start'].get('date')
            end = event['end'].get('dateTime') or event['end'].get('date')
            try:
                b_start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            except Exception:
                b_start_dt = datetime.strptime(start, '%Y-%m-%d').replace(tzinfo=tz)
            try:
                b_end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
            except Exception:
                b_end_dt = datetime.strptime(end, '%Y-%m-%d').replace(tzinfo=tz)
            busy.append((b_start_dt, b_end_dt))
        return busy

    @staticmethod
    def get_available_slots(user_tz_str: str = None) -> List[Dict[str, str]]:
        """
        Generates available 1-hour slots for the next 7 days.
        """
        service = CalendarService.get_service()
        
        # Determine timezone
        if not user_tz_str:
            cal_info = service.calendarList().get(calendarId='primary').execute()
            user_tz_str = cal_info.get('timeZone', 'UTC')
        
        try:
            tz = ZoneInfo(user_tz_str)
        except Exception:
            tz = timezone.utc

        now = datetime.now(tz)
        end_time = now + timedelta(days=7)
        
        # Fetch events
        events = CalendarService.get_events(
            time_min=now.isoformat(),
            time_max=end_time.isoformat()
        )
        
        busy = CalendarService.get_busy_ranges(events, tz)
        prefs = PreferencesService.get_preferences()
        
        # Build allowed time ranges per day (default 7am-10pm)
        allowed_ranges = {}
        for i in range(7):
            day = (now + timedelta(days=i)).date()
            allowed_ranges[day] = [(time(7,0), time(22,0))]

        # Apply hard blocks from preferences to allowed_ranges
        def subtract_block(ranges, b_start, b_end):
            """Subtract a block [b_start, b_end) from a list of time ranges."""
            new_ranges = []
            for r_start, r_end in ranges:
                if b_end <= r_start or b_start >= r_end:
                    new_ranges.append((r_start, r_end))
                else:
                    if r_start < b_start:
                        new_ranges.append((r_start, b_start))
                    if b_end < r_end:
                        new_ranges.append((b_end, r_end))
            return new_ranges

        for rule in prefs.get('no_meetings', []):
            rule_start = datetime.strptime(rule['start'], '%H:%M').time()
            rule_end = datetime.strptime(rule['end'], '%H:%M').time()

            for i in range(7):
                day = (now + timedelta(days=i))
                day_name = day.strftime('%A')
                if day_name in rule['days']:
                    if rule_end <= rule_start:
                        # Overnight rule: block from rule_start to midnight, and midnight to rule_end
                        allowed_ranges[day.date()] = subtract_block(
                            allowed_ranges[day.date()], rule_start, time(23, 59, 59))
                        # Apply the morning portion to the next day if it exists
                        next_day = (day + timedelta(days=1)).date()
                        if next_day in allowed_ranges:
                            allowed_ranges[next_day] = subtract_block(
                                allowed_ranges[next_day], time(0, 0), rule_end)
                    else:
                        allowed_ranges[day.date()] = subtract_block(
                            allowed_ranges[day.date()], rule_start, rule_end)

        legal_slots = []
        for i in range(7):
            day = (now + timedelta(days=i)).date()
            if day not in allowed_ranges: 
                continue
                
            for r_start, r_end in allowed_ranges[day]:
                slot_start_dt = datetime.combine(day, r_start, tzinfo=tz)
                
                while slot_start_dt.time() < r_end:
                    slot_end_dt = slot_start_dt + timedelta(hours=1)
                    
                    # Check if slot goes beyond range end
                    if slot_end_dt.time() > r_end and slot_end_dt.date() == slot_start_dt.date():
                         # If it stays on same day but exceeds time
                         break
                    if slot_end_dt.date() > slot_start_dt.date():
                        # Handle overnight if necessary, but here we assume daily ranges
                        break

                    # Check overlap with busy events
                    overlap = False
                    for b_start_dt, b_end_dt in busy:
                        if slot_start_dt < b_end_dt and slot_end_dt > b_start_dt:
                            overlap = True
                            break
                    
                    # Double check with is_slot_blocked (redundant but safe)
                    if not overlap and not CalendarService.is_slot_blocked(slot_start_dt, slot_end_dt, prefs):
                        legal_slots.append({
                            "start": slot_start_dt.isoformat(),
                            "end": slot_end_dt.isoformat()
                        })
                    
                    slot_start_dt += timedelta(hours=1)
                    
        return legal_slots

    @staticmethod
    def validate_slot(slot_start: datetime, slot_end: datetime, tz) -> None:
        """Validates that a slot doesn't conflict with busy events or preference rules."""
        now = datetime.now(tz)
        if slot_start < now:
            raise ValueError("Cannot book a slot in the past.")

        # Check preference rules
        prefs = PreferencesService.get_preferences()
        if CalendarService.is_slot_blocked(slot_start, slot_end, prefs):
            raise ValueError("This time slot is not available.")

        # Check busy events
        events = CalendarService.get_events(
            time_min=slot_start.isoformat(),
            time_max=slot_end.isoformat()
        )
        busy = CalendarService.get_busy_ranges(events, tz)
        for b_start, b_end in busy:
            if slot_start < b_end and slot_end > b_start:
                raise ValueError("This time slot conflicts with an existing event.")

    @staticmethod
    def book_slot(slot_data: Dict[str, Any]):
        service = CalendarService.get_service()

        # Validate the slot before booking
        start_dt = datetime.fromisoformat(slot_data['start'])
        end_dt = datetime.fromisoformat(slot_data['end'])
        tz = start_dt.tzinfo or timezone.utc
        CalendarService.validate_slot(start_dt, end_dt, tz)

        default_summary = 'Meeting with Birgit'

        event = {
            'summary': slot_data.get('summary') or default_summary,
            'start': {'dateTime': slot_data['start']},
            'end': {'dateTime': slot_data['end']},
            'conferenceData': {
                'createRequest': {
                    'requestId': str(uuid.uuid4()),
                    'conferenceSolutionKey': {
                        'type': 'hangoutsMeet'
                    }
                }
            }
        }
        
        if slot_data.get('email'):
            email = slot_data['email']
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                 raise ValueError("Invalid email address provided.")
            event['attendees'] = [{'email': email}]
            
        created_event = service.events().insert(
            calendarId='primary', 
            body=event, 
            sendUpdates='all',
            conferenceDataVersion=1
        ).execute()
        
        return created_event
