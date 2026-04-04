# FundTrace-AI — Changelog

All changes made to the FundTrace-AI AML fraud detection system, in chronological order.

---

## Phase 1: Backend Stabilization

### 1.1 Gemini API Fix
- **Problem:** `gemini-2.0-flash` returning `429 quota exceeded` (free tier limit = 0)
- **Fix:** Switched to `gemini-1.5-flash` (stable free-tier model)
- **File:** `backend/app.py`

### 1.2 OpenAI Fallback
- **Added:** OpenAI `gpt-3.5-turbo` as fallback when Gemini fails
- **Logic:** Gemini first → OpenAI if Gemini fails
- **File:** `backend/app.py`

### 1.3 Retry Logic
- **Added:** Exponential backoff retries (2s → 4s → 8s) for Gemini calls
- **Added:** 30-second timeout per AI call using `asyncio.wait_for`
- **File:** `backend/app.py`

### 1.4 Async AI Calls
- **Changed:** All AI calls run via `asyncio.run_in_executor` so they don't block the FastAPI event loop
- **File:** `backend/app.py`

### 1.5 STR Caching
- **Added:** SHA-256 in-memory cache (`_str_cache`) for `/generate-str`
- **Benefit:** Identical payloads skip the AI call entirely — saves cost and time
- **File:** `backend/app.py`

### 1.6 Token Optimization
- **Added:** `_slim_transactions()` helper — strips non-essential fields before sending to AI
- **Reduced:** Transaction limits (STR: 20, Ask: 10) and compact JSON (`separators=(',',':')`)
- **File:** `backend/app.py`

### 1.7 Structured Logging
- **Added:** `logging.getLogger("fundetrace")` with timestamped format
- **Replaced:** All `print()` statements with proper `logger.info/warning/error`
- **File:** `backend/app.py`

---

## Phase 2: Frontend Fixes

### 2.1 Deprecated Streamlit Parameters
- **Removed:** All `use_container_width=True` (deprecated in newer Streamlit)
- **File:** `frontend/app.py`

### 2.2 WebSocket Error Handling
- **Added:** `try/except` wrappers around all `st.*` calls in `_run_with_progress()`
- **Prevents:** `WebSocketClosedError` crashes when session disconnects mid-analysis
- **File:** `frontend/app.py`

### 2.3 AI Panels
- **Added:** STR Generator panel — calls `/generate-str` with spinner and error handling
- **Added:** Ask AI panel — calls `/ask` with question input and cached results
- **File:** `frontend/app.py`

---

## Phase 3: Developer Experience

### 3.1 `.gitignore`
- **Created:** Root `.gitignore` excluding `.env`, `venv/`, `__pycache__/`, `.vscode/`, build artifacts
- **File:** `.gitignore`

### 3.2 VS Code Settings
- **Created:** `.vscode/settings.json` with `python.terminal.useEnvFile: true`
- **Effect:** Terminals auto-load `.env` variables
- **File:** `.vscode/settings.json`

### 3.3 README
- **Created:** `README.md` with Quick Start commands, project structure, and troubleshooting
- **File:** `README.md`

### 3.4 Dependencies
- **Added to `requirements.txt`:**
  - `google-genai` (new Gemini SDK)
  - `python-dotenv`
  - `openai` (used for both NVIDIA NIM client and OpenAI fallback)
- **File:** `requirements.txt`

---

## Phase 4: NVIDIA Primary + Gemini Fallback

### 4.1 NVIDIA NIM Integration
- **Added:** NVIDIA API as **primary** AI provider using the OpenAI-compatible SDK
- **Client:** `OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=NVIDIA_KEY)`
- **Models:**
  - `/generate-str` → `meta/llama-3.1-70b-instruct` (long-form STR reports)
  - `/ask` → `meta/llama-3.1-8b-instruct` (fast Q&A)
- **File:** `backend/app.py`

### 4.2 Gemini SDK Migration
- **Problem:** `google.generativeai` package deprecated; `gemini-1.5-flash` removed from API
- **Fix:** Migrated to new `google-genai` SDK (`from google import genai`)
- **Model:** Changed to `gemini-2.0-flash` (currently available)
- **File:** `backend/app.py`

### 4.3 Model Name Fixes
- **Problem:** `mistralai/mixtral-8x7b-instruct` returns 404 on NVIDIA NIM
- **Fix:** Changed `/ask` model to `meta/llama-3.1-8b-instruct` (confirmed working)
- **File:** `backend/app.py`

### 4.4 Fallback Architecture
```
Request → NVIDIA NIM (single attempt, 45s timeout)
            │ fail
            ▼
         Gemini 2.0 Flash (2 retries, exponential backoff)
            │ fail
            ▼
         HTTP 500 → frontend shows error / loads fallback JSON
```
- **File:** `backend/app.py`

### 4.5 Health Endpoint Updated
- **Changed:** `/health` now reports `nvidia` and `gemini` readiness (was `gemini` + `openai`)
- **Frontend:** Sidebar health check updated to show `NVIDIA: ready | Gemini: ready`
- **Files:** `backend/app.py`, `frontend/app.py`

---

## Phase 5: Evidence Integrity

### 5.1 SHA-256 Evidence Hashing (Backend)
- **Added:** `generate_evidence_hash()` function
- **Hashes:** Complete evidence package (all alerts + all transactions) with `sort_keys=True`
- **Response:** `/analyze` now returns `evidence_hash` and `hash_generated_at`
- **File:** `backend/app.py`

### 5.2 Evidence Integrity Certificate (Frontend)
- **Added:** `🔐 Evidence Integrity Certificate` section between Fraud Paths and Network Graph
- **Shows:** SHA-256 hash in monospace `st.code()`, sealed timestamp, ✅ Verified badge
- **Expandable:** Legal basis (Indian Evidence Act §65B, IT Act 2000)
- **File:** `frontend/app.py`

---

## Phase 6: Fallback System

### 6.1 Fallback Generator Script
- **Created:** `scripts/generate_fallbacks.py`
- **Behavior:**
  1. Checks if backend is running (auto-starts if not)
  2. For each scenario (roundtrip, structuring, dormant):
     - Calls `/analyze` → saves `fallback_<scenario>_analysis.json`
     - Calls `/generate-str` → saves `fallback_<scenario>_str.json`
     - Calls `/ask` × 3 questions → saves `fallback_<scenario>_qa.json`
  3. If AI fails, saves stub responses (`"STR unavailable"`, `"Answer unavailable"`)
  4. Prints summary of which scenarios succeeded
- **Output:** 9 JSON files in `data/`

### 6.2 Frontend Fallback Loading
- **Added:** `load_fallback(scenario, type)` helper
- **Added:** `_scenario_key_from_label()` to map filenames to scenario keys
- **Wrapped:** All 3 API calls (`/analyze`, `/generate-str`, `/ask`) with fallback:
  - Analysis: loads `fallback_<scenario>_analysis.json` if backend fails
  - STR: loads `fallback_<scenario>_str.json` if AI fails
  - Ask: loads `fallback_<scenario>_qa.json` and fuzzy-matches the question
- **Added:** Yellow warning banner when using fallback data
- **File:** `frontend/app.py`

---

## Files Modified

| File | Changes |
|------|---------|
| `backend/app.py` | NVIDIA primary, Gemini fallback, evidence hashing, async AI, caching, logging |
| `frontend/app.py` | Fallback loading, evidence certificate, health display, WebSocket guards, AI panels |
| `requirements.txt` | Added `google-genai`, `python-dotenv`, `openai` |
| `.env` | Added `NVIDIA_API_KEY` alongside existing `GEMINI_API_KEY` |
| `.gitignore` | Created (excludes secrets, venv, caches) |
| `.vscode/settings.json` | Created (auto-loads .env in terminals) |
| `README.md` | Created (quick start + troubleshooting) |
| `scripts/generate_fallbacks.py` | Created (pre-generates fallback JSON) |

---

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start backend (from project root)
uvicorn backend.app:app --reload

# 3. Start frontend (separate terminal)
streamlit run frontend/app.py

# 4. (Optional) Pre-generate fallback data
python scripts/generate_fallbacks.py
```
