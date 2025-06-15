from flask import Flask, request, jsonify, render_template
from scheduler_bot import process_request, MEETING_STATE
from google_calendar import get_calendar_service
import json

app = Flask(__name__)

# Initialize calendar service once
try:
    service = get_calendar_service()
    print("Calendar service initialized successfully")
except Exception as e:
    print(f"Error initializing calendar service: {e}")
    service = None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/process", methods=["POST"])
def process():
    data = request.get_json()
    user_message = data.get("message")
    
    if not user_message:
        return jsonify({"reply": "No message provided."}), 400
    
    if not service:
        return jsonify({"reply": "Calendar service is not available. Please check your Google Calendar setup."}), 500
    
    try:
        reply = process_request(user_message, service)
        return jsonify({
            "reply": reply,
            "meeting_state": MEETING_STATE  # Optional: return current state for debugging
        })
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({"reply": "Sorry, there was an error processing your request. Please try again."}), 500

@app.route("/state", methods=["GET"])
def get_state():
    """Optional endpoint to check current meeting state"""
    return jsonify({"meeting_state": MEETING_STATE})

@app.route("/reset", methods=["POST"])
def reset_state():
    """Optional endpoint to reset meeting state"""
    global MEETING_STATE
    for key in MEETING_STATE:
        MEETING_STATE[key] = None
    return jsonify({"reply": "Meeting state has been reset.", "meeting_state": MEETING_STATE})



if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)