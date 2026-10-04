# NOVA — AI Discord Bot

NOVA is an AI-powered Discord bot built with Python.

It can have natural conversations, remember recent messages, store long-term user memories, and keep those memories even after the bot restarts.

This is my first complete AI project and was built to learn and practice Python, APIs, databases, asynchronous programming, Git, GitHub, and Discord bot development.

---

## Features

- AI-powered conversations using Google Gemini
- Natural Discord-style personality
- Conversation context
- Persistent SQLite database
- Long-term user memory
- Automatic memory detection
- Manual memory commands
- Per-user conversation history
- Discord typing indicator
- Secure API key storage using `.env`
- Git/GitHub version control
- Memory survives bot restarts

---

## How NOVA Works

```text
Discord User
     │
     ▼
Discord API
     │
     ▼
Python / discord.py
     │
     ├──── Conversation Manager
     │
     ├──── Memory System
     │          │
     │          ▼
     │       SQLite
     │
     ▼
Google Gemini API
     │
     ▼
AI Response
     │
     ▼
Discord
```

---

## Technologies

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| discord.py | Discord bot integration |
| Google Gemini API | AI response generation |
| SQLite | Persistent conversation and memory storage |
| python-dotenv | Secure environment variable loading |
| Git | Version control |
| GitHub | Source code hosting |

---

## Project Structure

```text
discord-ai-bot/
│
├── bot.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── .env        # Not uploaded to GitHub
├── nova.db     # Local memory database
└── .venv/      # Python virtual environment
```

The `.env`, `.venv`, and `nova.db` files are ignored by Git.

---

## Memory System

NOVA currently has two types of memory.

### Conversation Memory

NOVA keeps recent messages so follow-up conversations make sense.

Example:

```text
User: nova do you like Python?

NOVA: Yeah, Python is especially useful for projects like this.

User: why?

NOVA: Because it has simple syntax and a huge ecosystem of libraries.
```

The user does not need to repeat `nova` for every follow-up message.

### Long-Term Memory

Important information can be stored in SQLite and survives bot restarts.

Example:

```text
User: nova my favorite language is Python

NOVA: Nice choice!

User: nova memories

NOVA:
I remember:
- favorite language is Python
```

NOVA can also automatically detect some useful long-term information such as preferences and interests.

---

## Commands

```text
nova <message>
```

Starts a conversation with NOVA.

```text
nova stop
```

Stops the active conversation.

```text
nova memories
```

Shows stored long-term memories.

```text
nova remember that <fact>
```

Manually saves a memory.

```text
nova forget
```

Deletes recent conversation history.

```text
nova forget memories
```

Deletes long-term memories for the user.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Bahae47/discord-ai-bot.git
cd discord-ai-bot
```

### 2. Create a virtual environment

Windows:

```powershell
python -m venv .venv
```

### 3. Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. Create `.env`

Create a file called:

```text
.env
```

Add:

```env
DISCORD_TOKEN=your_discord_bot_token
GEMINI_API_KEY=your_gemini_api_key
```

Never upload `.env` or API keys to GitHub.

### 5. Run NOVA

```powershell
.\.venv\Scripts\python.exe bot.py
```

If everything is configured correctly:

```text
NOVA is online as NOVA
```

---

## Security

API keys and bot tokens are stored using environment variables.

The repository ignores:

```gitignore
.env
.venv/
nova.db
__pycache__/
```

This prevents secrets, the local virtual environment, and private conversation memory from being uploaded to GitHub.

---

## Current Status

NOVA's core functionality is working.

Current version includes:

```text
Discord bot              ✅
Gemini AI                ✅
Conversation context     ✅
SQLite database          ✅
Persistent memory        ✅
Automatic memory         ✅
Personality system       ✅
GitHub repository        ✅
24/7 deployment          ⏳
```

---

## Future Improvements

Planned improvements include:

- 24/7 cloud hosting
- Better automatic memory extraction
- Improved memory management
- Refactoring `bot.py` into multiple modules
- Slash commands
- Better multi-server support
- Admin configuration
- Improved error handling
- More advanced server behavior
- Optional image understanding
- Better database architecture

---

## What I Learned

This project helped me practice and understand:

```text
Python
Object-oriented concepts
Async programming
REST APIs
Discord API
AI APIs
Environment variables
SQLite databases
Persistent storage
Git
GitHub
Debugging
Basic software architecture
```

---

## Author

**Bahae47**

Software Engineering Student

GitHub: [@Bahae47](https://github.com/Bahae47)

---

## Disclaimer

NOVA is an independent educational project and is not affiliated with Discord or Google.
