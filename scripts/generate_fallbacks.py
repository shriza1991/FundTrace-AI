"""
FundTrace-AI — Fallback Data Generator
=======================================
Pre-generates all backend responses as JSON files so the Streamlit
frontend can load them if the backend or AI APIs are unavailable
during a live demo.

Usage:
    python scripts/generate_fallbacks.py

Prerequisites:
    - Backend running at http://127.0.0.1:8000 (auto-started if not)
    - Scenario CSVs present in data/
    - AI APIs configured in .env (NVIDIA_API_KEY, GEMINI_API_KEY)
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL    = "http://127.0.0.1:8000"
DATA_DIR    = Path("data")
TIMEOUT_STR = 60   # STR generation can be slow
TIMEOUT_QA  = 30   # Q&A is fast
TIMEOUT_ANA = 120  # Analysis can be heavy on large CSVs

SCENARIOS = {
    "roundtrip": {
        "csv": DATA_DIR / "scenario_roundtrip.csv",
        "name": "Round-Trip Fraud / Circular Layering",
        "questions": [
            "Which accounts form the circular flow and how long did it take?",
            "What is the total amount laundered across all hops?",
            "Which account initiated the round-trip?",
        ],
    },
    "structuring": {
        "csv": DATA_DIR / "scenario_structuring.csv",
        "name": "Structuring / Smurfing Pattern",
        "questions": [
            "How many transactions were made below the ₹1 lakh threshold?",
            "What is the cumulative total of the structured transactions?",
            "Which account initiated the structuring?",
        ],
    },
    "dormant": {
        "csv": DATA_DIR / "scenario_dormant.csv",
        "name": "Dormant Account Reactivation",
        "questions": [
            "How long was the account dormant before reactivation?",
            "What happened to the funds immediately after reactivation?",
            "Which accounts received the dispersed funds?",
        ],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _log(msg: str, level: str = "INFO") -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    prefix = {"INFO": "✅", "WARN": "⚠️", "ERR": "❌", "WAIT": "⏳"}.get(level, "ℹ️")
    print(f"  [{ts}] {prefix}  {msg}")


def _save_json(path: Path, data: dict | list) -> None:
    """Write data to a JSON file with pretty formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    _log(f"Saved → {path}  ({path.stat().st_size:,} bytes)")


def _check_health() -> bool:
    """Return True if backend responds 200 on /health."""
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def _ensure_backend() -> None:
    """
    Check if the backend is running. If not, start it as a background
    process and wait up to 20 seconds for it to become healthy.
    """
    if _check_health():
        _log("Backend already running")
        return

    _log("Backend not running — starting uvicorn…", "WAIT")
    # Start uvicorn in background (detached, no console window)
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(Path(__file__).resolve().parent.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for i in range(20):
        time.sleep(1)
        if _check_health():
            _log(f"Backend started (PID {proc.pid}) after {i + 1}s")
            return

    _log("Could not start backend after 20s — aborting", "ERR")
    proc.terminate()
    sys.exit(1)


# ---------------------------------------------------------------------------
# Step 1: Call /analyze and save fallback
# ---------------------------------------------------------------------------
def generate_analysis(scenario_key: str, csv_path: Path) -> dict | None:
    """POST the scenario CSV to /analyze and return the JSON response."""
    if not csv_path.exists():
        _log(f"CSV not found: {csv_path}", "ERR")
        return None

    _log(f"Analyzing {csv_path.name}…", "WAIT")
    try:
        with open(csv_path, "rb") as f:
            resp = requests.post(
                f"{BASE_URL}/analyze",
                files={"file": (csv_path.name, f, "text/csv")},
                timeout=TIMEOUT_ANA,
            )
        resp.raise_for_status()
        data = resp.json()
        out_path = DATA_DIR / f"fallback_{scenario_key}_analysis.json"
        _save_json(out_path, data)
        alert_count = len(data.get("alerts", []))
        _log(f"Analysis complete — {alert_count} alerts")
        return data
    except requests.exceptions.Timeout:
        _log("Analysis timed out", "ERR")
    except requests.exceptions.HTTPError as exc:
        try:
            detail = exc.response.json().get("detail", str(exc))
        except Exception:
            detail = str(exc)
        _log(f"Analysis failed: {detail}", "ERR")
    except Exception as exc:
        _log(f"Analysis error: {exc}", "ERR")
    return None


# ---------------------------------------------------------------------------
# Step 2: Call /generate-str and save fallback
# ---------------------------------------------------------------------------
def generate_str(scenario_key: str, scenario_name: str, analysis: dict, csv_path: Path) -> bool:
    """POST to /generate-str and save the result."""
    # Read raw transactions from CSV (not from analysis, which lacks some fields)
    try:
        import pandas as pd
        df = pd.read_csv(csv_path)
        transactions = json.loads(df.to_json(orient="records", default_handler=str))
    except Exception:
        transactions = []

    alerts = analysis.get("alerts", [])
    if not alerts:
        _log("No alerts to generate STR from", "WARN")

    payload = {
        "alerts": alerts[:20],
        "transactions": transactions[:50],
        "scenario_name": scenario_name,
    }

    _log(f"Generating STR for '{scenario_name}'…", "WAIT")
    out_path = DATA_DIR / f"fallback_{scenario_key}_str.json"

    try:
        resp = requests.post(
            f"{BASE_URL}/generate-str",
            json=payload,
            timeout=TIMEOUT_STR,
        )
        resp.raise_for_status()
        data = resp.json()
        _save_json(out_path, data)
        model = data.get("model_used", "unknown")
        _log(f"STR generated via {model}")
        return True

    except requests.exceptions.Timeout:
        _log("STR generation timed out — saving fallback stub", "WARN")
    except requests.exceptions.HTTPError as exc:
        try:
            detail = exc.response.json().get("detail", str(exc))
        except Exception:
            detail = str(exc)
        _log(f"STR generation failed: {detail}", "WARN")
    except Exception as exc:
        _log(f"STR error: {exc}", "WARN")

    # Save a stub so the frontend still has something to display
    stub = {
        "str_content": "STR unavailable — AI service was not reachable during pre-generation.",
        "case_id": f"STR-{datetime.utcnow().strftime('%Y-%m-%d')}-0000",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "model_used": "fallback-stub",
    }
    _save_json(out_path, stub)
    return False


# ---------------------------------------------------------------------------
# Step 3: Call /ask for each question and save fallback
# ---------------------------------------------------------------------------
def generate_qa(scenario_key: str, questions: list[str], analysis: dict, csv_path: Path) -> bool:
    """POST each question to /ask and save all Q&A pairs."""
    try:
        import pandas as pd
        df = pd.read_csv(csv_path)
        transactions = json.loads(df.to_json(orient="records", default_handler=str))
    except Exception:
        transactions = []

    qa_results = []
    all_ok = True

    for i, question in enumerate(questions, 1):
        _log(f"Asking Q{i}/{len(questions)}: {question[:60]}…", "WAIT")

        payload = {
            "question": question,
            "transactions": transactions[:30],
        }

        try:
            resp = requests.post(
                f"{BASE_URL}/ask",
                json=payload,
                timeout=TIMEOUT_QA,
            )
            resp.raise_for_status()
            data = resp.json()
            qa_results.append(data)
            _log(f"Q{i} answered via {data.get('model_used', 'unknown')}")

        except Exception as exc:
            _log(f"Q{i} failed: {exc}", "WARN")
            all_ok = False
            qa_results.append({
                "question": question,
                "answer": "Answer unavailable — AI service was not reachable during pre-generation.",
                "model_used": "fallback-stub",
            })

    out_path = DATA_DIR / f"fallback_{scenario_key}_qa.json"
    _save_json(out_path, qa_results)
    return all_ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print()
    print("=" * 65)
    print("  FundTrace-AI — Fallback Data Generator")
    print("=" * 65)
    print()

    # Ensure we're running from the project root
    if not DATA_DIR.exists():
        _log(f"Data directory not found: {DATA_DIR.resolve()}", "ERR")
        _log("Run this script from the project root: python scripts/generate_fallbacks.py")
        sys.exit(1)

    # 1. Ensure backend is up
    _ensure_backend()
    print()

    # 2. Process each scenario
    results: dict[str, dict] = {}

    for key, cfg in SCENARIOS.items():
        print(f"─── Scenario: {key.upper()} ─{'─' * (45 - len(key))}")

        csv_path = cfg["csv"]
        if not csv_path.exists():
            _log(f"Scenario CSV missing: {csv_path} — skipping", "ERR")
            results[key] = {"analysis": False, "str": False, "qa": False}
            print()
            continue

        # A. Analysis
        analysis = generate_analysis(key, csv_path)
        analysis_ok = analysis is not None
        if not analysis:
            analysis = {"alerts": [], "signals": {}, "fraud_paths": []}

        # B. STR
        str_ok = generate_str(key, cfg["name"], analysis, csv_path)

        # C. Q&A
        qa_ok = generate_qa(key, cfg["questions"], analysis, csv_path)

        results[key] = {"analysis": analysis_ok, "str": str_ok, "qa": qa_ok}
        print()

    # 3. Summary
    print("=" * 65)
    print("  SUMMARY")
    print("=" * 65)

    generated_files = sorted(DATA_DIR.glob("fallback_*.json"))

    for key, status in results.items():
        emoji = "✅" if all(status.values()) else ("⚠️" if any(status.values()) else "❌")
        parts = []
        for part, ok in status.items():
            parts.append(f"{part}: {'✅' if ok else '❌'}")
        print(f"  {emoji}  {key:<15}  {' | '.join(parts)}")

    print()
    print(f"  Generated {len(generated_files)} fallback files:")
    for f in generated_files:
        size_kb = f.stat().st_size / 1024
        print(f"    📄 {f}  ({size_kb:.1f} KB)")

    print()
    print("  Done! Frontend can now load fallback data if AI APIs are unavailable.")
    print("=" * 65)
    print()


if __name__ == "__main__":
    main()
