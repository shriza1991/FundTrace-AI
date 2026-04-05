"""
FundTrace-AI — Risk Scoring Engine

Calculates composite risk score for each account based on detected signals.

Optimised:
  - Weights dict moved to module level (avoids re-creation per call)
  - Expects signal values to be **sets** for O(1) membership lookup
    (caller in app.py converts lists → sets before calling)
"""

# Module-level constant — created once, not per-call
SIGNAL_WEIGHTS = {
    "cycle":       50,
    "layering":    30,
    "structuring": 20,
    "velocity":    25,
    "anomaly":     35,
    "dormant":     20,
    "ml_anomaly":  40,
}


def calculate_risk(account: str, signals: dict) -> tuple:
    """Score an account against all detected fraud signals.

    Args:
        account:  Account ID to evaluate.
        signals:  Dict of {signal_name: set_of_flagged_accounts}.
                  Values MUST be sets for O(1) lookup.

    Returns:
        (score, severity, reasons) tuple.
    """
    score = 0
    reasons = []

    for signal, accounts in signals.items():
        if account in accounts:          # O(1) with sets
            score += SIGNAL_WEIGHTS.get(signal, 0)
            reasons.append(signal)

    if score >= 70:
        severity = "HIGH"
    elif score >= 40:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    return score, severity, reasons