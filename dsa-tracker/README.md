# DSA Tracker

A Flask-based DSA tracker with a Netflix-inspired UI and AI-style suggestion engine.

## Features

- Track DSA problems with title, topic, difficulty, tags, code, notes, and status.
- External AI backend support for generating new DSA question ideas with OpenAI.
- AI-generated new DSA question ideas based on topic, tags, and difficulty.
- AI-style recommendations based on topic, difficulty, and shared tags.
- Netflix-like dark UI with animated cards and polished visuals.
- Mark problems as solved and browse your history.

## Setup

1. Open a terminal in `dsa-tracker`.
2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Run the app:

```bash
python app.py
```

4. Open `http://127.0.0.1:5000` in your browser.

## Usage

- Add new problems with the form.
- Open a question card to view details and see similar suggestions.
- Use the `Mark solved` button to update question status.

## Notes

This starter project uses a local SQLite database at `database.db`.
If you want a real AI backend later, replace the `ai_suggest` function with a call to an external model.
