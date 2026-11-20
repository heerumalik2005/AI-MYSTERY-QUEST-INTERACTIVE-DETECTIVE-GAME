# AI Mystery Quest

A responsive detective game built with Python, Flask, HTML, CSS, and vanilla JavaScript. Groq AI is optional: without a key, the game automatically uses two playable demo cases.

## Features
- AI-generated cases through the official Groq Python SDK (when configured)
- Offline Demo Mode with two complete mysteries
- Evidence examination, suspect profiles, puzzle scoring, progressive hints
- Context-aware detective assistant with a no-spoiler rule
- Final accusation, score updates, and JSON game history
- Flask session state and responsive mobile-friendly UI

## Windows PowerShell setup

```powershell
cd AI_Mystery_Quest
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
FLASK_SECRET_KEY=replace-with-a-long-random-secret
```

Get an API key from https://console.groq.com/ (create an account, open the API keys section, and create a key). Keep it private. The `.env` file is ignored by Git and the key is read only by Python.

If you leave `GROQ_API_KEY` empty, the application starts in Demo Mode and remains fully playable.

Run:

```powershell
python app.py
```

Open http://127.0.0.1:5000

If PowerShell blocks virtual-environment activation, run this in the current terminal and retry activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Project structure

```text
AI_Mystery_Quest/
├── app.py                  # Flask routes, sessions, request validation
├── ai_service.py           # Groq SDK, JSON validation, hints and chat
├── game_logic.py           # Demo data, safe clue filtering, score history
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── data/
│   └── demo_cases.json     # Two fully playable offline cases
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── dashboard.html
│   ├── investigation.html
│   └── history.html
└── static/
    ├── css/style.css
    ├── js/script.js
    └── images/
```

## How the application works

1. The landing page links to the dashboard.
2. Starting a case attempts Groq generation. If no key exists or generation/validation fails, a predefined demo case is loaded.
3. The active case, discovered clue IDs, score, puzzle completions, and hint count are stored in Flask's signed session cookie.
4. Evidence details are sent to the browser only after the `/api/examine` route records discovery.
5. Puzzle answers and accusations are validated on the server, not trusted from JavaScript.
6. The final accusation ends the case, reveals the explanation, and appends a result to `data/history.json`.

## Main routes

| Route | Purpose |
|---|---|
| `GET /` | Welcome page |
| `GET /dashboard` | Score summary and recent cases |
| `POST /new-game` | Generate an AI case or load a demo case |
| `GET /investigation` | Active case interface |
| `POST /api/examine` | Reveal one evidence detail |
| `POST /api/puzzle` | Validate puzzle answer and award points |
| `POST /api/hint` | Return a progressive hint and deduct points |
| `POST /api/chat` | Ask the case-aware detective assistant |
| `POST /api/accuse` | Validate final suspect selection and save result |
| `GET /history` | Display completed investigations |

## Scoring

- Correct accusation: +100
- Correct puzzle: +20 (once per puzzle)
- Hint: -10 per hint
- Incorrect accusation: -20

A wrong puzzle answer does not change the score.

## Viva preparation

**Why Flask?** Flask is a lightweight Python web framework. It maps URLs to Python functions and renders HTML templates.

**What is a route?** A route connects an HTTP method and URL to a Python function, such as `@app.get("/")`.

**What is a session?** Flask sessions store small per-player state between requests. They are signed by Flask using the secret key. This project stores the active case state in the session.

**Why JSON history?** JSON is human-readable and sufficient for a small local coursework project. For a multi-user production game, use a database and server-side sessions.

**How is the API key protected?** `python-dotenv` loads `.env` on the server. The Groq SDK reads `GROQ_API_KEY` in Python. The key is never included in a template or JavaScript response, and `.env` is excluded from Git.

**How does the AI generate a case?** `ai_service.py` sends a schema request to Groq with JSON response mode. The returned JSON is parsed and validated before the game accepts it. If generation fails, the route falls back to a demo case.

**How are clues hidden?** `public_case()` removes the culprit, solution, and hints from the public case object. It also omits the detail of every undiscovered clue. The server reveals the detail only after a valid examination request.

**Why validate on the server?** Browser code can be changed by a user. The server is the authority for puzzle answers, scoring, and accusations.

## Testing checklist

- [ ] Start the app without a Groq key and confirm the Demo Mode banner appears.
- [ ] Start a case and examine evidence; the detail appears only after clicking Examine.
- [ ] Submit a wrong puzzle answer, then a correct answer. Confirm +20 is awarded only once.
- [ ] Use a hint and confirm the score decreases by 10.
- [ ] Ask the assistant a question and confirm it does not reveal the culprit before the case ends.
- [ ] Submit an incorrect accusation and confirm -20 and the solution reveal.
- [ ] Start another case, solve it, and confirm both results appear in Case History.
- [ ] Configure a valid Groq key and test AI case generation and chat.
- [ ] Resize the browser to phone width and verify the layout stacks cleanly.

## Notes
This is a local educational project. Before public deployment, use a strong secret key, disable Flask debug mode, add CSRF protection and rate limiting, move sessions server-side, and store game history in a database. Groq model availability can change; set `GROQ_MODEL` to a model currently enabled in your Groq console.
