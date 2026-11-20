"""Flask entry point and JSON API routes for AI Mystery Quest."""
import os
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

from ai_service import ask_assistant, generate_case, get_hint
from game_logic import (choose_demo_case, load_demo_cases, progress, public_case,
                        read_history, save_result)

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "local-development-key-change-me")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")


def ai_available():
    return bool(os.getenv("GROQ_API_KEY"))


def current_game():
    return session.get("game")


def start_game(case=None, demo=False):
    case = case or choose_demo_case()
    session["game"] = {
        "case": case, "discovered": [], "completed_puzzles": [],
        "hint_count": 0, "score": 0, "ended": False,
        "case_id": case.get("id", str(uuid.uuid4())),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "demo": demo
    }
    session.modified = True


@app.get("/")
def index():
    return render_template("index.html", demo_mode=not ai_available())


@app.get("/dashboard")
def dashboard():
    history = read_history()
    total_score = sum(item.get("score", 0) for item in history)
    return render_template("dashboard.html", history=history[:5],
                           total_score=total_score, solved=len(history),
                           demo_mode=not ai_available())


@app.post("/new-game")
def new_game():
    case = None
    demo = not ai_available()
    if ai_available():
        try:
            case = generate_case()
            if case:
                case["id"] = "ai-" + str(uuid.uuid4())[:8]
            else:
                demo = True
        except Exception as exc:
            app.logger.warning("AI case generation failed; using demo case: %s", exc)
            demo = True
    start_game(case, demo)
    return redirect(url_for("investigation"))


@app.get("/investigation")
def investigation():
    game = current_game()
    if not game:
        return redirect(url_for("dashboard"))
    safe_case = public_case(game["case"], game["discovered"])
    return render_template("investigation.html", case=safe_case, game=game,
                           progress=progress(game), demo_mode=game["demo"])


@app.post("/api/examine")
def examine():
    game = current_game()
    if not game or game["ended"]:
        return jsonify(error="Start an active case before examining clues."), 400
    data = request.get_json(silent=True) or {}
    clue_id = data.get("clue_id")
    clue = next((x for x in game["case"]["evidence"] if x["id"] == clue_id), None)
    if not clue:
        return jsonify(error="That evidence does not exist."), 404
    if clue_id not in game["discovered"]:
        game["discovered"].append(clue_id)
        session["game"] = game
    return jsonify(message="Clue examined.", clue=clue, discovered=game["discovered"],
                   progress=progress(game))


@app.post("/api/puzzle")
def puzzle():
    game = current_game()
    if not game or game["ended"]:
        return jsonify(error="No active investigation."), 400
    data = request.get_json(silent=True) or {}
    puzzle_id = data.get("puzzle_id")
    answer = (data.get("answer") or "").strip().lower()
    item = next((p for p in game["case"]["puzzles"] if p["id"] == puzzle_id), None)
    if not item or not answer:
        return jsonify(error="Choose a puzzle and enter an answer."), 400
    if puzzle_id in game["completed_puzzles"]:
        return jsonify(message="You already solved this puzzle.", correct=True,
                       score=game["score"])
    accepted = [x.lower().strip() for x in item["accepted"]]
    correct = any(answer == x or (len(x) > 3 and x in answer) for x in accepted)
    if correct:
        game["completed_puzzles"].append(puzzle_id)
        game["score"] += 20
        message = item["explanation"]
    else:
        message = "Not quite. Recheck the timeline and the information in the case."
    session["game"] = game
    return jsonify(correct=correct, message=message, score=game["score"],
                   progress=progress(game))


@app.post("/api/hint")
def hint():
    game = current_game()
    if not game or game["ended"]:
        return jsonify(error="No active investigation."), 400
    index = game["hint_count"]
    if index >= len(game["case"]["hints"]):
        return jsonify(error="You have used all available hints."), 400
    names = [x["name"] for x in game["case"]["evidence"] if x["id"] in game["discovered"]]
    text = get_hint(game["case"], index, names) if not game["demo"] else game["case"]["hints"][index]
    game["hint_count"] += 1
    game["score"] -= 10
    session["game"] = game
    return jsonify(hint=text, score=game["score"], remaining=len(game["case"]["hints"])-game["hint_count"])


@app.post("/api/chat")
def chat():
    game = current_game()
    if not game:
        return jsonify(error="Start a case before chatting."), 400
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify(error="Please enter a question."), 400
    if len(question) > 500:
        return jsonify(error="Keep questions under 500 characters."), 400
    answer = ask_assistant(game["case"], question, game["discovered"], game["ended"])
    return jsonify(answer=answer)


@app.post("/api/accuse")
def accuse():
    game = current_game()
    if not game or game["ended"]:
        return jsonify(error="No active case to accuse in."), 400
    data = request.get_json(silent=True) or {}
    suspect_id = data.get("suspect_id")
    suspect = next((s for s in game["case"]["suspects"] if s["id"] == suspect_id), None)
    if not suspect:
        return jsonify(error="Select a valid suspect."), 400
    correct = suspect_id == game["case"]["culprit_id"]
    game["score"] += 100 if correct else -20
    game["ended"] = True
    culprit = next(s for s in game["case"]["suspects"] if s["id"] == game["case"]["culprit_id"])
    result = {
        "case_title": game["case"]["title"], "suspect": suspect["name"],
        "culprit": culprit["name"], "correct": correct, "score": game["score"],
        "solved_at": datetime.now().isoformat(timespec="seconds"),
        "clues_found": len(game["discovered"]),
        "puzzles_solved": len(game["completed_puzzles"]),
        "solution": game["case"]["solution"]
    }
    try:
        save_result(result)
    except OSError:
        app.logger.exception("Could not save game history")
    session["game"] = game
    return jsonify(result=result)


@app.get("/history")
def history():
    records = read_history()
    return render_template("history.html", history=records, demo_mode=not ai_available())


@app.errorhandler(404)
def not_found(_error):
    return render_template("index.html", demo_mode=not ai_available(),
                           not_found=True), 404


if __name__ == "__main__":
    # Debug is convenient for local coursework; disable it when deploying publicly.
    app.run(host="127.0.0.1", port=5000, debug=True)
