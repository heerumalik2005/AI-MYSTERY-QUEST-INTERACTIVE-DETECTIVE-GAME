"""Groq integration. All API calls stay on the server; keys never reach the browser."""
import json
import os
from groq import Groq

MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def _client():
    """Return a Groq client, or None when Demo Mode should be used."""
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return None
    return Groq(api_key=key, timeout=25.0, max_retries=1)


def _chat(system_prompt, user_prompt, temperature=0.4):
    client = _client()
    if client is None:
        return None
    response = client.chat.completions.create(
        model=MODEL,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


def validate_case(case):
    """Basic schema and logic checks before an AI case enters the game."""
    required = ["title", "description", "location", "difficulty",
                "suspects", "evidence", "puzzles", "hints",
                "culprit_id", "solution"]
    if not isinstance(case, dict) or any(k not in case for k in required):
        raise ValueError("Generated case is missing required fields.")
    if not 3 <= len(case["suspects"]) <= 4:
        raise ValueError("A case must contain three or four suspects.")
    suspect_ids = {s.get("id") for s in case["suspects"]}
    if case["culprit_id"] not in suspect_ids:
        raise ValueError("The culprit must match one suspect.")
    if len(case["evidence"]) < 3 or not case["puzzles"] or len(case["hints"]) < 2:
        raise ValueError("The case needs evidence, a puzzle, and progressive hints.")
    for suspect in case["suspects"]:
        for key in ("id", "name", "background", "motive", "alibi", "statement"):
            if not suspect.get(key):
                raise ValueError("A suspect is missing " + key)
    for item in case["evidence"]:
        for key in ("id", "name", "description", "detail", "unlock"):
            if not item.get(key):
                raise ValueError("Evidence is missing " + key)
    return case


def generate_case():
    """Ask Groq for a structured mystery. Raises errors so caller can fall back."""
    prompt = """
Create one fair-play fictional detective mystery as JSON only.
Schema:
{
"title":"...", "description":"...", "location":"...", "difficulty":"Easy|Medium|Hard",
"suspects":[{"id":"short_unique_id","name":"...","background":"...","motive":"...","alibi":"...","statement":"..."}],
"evidence":[{"id":"short_unique_id","name":"...","description":"safe public description","detail":"deeper clue revealed on examination","unlock":"start|puzzle|suspect"}],
"puzzles":[{"id":"...","question":"...","accepted":["answer variants"],"explanation":"..."}],
"hints":["subtle hint","stronger hint","very strong hint"],
"culprit_id":"one suspect id",
"solution":"clear explanation connecting at least two clues"
}
Use exactly 3 suspects, at least 3 evidence items, one solvable puzzle, and one uniquely provable culprit.
Ensure the evidence and alibis logically establish exactly one culprit. Keep the solution out of suspect-facing text.
"""
    raw = _chat("You are a careful mystery-game writer. Return valid JSON only.", prompt, 0.8)
    if raw is None:
        return None
    return validate_case(json.loads(raw))


def get_hint(case, hint_index, discovered_names):
    """Generate a non-spoiling hint; deterministic case hints remain fallback."""
    fallback = case["hints"][min(hint_index, len(case["hints"]) - 1)]
    try:
        raw = _chat(
            "You are a detective coach. Return JSON with one string field named hint. "
            "Never name or reveal the culprit. Use only the supplied case facts.",
            json.dumps({"case": {k: case[k] for k in ("description", "suspects", "evidence")},
                        "hint_level": hint_index + 1, "already_discovered": discovered_names,
                        "fallback_direction": fallback}),
            0.3,
        )
        if raw:
            hint = json.loads(raw).get("hint")
            if isinstance(hint, str) and hint.strip():
                return hint.strip()
    except Exception:
        pass
    return fallback


def ask_assistant(case, question, discovered_ids, ended=False):
    """Answer using only public information and discovered clue details."""
    suspects = [{k: s[k] for k in ("name", "background", "motive", "alibi", "statement")}
                for s in case["suspects"]]
    evidence = []
    for item in case["evidence"]:
        if item["id"] in discovered_ids:
            evidence.append({"name": item["name"], "description": item["description"],
                             "detail": item["detail"]})
        else:
            evidence.append({"name": "Undiscovered evidence", "description": "A clue remains to be examined."})
    context = {"description": case["description"], "location": case["location"],
               "suspects": suspects, "evidence": evidence}
    if ended:
        context["solution"] = case["solution"]
    system = ("You are the AI Detective Assistant in a mystery game. Be helpful and concise. "
              "Use only supplied facts. Do not invent evidence. Do not reveal or guess the culprit "
              "or solution unless the case has ended. Encourage logical comparison of timelines, "
              "motives, and discovered clues. Return JSON with an 'answer' string.")
    try:
        raw = _chat(system, json.dumps({"case": context, "question": question, "case_ended": ended}), 0.35)
        if raw:
            answer = json.loads(raw).get("answer")
            if isinstance(answer, str) and answer.strip():
                return answer.strip()
    except Exception:
        pass
    # Useful offline assistant fallback.
    if not ended:
        return ("Let's reason from what you have uncovered. Compare each suspect's alibi "
                "with the evidence you have examined, then look for a contradiction. "
                "I can discuss discovered clues, but I won't identify the culprit before the case ends.")
    return case["solution"]
