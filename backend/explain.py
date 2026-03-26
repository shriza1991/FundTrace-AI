def generate_explanation(account, df, signals):

    explanations = []

    # 🔁 Cycle
    if account in signals["cycle"]:
        explanations.append(
            f"🔁 Circular transactions detected: funds leave and return to {account}, indicating possible round-tripping."
        )

    # 🔄 Layering
    if account in signals["layering"]:
        explanations.append(
            f"🔄 Layering behavior detected: funds move across multiple accounts to obscure origin."
        )

    # 💰 Structuring
    if account in signals["structuring"]:
        explanations.append(
            f"💰 Structuring detected: multiple small transactions used to avoid detection thresholds."
        )

    # ⚡ Velocity
    if account in signals["velocity"]:
        explanations.append(
            f"⚡ High transaction velocity: multiple transfers in a short time window."
        )

    # 💤 Dormant
    if account in signals["dormant"]:
        explanations.append(
            f"💤 Dormant account activation: sudden activity after inactivity."
        )

    # 🤖 ML anomaly
    if account in signals["ml_anomaly"]:
        explanations.append(
            f"🤖 ML anomaly detected: transaction behavior deviates from normal patterns."
        )

    # 📊 Evidence
    txns = df[df["from"] == account]

    evidence = txns.head(3).to_dict(orient="records")

    return {
        "summary": " ".join(explanations),
        "evidence": evidence
    }