"""
FundTrace-AI — FastAPI Backend
AML Fraud Detection + AI Report Generation for Union Bank of India

AI Architecture (v4):
  PRIMARY:  NVIDIA NIM API  (free tier, OpenAI-compatible)
            /generate-str → meta/llama-3.1-70b-instruct
            /ask          → meta/llama-3.1-8b-instruct
  FALLBACK: Gemini 2.0 Flash (Google AI Studio free tier, new google-genai SDK)
  /analyze  — graph-based fraud detection (unchanged)
  /health   — liveness probe
"""

# ---------------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------------
import asyncio
import hashlib
import json
import logging
import os
import random
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# ---------------------------------------------------------------------------
# Third-party
# ---------------------------------------------------------------------------
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google import genai

# ---------------------------------------------------------------------------
# Logging — structured, timestamped
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("fundetrace")

# ---------------------------------------------------------------------------
# Environment & AI client setup
# ---------------------------------------------------------------------------
load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
NVIDIA_KEY  = os.getenv("NVIDIA_API_KEY", "")

# ---------------------------------------------------------------------------
# NVIDIA NIM client — OpenAI-compatible SDK, free-tier generous quota
# Models used:
#   STR generation → meta/llama-3.1-70b-instruct   (long-form, structured)
#   Q&A            → meta/llama-3.1-8b-instruct    (fast, concise)
# ---------------------------------------------------------------------------
nvidia_client = None
if NVIDIA_KEY:
    try:
        from openai import OpenAI as _OpenAI
        nvidia_client = _OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=NVIDIA_KEY,
        )
        logger.info("NVIDIA NIM client initialised (primary AI)")
    except ImportError:
        logger.warning("openai package not installed — NVIDIA client disabled")
else:
    logger.warning("NVIDIA_API_KEY not set — NVIDIA primary disabled")

# ---------------------------------------------------------------------------
# Gemini fallback — new google-genai SDK with gemini-2.0-flash
# ---------------------------------------------------------------------------
GEMINI_MODEL = "gemini-2.0-flash"
gemini_client = None
if GEMINI_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_KEY)
        logger.info(f"Gemini fallback initialised ({GEMINI_MODEL}, new google-genai SDK)")
    except Exception as exc:
        logger.warning(f"Gemini init failed: {exc}")
else:
    logger.warning("GEMINI_API_KEY not set — Gemini fallback disabled")

# ---------------------------------------------------------------------------
# Internal imports
# ---------------------------------------------------------------------------
from backend.explain import generate_explanation
from backend.fraud_detection import (
    detect_cycles, detect_layering, detect_structuring,
    detect_velocity, detect_anomaly, detect_dormant, ml_anomaly,
)
from backend.graph_builder import build_graph
from backend.risk_scoring import calculate_risk

# Shared thread pool for CPU-bound detection functions
_detection_pool = ThreadPoolExecutor(max_workers=4)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="FundTrace-AI", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory STR cache  {sha256(payload) → response_dict}
# Prevents duplicate Gemini calls for the same data in a demo session
# ---------------------------------------------------------------------------
_str_cache: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
REQUIRED_COLUMNS    = {"from_account", "to_account", "amount", "timestamp"}
AI_TIMEOUT_SECS     = 45           # NVIDIA NIM can be slightly slower on cold start
MAX_STR_TXN         = 20           # transactions sent to /generate-str
MAX_ASK_TXN         = 10           # transactions sent to /ask (keep prompt small)
NVIDIA_STR_MODEL    = "meta/llama-3.1-70b-instruct"
NVIDIA_ASK_MODEL    = "meta/llama-3.1-8b-instruct"


# ===========================================================================
# Helper utilities
# ===========================================================================

def get_fraud_paths(cycles: list) -> list[str]:
    return [" → ".join(c + [c[0]]) for c in cycles]


def _validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Validate columns, types, and non-emptiness. Raises HTTPException on failure."""
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise HTTPException(400, detail=f"Missing required columns: {sorted(missing)}")
    if df.empty:
        raise HTTPException(400, detail="Uploaded file contains no data rows.")
    try:
        df["amount"] = df["amount"].astype(float)
    except (ValueError, TypeError) as exc:
        raise HTTPException(400, detail=f"'amount' must be numeric: {exc}")
    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    except Exception as exc:
        raise HTTPException(400, detail=f"'timestamp' must be parseable dates: {exc}")
    return df


def _slim_transactions(transactions: list, limit: int) -> list:
    """
    Return at most `limit` transactions, keeping only the essential fields
    to minimise token usage sent to the AI.
    """
    keep = {"from_account", "to_account", "amount", "timestamp",
            "from_name", "to_name", "transaction_type", "channel"}
    slimmed = []
    for t in transactions[:limit]:
        slimmed.append({k: v for k, v in t.items() if k in keep})
    return slimmed


def _cache_key(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# AI call helpers
# ---------------------------------------------------------------------------

async def _call_nvidia(prompt: str, model: str, max_tokens: int) -> str:
    """
    Call NVIDIA NIM API using the openai-compatible client.
    Single attempt with timeout — caller handles retry/fallback.
    Raises RuntimeError on any failure.
    """
    if not nvidia_client:
        raise RuntimeError("NVIDIA client not configured")

    logger.info(f"NVIDIA call → model={model} max_tokens={max_tokens}")
    loop = asyncio.get_event_loop()
    try:
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: nvidia_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=0.3,
                    stream=False,
                ),
            ),
            timeout=AI_TIMEOUT_SECS,
        )
        text = response.choices[0].message.content.strip()
        if not text:
            raise RuntimeError("NVIDIA returned an empty response")
        logger.info(f"NVIDIA call succeeded ({model})")
        return text
    except asyncio.TimeoutError:
        raise RuntimeError(f"NVIDIA request timed out ({model})")
    except Exception as exc:
        raise RuntimeError(f"NVIDIA error ({model}): {exc}")


async def _call_gemini(prompt: str, max_tokens: int, retries: int = 2) -> str:
    """
    Call Gemini 2.0 Flash via the new google-genai SDK.
    Exponential backoff retry (fallback only).
    Raises RuntimeError after all retries exhausted.
    """
    if not gemini_client:
        raise RuntimeError("Gemini not configured")

    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Gemini fallback attempt {attempt}/{retries} (max_tokens={max_tokens})")
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: gemini_client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=prompt,
                        config=genai.types.GenerateContentConfig(
                            max_output_tokens=max_tokens,
                            temperature=0.3,
                        ),
                    ),
                ),
                timeout=AI_TIMEOUT_SECS,
            )
            text = response.text.strip()
            if not text:
                raise RuntimeError("Gemini returned an empty response")
            logger.info(f"Gemini fallback succeeded (attempt {attempt})")
            return text

        except asyncio.TimeoutError as exc:
            last_err = exc
            logger.warning(f"Gemini timeout on attempt {attempt}")
        except Exception as exc:
            last_err = exc
            logger.warning(f"Gemini error on attempt {attempt}: {exc}")

        if attempt < retries:
            wait = 2 ** attempt   # 2s, 4s
            logger.info(f"Retrying Gemini in {wait}s…")
            await asyncio.sleep(wait)

    raise RuntimeError(f"Gemini failed after {retries} attempts: {last_err}")


async def _generate_with_fallback(
    prompt: str,
    max_tokens: int,
    nvidia_model: str = NVIDIA_STR_MODEL,
) -> tuple[str, str]:
    """
    PRIMARY  → NVIDIA NIM (Llama 3.1)
    FALLBACK → Gemini 2.0 Flash
    Returns (response_text, model_label).
    Raises HTTPException(500) if both fail.
    """
    # --- Try NVIDIA first ---
    try:
        text = await _call_nvidia(prompt, nvidia_model, max_tokens)
        return text, nvidia_model
    except RuntimeError as nvidia_err:
        logger.error(f"NVIDIA failed: {nvidia_err} — falling back to Gemini…")

    # --- Gemini fallback ---
    try:
        text = await _call_gemini(prompt, max_tokens)
        return text, f"{GEMINI_MODEL} (fallback)"
    except RuntimeError as gemini_err:
        logger.error(f"Gemini fallback also failed: {gemini_err}")
        raise HTTPException(
            status_code=500,
            detail="AI service temporarily unavailable. Please try again.",
        )


# ===========================================================================
# Request models
# ===========================================================================

class STRRequest(BaseModel):
    alerts: list
    transactions: list
    scenario_name: str


class AskRequest(BaseModel):
    question: str
    transactions: list


# ===========================================================================
# Endpoints
# ===========================================================================

# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    """Liveness probe — shows AI provider readiness."""
    return {
        "status":  "ok",
        "version": "3.0",
        "nvidia":  "ready" if nvidia_client else "disabled",
        "gemini":  "ready" if gemini_client else "disabled",
    }


# ---------------------------------------------------------------------------
# POST /analyze  (unchanged logic, same interface)
# ---------------------------------------------------------------------------
def generate_evidence_hash(alerts: list, transactions_dict: list) -> str:
    """
    Generates a deterministic SHA-256 hash of the complete evidence
    package. sort_keys=True ensures same input always produces same hash.
    If any alert or transaction is modified after this hash is generated,
    the hash will change — proving tampering occurred.
    """
    payload = {
        "alerts": alerts,
        "transactions": transactions_dict,
        "schema_version": "1.0",
    }
    data = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(data.encode()).hexdigest()


@app.post("/analyze")
async def analyze(file: UploadFile):
    """Upload a transaction CSV and receive fraud-risk analysis.

    Optimised pipeline:
      1. Graph-based signals (cycles, layering) run sequentially (need G)
      2. DataFrame-based signals run concurrently via thread pool
      3. All signals stored as sets for O(1) lookups
      4. Name lookup dict built once, shared across all explanations
    """
    try:
        df = pd.read_csv(file.file)
    except Exception as exc:
        raise HTTPException(400, detail=f"Could not parse CSV: {exc}")

    df = _validate_dataframe(df)

    try:
        # ── Phase 1: Build graph + graph-based signals ────────────────────
        loop = asyncio.get_event_loop()
        G = await loop.run_in_executor(_detection_pool, build_graph, df)
        cycles = await loop.run_in_executor(_detection_pool, detect_cycles, G)

        # ── Phase 2: Run independent detectors concurrently ───────────────
        layering_fut    = loop.run_in_executor(_detection_pool, detect_layering, G)
        structuring_fut = loop.run_in_executor(_detection_pool, detect_structuring, df)
        velocity_fut    = loop.run_in_executor(_detection_pool, detect_velocity, df)
        anomaly_fut     = loop.run_in_executor(_detection_pool, detect_anomaly, df)
        dormant_fut     = loop.run_in_executor(_detection_pool, detect_dormant, df)
        ml_anomaly_fut  = loop.run_in_executor(_detection_pool, ml_anomaly, df)

        (
            layering_paths, structuring_accs, velocity_accs,
            anomaly_accs, dormant_accs, ml_anomaly_accs,
        ) = await asyncio.gather(
            layering_fut, structuring_fut, velocity_fut,
            anomaly_fut, dormant_fut, ml_anomaly_fut,
        )

        # ── Phase 3: Build signals as SETS for O(1) lookup ────────────────
        signals = {
            "cycle":       set(n for c in cycles for n in c),
            "layering":    set(n for p in layering_paths for n in p),
            "structuring": set(structuring_accs),
            "velocity":    set(velocity_accs),
            "anomaly":     set(anomaly_accs),
            "dormant":     set(dormant_accs),
            "ml_anomaly":  set(ml_anomaly_accs),
        }

        # ── Phase 4: Pre-build name lookup (once, not per-account) ────────
        name_lookup = {}
        if "from_name" in df.columns:
            name_pairs = df[["from_account", "from_name"]].drop_duplicates("from_account")
            name_lookup = dict(zip(name_pairs["from_account"], name_pairs["from_name"]))

        # ── Phase 5: Score + explain each node ────────────────────────────
        results = []
        for node in G.nodes:
            score, severity, reasons = calculate_risk(node, signals)
            if score > 0:
                explanation = generate_explanation(
                    node, df, signals, name_lookup=name_lookup
                )
                results.append({
                    "account":     node,
                    "risk_score":  score,
                    "severity":    severity,
                    "reasons":     reasons,
                    "explanation": explanation["summary"],
                    "evidence":    explanation["evidence"],
                })

        fraud_paths = get_fraud_paths(cycles)

        # Sort alerts by risk score before hashing (deterministic order)
        sorted_alerts = sorted(results, key=lambda x: x["risk_score"], reverse=True)

        # Cryptographic seal over the complete evidence package
        evidence_hash   = generate_evidence_hash(sorted_alerts, df.to_dict("records"))
        hash_generated  = datetime.utcnow().isoformat() + "Z"

        # Convert sets → lists for JSON serialisation in the response
        signals_serialisable = {k: sorted(v) for k, v in signals.items()}

        logger.info(
            f"Analysis complete — {len(results)} alerts, {len(cycles)} cycles, "
            f"evidence hash: {evidence_hash[:16]}…"
        )

        return {
            "alerts":            sorted_alerts,
            "signals":           signals_serialisable,
            "fraud_paths":       fraud_paths,
            "evidence_hash":     evidence_hash,
            "hash_generated_at": hash_generated,
        }

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(500, detail=f"Analysis failed: {type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# POST /generate-str
# ---------------------------------------------------------------------------
@app.post("/generate-str")
async def generate_str(body: STRRequest):
    """
    Generate a PMLA-compliant Suspicious Transaction Report.
    PRIMARY:  NVIDIA Llama-3.1-70b-instruct
    FALLBACK: Gemini 2.0 Flash
    Results are cached per unique payload hash.
    """
    case_id      = f"STR-{datetime.utcnow().strftime('%Y-%m-%d')}-{random.randint(1000, 9999)}"
    generated_at = datetime.utcnow().isoformat() + "Z"

    # Check cache first (avoids re-calling AI for identical data)
    cache_payload = {
        "alerts": body.alerts,
        "transactions": body.transactions[:MAX_STR_TXN],
        "scenario": body.scenario_name,
    }
    ck = _cache_key(cache_payload)
    if ck in _str_cache:
        logger.info(f"STR cache hit for key {ck[:8]}…")
        cached = _str_cache[ck]
        # Refresh case_id and timestamp on cache hits to keep output unique
        cached.update({"case_id": case_id, "generated_at": generated_at})
        return cached

    # Slim down transactions to reduce token usage
    slim_txn = _slim_transactions(body.transactions, MAX_STR_TXN)

    # Compact but complete prompt
    prompt = f"""You are a senior AML compliance officer at Union Bank of India.
Generate a Suspicious Transaction Report (STR) per PMLA 2002 and RBI AML guidelines.

SCENARIO: {body.scenario_name}
CASE REFERENCE: {case_id}
FLAGGED ALERTS (summary):
{json.dumps(body.alerts[:10], separators=(',', ':'))}

KEY TRANSACTIONS ({len(slim_txn)} records):
{json.dumps(slim_txn, separators=(',', ':'))}

Write the STR with EXACTLY these sections (plain text, no markdown):
1. CASE REFERENCE
2. REPORTING ENTITY: Union Bank of India, AML Compliance Division
3. SUBJECT ACCOUNTS: IDs, names, suspicious totals
4. FRAUD PATTERN IDENTIFIED
5. TRANSACTION TIMELINE: chronological bullet points
6. REGULATORY BASIS: PMLA 2002 sections + RBI AML Master Circular clauses
7. RECOMMENDED ACTION: Account Freeze / FIU-IND goAML / Refer to ED / Enhanced Monitoring
8. RISK RATING: HIGH/MEDIUM/LOW + one-line justification
9. INVESTIGATING OFFICER: [To be assigned]
10. REPORT GENERATED: {generated_at}"""

    # Use Llama 3.1 70B for STR (best structured long-form output)
    str_text, model_used = await _generate_with_fallback(
        prompt, max_tokens=1200, nvidia_model=NVIDIA_STR_MODEL
    )

    result = {
        "str_content":  str_text,
        "case_id":      case_id,
        "generated_at": generated_at,
        "model_used":   model_used,
    }

    # Cache result so re-runs on same data skip API calls
    _str_cache[ck] = result
    logger.info(f"STR generated via {model_used} — cached key {ck[:8]}…")
    return result


# ---------------------------------------------------------------------------
# POST /ask
# ---------------------------------------------------------------------------
@app.post("/ask")
async def ask(body: AskRequest):
    """
    Answer a natural-language question about transaction data.
    PRIMARY:  NVIDIA Llama-3.1-8b-instruct (fast, concise)
    FALLBACK: Gemini 2.0 Flash
    """
    slim_txn = _slim_transactions(body.transactions, MAX_ASK_TXN)

    prompt = f"""You are an AML investigator assistant for Union Bank of India.
Answer in 2-4 plain English sentences. Use account IDs and holder names when available.
Express amounts as \u20b9X lakh or \u20b9X crore. Never speculate beyond the data.

TRANSACTION DATA ({len(slim_txn)} records):
{json.dumps(slim_txn, separators=(',', ':'))}

QUESTION: {body.question}

Answer:"""

    # Use Llama 3.1 8B for Q&A — fastest model for short factual responses
    answer, model_used = await _generate_with_fallback(
        prompt, max_tokens=300, nvidia_model=NVIDIA_ASK_MODEL
    )
    logger.info(f"Ask answered via {model_used}")
    return {"answer": answer, "question": body.question, "model_used": model_used}