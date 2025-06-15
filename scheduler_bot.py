from google_calendar import get_calendar_service, find_free_slots, create_meeting
from voice import speak
from llm import chat_with_llm, extract_json_from_llm_response
from datetime import datetime, timedelta, timezone
import calendar
from dateutil import parser as date_parser

# State accumulator
MEETING_STATE = {
    "duration_minutes": None,
    "date": None,
    "time_pref": None,
    "deadline": None,
}


def parse_date_or_day(value):
    """
    Convert day names or natural date expressions to YYYY-MM-DD string
    """
    today = datetime.utcnow().date()
    try:
        # Try parsing as date
        dt = date_parser.parse(
            value, fuzzy=True, default=datetime.combine(today, datetime.min.time())
        )
        return dt.date().isoformat()
    except Exception:
        # Try parsing as day name
        try:
            target_weekday = list(calendar.day_name).index(value.capitalize())
            days_ahead = (target_weekday - today.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            target_date = today + timedelta(days=days_ahead)
            return target_date.isoformat()
        except ValueError:
            return None


def find_available_dates_before_deadline(service, duration_minutes, time_pref, deadline_str):
    """
    Find available dates before the deadline
    """
    deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
    today = datetime.utcnow().date()
    
    # If deadline is in the past, start from today
    start_date = max(today, today)
    
    available_dates = []
    current_date = start_date
    
    # Check up to 14 days or until deadline, whichever comes first
    max_days_to_check = min(14, (deadline_date - start_date).days + 1)
    days_checked = 0
    
    while current_date <= deadline_date and len(available_dates) < 7 and days_checked < max_days_to_check:
        days_checked += 1
        
        # Skip today if it's already past preferred time
        if current_date == today:
            current_datetime = datetime.now()
            try:
                time_obj = date_parser.parse(time_pref, fuzzy=True)
                preferred_time = current_datetime.replace(
                    hour=time_obj.hour, 
                    minute=time_obj.minute,
                    second=0,
                    microsecond=0
                )
                if current_datetime >= preferred_time:
                    current_date += timedelta(days=1)
                    continue
            except:
                pass
        
        # Check if this date has availability
        try:
            date_obj = datetime.combine(current_date, datetime.min.time())
            time_obj = date_parser.parse(time_pref, fuzzy=True)
            start_dt = datetime(
                date_obj.year,
                date_obj.month,
                date_obj.day,
                time_obj.hour,
                time_obj.minute,
                tzinfo=timezone.utc,
            )
            end_dt = start_dt + timedelta(minutes=duration_minutes)
            
            time_min = start_dt.isoformat()
            time_max = end_dt.isoformat()
            
            free_slots = find_free_slots(service, duration_minutes, time_min, time_max)
            
            if free_slots:
                day_name = current_date.strftime("%A")
                available_dates.append({
                    "date": current_date.isoformat(),
                    "day": day_name,
                    "formatted": current_date.strftime("%Y-%m-%d (%A)")
                })
        except Exception as e:
            print(f"Error checking date {current_date}: {e}")
        
        current_date += timedelta(days=1)
    
    return available_dates


def is_greeting_or_casual(user_input):
    """
    Check if the input is a greeting or casual conversation
    """
    greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 
                'how are you', 'what\'s up', 'whats up', 'sup', 'yo', 'hiya']
    casual_phrases = ['thanks', 'thank you', 'bye', 'goodbye', 'see you', 'ok', 'okay', 'cool']
    
    user_lower = user_input.lower().strip()
    
    # Check exact matches
    if user_lower in greetings + casual_phrases:
        return True
    
    # Check if input starts with common greetings
    for greeting in greetings:
        if user_lower.startswith(greeting):
            return True
    
    return False


def handle_greeting_or_casual(user_input):
    """
    Handle greetings and casual conversation
    """
    user_lower = user_input.lower().strip()
    
    # Greetings
    if any(greeting in user_lower for greeting in ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening']):
        return "Hello! I'm here to help you schedule meetings. You can tell me things like 'Schedule a 30-minute meeting on Monday at 2 PM' or 'I need a meeting before Friday at 10 AM'. What would you like to schedule?"
    
    # Appreciation
    if any(thanks in user_lower for thanks in ['thanks', 'thank you']):
        return "You're welcome! Is there anything else I can help you schedule?"
    
    # Goodbye
    if any(bye in user_lower for bye in ['bye', 'goodbye', 'see you']):
        return "Goodbye! Feel free to come back anytime you need to schedule a meeting."
    
    # Casual acknowledgments
    if user_lower in ['ok', 'okay', 'cool', 'got it']:
        return "Great! What would you like to schedule?"
    
    # Default for other casual inputs
    return "I'm here to help you schedule meetings. You can tell me the duration, date, and time you prefer. What meeting would you like to schedule?"


def process_request(user_input, service):
    # Check if it's a greeting or casual conversation first
    if is_greeting_or_casual(user_input):
        return handle_greeting_or_casual(user_input)
    
    # Build prompt showing current state
    prompt = f"""
Current meeting state:
{MEETING_STATE}

User input:
{user_input}

Instructions:
- If the user is providing a complete meeting request with duration, date, and time, extract all details and set is_date_selection to false
- If the user is just selecting a date (like "Sunday", "Monday", "option 1", etc.) from previously suggested options, set is_date_selection to true and only extract the date
- If the user is asking for suggestions or alternatives, set request_suggestions to true

Extract any new info in JSON:
{{
  "duration_minutes": int optional,
  "date": str optional (day or date),
  "time_pref": str optional,
  "deadline": str optional (day or date),
  "request_suggestions": bool optional (true if asking for available dates/times),
  "is_date_selection": bool optional (true if user is selecting from previously suggested dates)
}}
Only respond with JSON. If no new info, return {{}}
"""

    llm_response = chat_with_llm(prompt)
    print("LLM response:", llm_response)
    structured = extract_json_from_llm_response(llm_response)

    if not structured:
        return "I didn't catch any meeting details in your message. Could you please tell me about the meeting you'd like to schedule? For example, 'I need a 30-minute meeting on Monday at 2 PM'."

    # Handle suggestion requests
    if structured.get("request_suggestions", False):
        if not all([MEETING_STATE["duration_minutes"], MEETING_STATE["time_pref"], MEETING_STATE["deadline"]]):
            return "I need the meeting duration, preferred time, and deadline to suggest available dates."
        
        available_dates = find_available_dates_before_deadline(
            service, 
            MEETING_STATE["duration_minutes"], 
            MEETING_STATE["time_pref"], 
            MEETING_STATE["deadline"]
        )
        
        if not available_dates:
            return f"No available slots found before {MEETING_STATE['deadline']} at {MEETING_STATE['time_pref']}. Please try a different time or deadline."
        
        suggestion_text = "Here are available dates before your deadline:\n"
        for i, date_info in enumerate(available_dates, 1):
            suggestion_text += f"{i}. {date_info['formatted']}\n"
        suggestion_text += "\nPlease let me know which date you'd prefer."
        
        return suggestion_text

    # Handle date selections (don't reset state if user is just selecting a date)
    is_selecting_date = structured.get("is_date_selection", False) or (
        "date" in structured and 
        len(structured) == 1 and 
        any(MEETING_STATE[k] for k in ["duration_minutes", "time_pref", "deadline"])
    )

    # If structured includes duration/time_pref AND date, it's a new request (reset state)
    # If it's just a date selection, don't reset
    if not is_selecting_date and any(k in structured for k in ["duration_minutes", "time_pref"]):
        for k in MEETING_STATE:
            MEETING_STATE[k] = None

    # Update state
    for key in MEETING_STATE:
        if key in structured and structured[key]:
            MEETING_STATE[key] = structured[key]

    # Normalize date fields
    if MEETING_STATE["date"]:
        parsed = parse_date_or_day(MEETING_STATE["date"])
        if not parsed:
            return f"I couldn't understand the date: {MEETING_STATE['date']}. Please rephrase."
        MEETING_STATE["date"] = parsed

    if MEETING_STATE["deadline"]:
        parsed = parse_date_or_day(MEETING_STATE["deadline"])
        if not parsed:
            return f"I couldn't understand the deadline: {MEETING_STATE['deadline']}. Please rephrase."
        MEETING_STATE["deadline"] = parsed

    # Check for missing fields
    missing = [k for k, v in MEETING_STATE.items() if not v and k != "deadline"]
    if missing:
        return f"Could you provide the following missing details: {', '.join(missing)}?"

    # Check deadline validity - FIXED: Compare date objects, not strings
    if MEETING_STATE["deadline"]:
        meeting_date = datetime.strptime(MEETING_STATE["date"], "%Y-%m-%d").date()
        deadline_date = datetime.strptime(MEETING_STATE["deadline"], "%Y-%m-%d").date()
        
        if meeting_date > deadline_date:
            # Suggest available dates
            available_dates = find_available_dates_before_deadline(
                service, 
                MEETING_STATE["duration_minutes"], 
                MEETING_STATE["time_pref"], 
                MEETING_STATE["deadline"]
            )
            
            if available_dates:
                suggestion_text = f"The date {MEETING_STATE['date']} is after your deadline {MEETING_STATE['deadline']}. Here are available dates before the deadline:\n"
                for i, date_info in enumerate(available_dates, 1):
                    suggestion_text += f"{i}. {date_info['formatted']}\n"
                suggestion_text += "\nPlease choose one of these dates."
                return suggestion_text
            else:
                return f"The date you provided is after the deadline, and no slots are available before {MEETING_STATE['deadline']} at {MEETING_STATE['time_pref']}. Please try a different time or extend the deadline."

    # Schedule meeting
    try:
        duration = int(MEETING_STATE["duration_minutes"])
    except:
        return "Invalid duration."

    date_obj = datetime.strptime(MEETING_STATE["date"], "%Y-%m-%d")
    time_pref = MEETING_STATE["time_pref"]

    try:
        time_obj = date_parser.parse(time_pref, fuzzy=True)
        start_dt = datetime(
            date_obj.year,
            date_obj.month,
            date_obj.day,
            time_obj.hour,
            time_obj.minute,
            tzinfo=timezone.utc,
        )
    except:
        return f"Invalid time preference: {time_pref}"

    end_dt = start_dt + timedelta(minutes=duration)
    time_min = start_dt.isoformat()
    time_max = end_dt.isoformat()

    free_slots = find_free_slots(service, duration, time_min, time_max)

    if not free_slots:
        return "No available slots at that time. Please try another time."

    slot = free_slots[0]
    link = create_meeting(service, slot["start"], slot["end"])

    # Reset state
    for k in MEETING_STATE:
        MEETING_STATE[k] = None

    return f"Meeting scheduled from {slot['start']} to {slot['end']}. Link: {link}"


def main():
    service = get_calendar_service()
    speak("Hi! I can help schedule your meeting. What do you need?")
    while True:
        mode = input("Type 'voice' or 'text': ").strip().lower()
        if mode == "voice":
            from voice import listen

            user_input = listen()
        elif mode == "text":
            user_input = input("Please enter your meeting request: ")
        else:
            print("Invalid mode.")
            continue

        reply = process_request(user_input, service)
        speak(reply)
        print(reply)


if __name__ == "__main__":
    main()