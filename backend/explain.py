"""
FundTrace-AI — Explanation Generator

Generates human-readable explanations and evidence for flagged accounts.

Optimised:
  - Accepts a pre-built `name_lookup` dict ({account: name}) instead of
    re-filtering the entire DataFrame per account call
  - Expects `signals` values to be **sets** for O(1) membership lookup
  - Only includes essential evidence columns (not all 18+ fields)
"""

# Columns to include in the evidence payload — keeps it slim for the frontend
_EVIDENCE_COLUMNS = [
    "from_account", "to_account", "amount", "timestamp",
    "from_name", "to_name", "channel", "transaction_type",
]


def generate_explanation(
    account: str,
    df,
    signals: dict,
    name_lookup: dict | None = None,
) -> dict:
    """Generate human-readable explanation and evidence for a flagged account.

    Args:
        account:      Account ID to explain.
        df:           Full transaction DataFrame.
        signals:      Dict of {signal_name: set_of_flagged_accounts}.
        name_lookup:  Pre-built {account_id: display_name} dict.
                      If None, falls back to DataFrame lookup.

    Returns:
        {"summary": str, "evidence": list[dict]}
    """
    # ── Resolve display label ─────────────────────────────────────────────
    if name_lookup and account in name_lookup:
        name = name_lookup[account]
        label = f"{name} ({account})"
    elif "from_name" in df.columns:
        sender_rows = df.loc[df["from_account"] == account, "from_name"]
        name = sender_rows.iloc[0] if not sender_rows.empty else None
        label = f"{name} ({account})" if name else account
    else:
        label = account

    # ── Build explanation sentences ───────────────────────────────────────
    explanations = []

    if account in signals.get("cycle", set()):
        explanations.append(
            f"🔁 Circular transactions detected: funds leave and return to {label}, "
            f"indicating possible round-tripping."
        )

    if account in signals.get("layering", set()):
        explanations.append(
            f"🔄 Layering behavior detected: funds move across multiple accounts "
            f"to obscure origin from {label}."
        )

    if account in signals.get("structuring", set()):
        explanations.append(
            f"💰 Structuring detected: {label} made multiple sub-threshold transactions "
            f"to avoid ₹10L reporting requirement."
        )

    if account in signals.get("velocity", set()):
        explanations.append(
            f"⚡ High transaction velocity: {label} made multiple rapid transfers "
            f"in a short time window — possible automated mule behaviour."
        )

    if account in signals.get("dormant", set()):
        explanations.append(
            f"💤 Dormant account reactivation: {label} showed sudden activity "
            f"after 180+ days of inactivity (RBI dormancy threshold)."
        )

    if account in signals.get("ml_anomaly", set()):
        explanations.append(
            f"🤖 ML anomaly: {label}'s transaction behaviour deviates significantly "
            f"from normal patterns (Isolation Forest)."
        )

    # ── Evidence — slim transaction records for this account ──────────────
    sender_txns = df.loc[df["from_account"] == account].head(3)

    # Only keep columns that exist in the dataframe AND are in our slim list
    keep_cols = [c for c in _EVIDENCE_COLUMNS if c in sender_txns.columns]
    evidence_df = sender_txns[keep_cols].copy()

    # Convert timestamps to strings for JSON serialisation
    if "timestamp" in evidence_df.columns:
        evidence_df["timestamp"] = evidence_df["timestamp"].astype(str)

    evidence = evidence_df.to_dict(orient="records")

    return {
        "summary": " ".join(explanations),
        "evidence": evidence,
    }