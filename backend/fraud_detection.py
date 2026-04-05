"""
FundTrace-AI — Fraud Detection Signals

All detection functions return **lists** of flagged account IDs.
The orchestrator (app.py) converts them to sets for O(1) lookups.

Optimisations applied:
  - detect_structuring: groupby + vectorised rolling window (was O(A×T²))
  - detect_velocity: groupby + vectorised time-span (was O(A×T))
  - detect_dormant: melt + groupby + diff in one pass (was O(A×T))
  - ml_anomaly: no longer mutates caller's DataFrame
  - All functions avoid redundant pd.to_datetime() if already datetime
"""

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
MAX_CYCLES = 50            # Cap to prevent downstream UI explosion
MAX_LAYERING_PATHS = 200   # Prevent O(N²) path enumeration explosion


def _ensure_datetime(df: pd.DataFrame, col: str = "timestamp") -> pd.DataFrame:
    """Return df with `col` as datetime64; avoids redundant conversion."""
    if not pd.api.types.is_datetime64_any_dtype(df[col]):
        df = df.copy()
        df[col] = pd.to_datetime(df[col])
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Cycle detection (graph-based)
# ─────────────────────────────────────────────────────────────────────────────
def detect_cycles(G):
    """Detect circular transaction flows.
    Capped at MAX_CYCLES to prevent combinatorial explosion on dense graphs."""
    found = []
    for c in nx.simple_cycles(G):
        if len(c) > 2:
            found.append(c)
            if len(found) >= MAX_CYCLES:
                break
    return found


# ─────────────────────────────────────────────────────────────────────────────
# Layering detection (graph-based)
# ─────────────────────────────────────────────────────────────────────────────
def detect_layering(G):
    """Detect layering (multi-hop fund movement to obscure origin).

    Searches from high-degree source nodes to high-degree sink nodes only,
    capped at MAX_LAYERING_PATHS to keep complexity tractable.
    """
    paths = []

    source_nodes = sorted(G.nodes, key=lambda n: G.out_degree(n), reverse=True)
    sink_nodes   = sorted(G.nodes, key=lambda n: G.in_degree(n),  reverse=True)

    max_sources = min(len(source_nodes), 20)
    max_sinks   = min(len(sink_nodes),   20)

    for s in source_nodes[:max_sources]:
        if len(paths) >= MAX_LAYERING_PATHS:
            break
        for t in sink_nodes[:max_sinks]:
            if s == t:
                continue
            if len(paths) >= MAX_LAYERING_PATHS:
                break
            for path in nx.all_simple_paths(G, s, t, cutoff=5):
                if len(path) >= 4:
                    paths.append(path)
                    if len(paths) >= MAX_LAYERING_PATHS:
                        break
    return paths


# ─────────────────────────────────────────────────────────────────────────────
# Structuring / Smurfing detection (vectorised)
# ─────────────────────────────────────────────────────────────────────────────
def detect_structuring(df):
    """Detect structuring (smurfing) as per RBI / FIU-IND guidelines.

    Flags accounts that make 3+ sub-₹1L transactions summing >₹5L
    within a rolling 4-hour window.

    Optimised: groupby + vectorised rolling (was nested iterrows loop).
    """
    df = _ensure_datetime(df)

    # Pre-filter: only sub-threshold transactions
    sub = df.loc[df["amount"] < 100_000, ["from_account", "amount", "timestamp"]].copy()
    if sub.empty:
        return []

    sub = sub.sort_values("timestamp")
    sub = sub.set_index("timestamp")

    flagged = set()

    # Group by account, then apply a 4-hour rolling window
    for acc, grp in sub.groupby("from_account"):
        if len(grp) < 3:
            continue
        # Rolling 4-hour window: count and sum
        rolling_count = grp["amount"].rolling("4h").count()
        rolling_sum   = grp["amount"].rolling("4h").sum()

        if ((rolling_count >= 3) & (rolling_sum > 500_000)).any():
            flagged.add(acc)

    return list(flagged)


# ─────────────────────────────────────────────────────────────────────────────
# Velocity detection (vectorised)
# ─────────────────────────────────────────────────────────────────────────────
def detect_velocity(df):
    """Detect high transaction velocity — 3+ transactions within 1 hour.

    Optimised: groupby + vectorised agg (was per-account filter loop).
    Does NOT mutate the input DataFrame.
    """
    df = _ensure_datetime(df)

    grouped = df.groupby("from_account").agg(
        count=("timestamp", "size"),
        t_min=("timestamp", "min"),
        t_max=("timestamp", "max"),
    )

    # Accounts with 3+ transactions whose total time span < 1 hour
    mask = (grouped["count"] >= 3) & (
        (grouped["t_max"] - grouped["t_min"]).dt.total_seconds() < 3600
    )

    return grouped.index[mask].tolist()


# ─────────────────────────────────────────────────────────────────────────────
# Statistical anomaly detection (already vectorised — no change)
# ─────────────────────────────────────────────────────────────────────────────
def detect_anomaly(df):
    """Flag accounts with transactions > mean + 2σ."""
    threshold = df["amount"].mean() + 2 * df["amount"].std()
    return df.loc[df["amount"] > threshold, "from_account"].unique().tolist()


# ─────────────────────────────────────────────────────────────────────────────
# Dormant account detection (vectorised)
# ─────────────────────────────────────────────────────────────────────────────
def detect_dormant(df):
    """Detect sudden reactivation of dormant accounts per RBI guidelines.

    Flags any account with a 180+ day gap between consecutive transactions,
    considering both sender and receiver sides.

    Optimised: melt + groupby + diff in a single vectorised pass
    (was per-account filter loop — O(A×T) → O(T log T)).
    """
    DORMANT_DAYS = 180

    df = _ensure_datetime(df)

    # Melt from/to into a single (account, timestamp) Series
    from_col = df[["from_account", "timestamp"]].rename(columns={"from_account": "account"})
    to_col   = df[["to_account",   "timestamp"]].rename(columns={"to_account":   "account"})
    melted   = pd.concat([from_col, to_col], ignore_index=True)

    # Sort once, compute gaps per account
    melted = melted.sort_values(["account", "timestamp"])
    melted["gap_days"] = melted.groupby("account")["timestamp"].diff().dt.days

    # Accounts with any gap >= 180 days (and at least 2 transactions)
    flagged = melted.loc[melted["gap_days"] >= DORMANT_DAYS, "account"].unique().tolist()

    return flagged


# ─────────────────────────────────────────────────────────────────────────────
# ML anomaly (Isolation Forest) — no longer mutates input df
# ─────────────────────────────────────────────────────────────────────────────
def ml_anomaly(df):
    """Isolation Forest anomaly detection on transaction amounts.

    Optimised: operates on a copy to avoid mutating the caller's DataFrame.
    """
    work = df[["from_account", "amount"]].copy()
    model = IsolationForest(contamination=0.1, random_state=42)
    work["anomaly"] = model.fit_predict(work[["amount"]])
    return work.loc[work["anomaly"] == -1, "from_account"].unique().tolist()