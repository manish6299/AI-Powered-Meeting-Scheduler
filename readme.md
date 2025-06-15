# AI Meeting Scheduler

An intelligent meeting scheduler that uses natural language processing and voice commands to automatically schedule meetings in your Google Calendar.

## 🚀 Features

- **Natural Language Processing**: Schedule meetings using conversational language
- **Voice Interface**: Speak your meeting requests naturally
- **Google Calendar Integration**: Automatically creates calendar events
- **Smart Scheduling**: Finds available time slots and handles conflicts
- **Google Meet Integration**: Automatically generates video conference links
- **Conversation Memory**: Remembers context across multiple interactions

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.7 or higher
- pip (Python package installer)
- A Google account with Google Calendar access
- A microphone (for voice input)
- Speakers or headphones (for voice output)

## 🛠️ Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/ai-meeting-scheduler.git
cd ai-meeting-scheduler
```

### Step 2: Install Required Dependencies

```bash
pip install -r requirements.txt
```

If you don't have a `requirements.txt` file, install the dependencies manually:

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
pip install gemeni
pip install SpeechRecognition
pip install pyttsx3
pip install python-dateutil
pip install pyaudio
```

**Note for macOS users**: You may need to install `portaudio` first:
```bash
brew install portaudio
```

**Note for Windows users**: If you encounter issues with `pyaudio`, try:
```bash
pip install pipwin
pipwin install pyaudio
```

## 🔧 Configuration

### Step 3: Set Up Google Calendar API

1. **Go to Google Cloud Console**:
   - Visit [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one

2. **Enable Google Calendar API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Calendar API"
   - Click on it and press "Enable"

3. **Create Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Desktop Application" as the application type
   - Name your OAuth 2.0 client (e.g., "AI Meeting Scheduler")
   - Download the JSON file

4. **Save Credentials**:
   - Rename the downloaded file to `credentials.json`
   - Place it in your project root directory

### Step 4: Set Up OpenAI API

1. **Get OpenAI API Key**:
   - Go to [OpenAI Platform](https://platform.openai.com/)
   - Create an account or log in
   - Go to "API Keys" and create a new secret key
   - Copy the API key

2. **Configure API Key**:
   - Open `llm.py` file
   - Replace the API key in this line:
   ```python
   client = openai.OpenAI(api_key="YOUR_API_KEY_HERE")
   ```
   
   **Alternative (Recommended)**: Set as environment variable:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```
   
   Then modify `llm.py`:
   ```python
   client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
   ```

## 🚀 Running the Application

### Step 5: First Run

1. **Start the application**:
   ```bash
   python app.py
   ```

2. **Authenticate with Google**:
   - On first run, a browser window will open
   - Log in to your Google account
   - Grant calendar access permissions
   - Close the browser window after successful authentication

3. **Choose Input Mode**:
   - Type `voice` for voice input
   - Type `text` for text input

### Step 6: Using the Scheduler

#### Text Mode Examples:
```
"Schedule a 30-minute meeting on Monday at 2 PM"
"I need a meeting before Friday at 10 AM"
"Book a 1-hour call tomorrow at 3:30 PM"
```

#### Voice Mode:
- Speak naturally after seeing "Listening..."
- Wait for the system to process your request
- Follow the conversation flow

## 📁 Project Structure

```
ai-meeting-scheduler/
├── app.py              # Main application controller
├── google_calendar.py   # Google Calendar API integration
├── llm.py              # google API integration
├── voice.py            # Voice input/output handling
├── credentials.json    # Google API credentials (you create this)
├── token.json   
---scheduler.py       # Auto-generated OAuth token
├── requirements.txt    # Python dependencies
└── README.md   
       # This file
```

## 🔍 Troubleshooting

### Common Issues and Solutions

#### 1. **"credentials.json file not found"**
- Make sure you've downloaded the OAuth 2.0 credentials from Google Cloud Console
- Rename the file to exactly `credentials.json`
- Place it in your project root directory

#### 2. **"Invalid API key" (OpenAI)**
- Verify your OpenAI API key is correct
- Check if you have credits available in your OpenAI account
- Ensure the API key has the necessary permissions

#### 3. **"No module named 'pyaudio'"**
- For Windows: `pip install pipwin && pipwin install pyaudio`
- For macOS: `brew install portaudio && pip install pyaudio`
- For Linux: `sudo apt-get install python3-pyaudio`

#### 4. **Microphone not working**
- Check if your microphone is working in other applications
- Verify microphone permissions for your terminal/IDE
- Try running: `python -c "import speech_recognition as sr; print(sr.Microphone.list_microphone_names())"`

#### 5. **Calendar events not creating**
- Verify your Google Calendar API is enabled
- Check if the OAuth token has expired (delete `token.json` and re-authenticate)
- Ensure you have write permissions to your calendar

## 🎯 Usage Examples

### Example Conversations

**Complete Request:**
```
User: "Schedule a 30-minute meeting on Monday at 2 PM"
System: "Meeting scheduled from 2024-01-15T14:00:00+00:00 to 2024-01-15T14:30:00+00:00"
```

**Incremental Request:**
```
User: "I need a meeting"
System: "Could you provide the following missing details: duration_minutes, date, time_pref?"
User: "30 minutes on Friday at 3 PM"
System: "Meeting scheduled..."
```

**Conflict Handling:**
```
User: "Book a meeting tomorrow at 10 AM for 1 hour"
System: "No available slots at that time. Here are available times: ..."
User: "11 AM works"
System: "Meeting scheduled..."
```

## 🔐 Security Notes

- Keep your `credentials.json` file secure and never commit it to version control
- Store your OpenAI API key as an environment variable
- The `token.json` file is auto-generated and should also be kept secure
- Add these files to your `.gitignore`:
  ```
  credentials.json
  token.json
  .env
  ```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘
