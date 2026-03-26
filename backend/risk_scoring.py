def calculate_risk(account, signals):
    score = 0
    reasons = []

    weights = {
        "cycle": 50,
        "layering": 30,
        "structuring": 20,
        "velocity": 25,
        "anomaly": 35,
        "dormant": 20
    }

    for signal, accounts in signals.items():
        if account in accounts:
            score += weights[signal]
            reasons.append(signal)

    # severity levels
    if score >= 70:
        severity = "HIGH"
    elif score >= 40:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    return score, severity, reasons