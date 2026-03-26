def calculate_risk(account, cycles, layering, structuring):
    score = 0
    reasons = []

    for cycle in cycles:
        if account in cycle:
            score += 50
            reasons.append("Circular Transaction")

    for path in layering:
        if account in path:
            score += 30
            reasons.append("Layering")

    if account in structuring:
        score += 20
        reasons.append("Structuring")

    return score, list(set(reasons))