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
    today = datetime.utcnow().date()
    try:
        dt = date_parser.parse(
            value, fuzzy=True, default=datetime.combine(today, datetime.min.time())
        )
        return dt.date().isoformat()
    except Exception:
        try:
            target_weekday = list(calendar.day_name).index(value.capitalize())
            days_ahead = (target_weekday - today.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            target_date = today + timedelta(days=days_ahead)
            return target_date.isoformat()
        except ValueError:
            return None


def find_available_dates_before_deadline(
    service, duration_minutes, time_pref, deadline_str
):
    deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
    today = datetime.utcnow().date()

    # If deadline is in the past, start from today
    start_date = max(today, today)

    available_dates = []
    current_date = start_date

    # Check up to 14 days or until deadline, whichever comes first
    max_days_to_check = min(14, (deadline_date - start_date).days + 1)
    days_checked = 0

    while (
        current_date <= deadline_date
        and len(available_dates) < 7
        and days_checked < max_days_to_check
    ):
        days_checked += 1

        # Skip today if it's already past preferred time
        if current_date == today:
            current_datetime = datetime.now()
            try:
                time_obj = date_parser.parse(time_pref, fuzzy=True)
                preferred_time = current_datetime.replace(
                    hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0
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
                available_dates.append(
                    {
                        "date": current_date.isoformat(),
                        "day": day_name,
                        "formatted": current_date.strftime("%Y-%m-%d (%A)"),
                    }
                )
        except Exception as e:
            print(f"Error checking date {current_date}: {e}")

        current_date += timedelta(days=1)

    return available_dates


def is_greeting_or_casual(user_input):
    """
    Check if the input is a greeting or casual conversation
    """
    greetings = [
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you",
        "what's up",
        "whats up",
        "sup",
        "yo",
        "hiya",
    ]
    casual_phrases = [
        "thanks",
        "thank you",
        "bye",
        "goodbye",
        "see you",
        "ok",
        "okay",
        "cool",
    ]

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
    if any(
        greeting in user_lower
        for greeting in [
            "hi",
            "hello",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
        ]
    ):
        return "Hello! I'm here to help you schedule meetings. You can tell me things like 'Schedule a 30-minute meeting on Monday at 2 PM' or 'I need a meeting before Friday at 10 AM'. What would you like to schedule?"

    # Appreciation
    if any(thanks in user_lower for thanks in ["thanks", "thank you"]):
        return "You're welcome! Is there anything else I can help you schedule?"

    # Goodbye
    if any(bye in user_lower for bye in ["bye", "goodbye", "see you"]):
        return "Goodbye! Feel free to come back anytime you need to schedule a meeting."

    # Casual acknowledgments
    if user_lower in ["ok", "okay", "cool", "got it"]:
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

You are a helpful and efficient calendar assistant. Your current date and time is {{CURRENT_DATETIME}}.

**Your primary goal is to manage calendar events, either by creating new ones or searching existing ones.**

**Here's how to handle requests:**
- **If the user wants to create an event:**
  - **First, gather all essential details:** This includes the **title**, **start time**, and **end time** (or duration to calculate the end time).
  - **Always ask clarifying questions** if any of these critical pieces of information are missing. Be specific about what you need.
  - **Once you have the title, start time, and end time, use the `search_calendar_event` tool to check for any overlapping or conflicting events.**
  - **If `search_calendar_event` finds conflicts:** Report these conflicts clearly to the user. Ask if they want to proceed with the current time, suggest alternative times, or if they wish to alter the event details.
  - **If no conflicts are found, or the user confirms despite conflicts:** Proceed to use the `create_calendar_event` tool.
  - **After creating the event, confirm with the user** and provide the event link if available.

- **If the user wants to search for events:**
  - Directly use the `search_calendar_event` tool. If parameters like `event_name` or `time_min` are missing, ask for them before searching.
  - If the user refuses to provide the minimum time, consider the current time as minimum time (in ISO format).

- **If the user asks for the current time:** Use the `get_current_date_time` tool.

- **If the user wants to delete events:**
  - Use `delete_calendar_event` tool if the event_id is known, else use the `search_calendar_event` tool to find the event_id (link) and use `delete_event` tool.

- **If the user wants to list the events:**
  - Use the `list_calendar_event` tool to list the events starting from a minimum time range.

- **For unrelated requests:** Politely inform the user that you specialize in calendar management and cannot assist with that specific request.

**Key principles for interaction:**
- Maintain a natural and conversational tone.
- Be proactive in asking for missing information.
- Be clear and concise in your responses.

### Example 1: Creating a Meeting
**User:** I need to schedule a meeting.  
**Bot:** Sure! How long should the meeting be?  
**User:** 1 hour.  
**Bot:** Got it. Do you have a preferred day or time?  
**User:** Sometime on Tuesday afternoon.  
**Bot:** Great. I see 2:00 PM and 4:30 PM available on Tuesday. Which works best for you?  
**User:** 2:00 PM works for me.  
**Bot:** Perfect! I've scheduled the meeting for 2:00 PM on Tuesday. Anything else I can help you with?

### Example 2: Rescheduling Due to Conflict
**User:** I'm going to a party this Sunday.  
**Bot:** Nice! How long will the party last?  
**User:** About 3 hours, starting at 5 PM.  
**Bot:** Just a heads-up — you have a meeting at 7 PM on Sunday. Do you want to reschedule it or proceed as planned?  
**User:** Oh, I forgot. Can you move it to 8 PM?  
**Bot:** Sure! Would 8:30 PM work better to give you a little buffer after the party?  
**User:** Yes, that’s better.  
**Bot:** Great! I’ve rescheduled your meeting to 8:30 PM on Sunday.

### Example 3: Flexible Duration & Time Parsing
**User:** Can you create an event for a test interview?  
**Bot:** Of course! What date and time do you want the interview?  
**User:** It is in 5 hours from now.  
**Bot:** Got it! How long should the interview last?  
**User:** I have no idea, can you suggest a time?  
**Bot:** Typically, interviews last about 30 minutes to an hour. Would you like to schedule it for 30 minutes?  
**User:** Yes, 30 minutes is fine.  
**Bot:** Great! I’ll create the event for 30 minutes starting in 5 hours. Anything else you need?  
**User:** No, that’s all for now. Thanks!

Extract any new info in JSON:
{{
  "duration_minutes": 30,
  "date": "in 5 hours",
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
        if not all(
            [
                MEETING_STATE["duration_minutes"],
                MEETING_STATE["time_pref"],
                MEETING_STATE["deadline"],
            ]
        ):
            return "I need the meeting duration, preferred time, and deadline to suggest available dates."

        available_dates = find_available_dates_before_deadline(
            service,
            MEETING_STATE["duration_minutes"],
            MEETING_STATE["time_pref"],
            MEETING_STATE["deadline"],
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
        "date" in structured
        and len(structured) == 1
        and any(MEETING_STATE[k] for k in ["duration_minutes", "time_pref", "deadline"])
    )

    # If structured includes duration/time_pref AND date, it's a new request (reset state)
    # If it's just a date selection, don't reset
    if not is_selecting_date and any(
        k in structured for k in ["duration_minutes", "time_pref"]
    ):
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
                MEETING_STATE["deadline"],
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
