import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

st.title("🏦 FundTrace AI – Banking Fraud Dashboard")

uploaded_file = st.file_uploader("Upload Transactions CSV", type=["csv"])

if uploaded_file:
    files = {"file": uploaded_file.getvalue()}
    response = requests.post("http://127.0.0.1:8000/analyze", files=files)

    data = response.json()

    st.subheader("🚨 High Risk Accounts")

    for alert in data["alerts"]:
        if alert["severity"] == "HIGH":
            st.error(f"{alert['account']} | Score: {alert['risk_score']} | {alert['reasons']}")

    st.subheader("⚠️ Medium Risk Accounts")

    for alert in data["alerts"]:
        if alert["severity"] == "MEDIUM":
            st.warning(f"{alert['account']} | Score: {alert['risk_score']}")

    st.subheader("ℹ️ Low Risk Accounts")

    for alert in data["alerts"]:
        if alert["severity"] == "LOW":
            st.info(f"{alert['account']} | Score: {alert['risk_score']}")

    st.subheader("🧠 Detection Signals")
    st.write(data["signals"])