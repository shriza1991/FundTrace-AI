def generate_explanation(account, df, signals):
    """Generate human-readable explanation and evidence for a flagged account.

    If the dataframe contains a 'from_name' column (present in the enriched
    synthetic dataset), uses the real person name in alert text to make
    investigator output more readable. e.g. 'Ramesh Kumar (ACC052...)'
    """

    # Resolve display label — prefer name + account, fall back to account only
    has_name = "from_name" in df.columns
    if has_name:
        sender_rows = df[df["from_account"] == account]
        name = sender_rows["from_name"].iloc[0] if not sender_rows.empty else None
        label = f"{name} ({account})" if name else account
    else:
        label = account

    explanations = []

    # 🔁 Cycle
    if account in signals["cycle"]:
        explanations.append(
            f"🔁 Circular transactions detected: funds leave and return to {label}, "
            f"indicating possible round-tripping."
        )

    # 🔄 Layering
    if account in signals["layering"]:
        explanations.append(
            f"🔄 Layering behavior detected: funds move across multiple accounts "
            f"to obscure origin from {label}."
        )

    # 💰 Structuring
    if account in signals["structuring"]:
        explanations.append(
            f"💰 Structuring detected: {label} made multiple sub-threshold transactions "
            f"to avoid ₹10L reporting requirement."
        )

    # ⚡ Velocity
    if account in signals["velocity"]:
        explanations.append(
            f"⚡ High transaction velocity: {label} made multiple rapid transfers "
            f"in a short time window — possible automated mule behaviour."
        )

    # 💤 Dormant
    if account in signals["dormant"]:
        explanations.append(
            f"💤 Dormant account reactivation: {label} showed sudden activity "
            f"after 180+ days of inactivity (RBI dormancy threshold)."
        )

    # 🤖 ML anomaly
    if account in signals["ml_anomaly"]:
        explanations.append(
            f"🤖 ML anomaly: {label}'s transaction behaviour deviates significantly "
            f"from normal patterns (Isolation Forest)."
        )

    # 📊 Evidence — transactions where this account is the sender
    txns = df[df["from_account"] == account].head(3).copy()

    # FIX: pandas Timestamps are not JSON-serialisable; convert to ISO strings.
    if "timestamp" in txns.columns:
        txns["timestamp"] = txns["timestamp"].astype(str)

    evidence = txns.to_dict(orient="records")

    return {
        "summary": " ".join(explanations),
        "evidence": evidence,
    }