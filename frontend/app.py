import streamlit as st
import requests
import pandas as pd
from pyvis.network import Network
import tempfile
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(layout="wide")

st.title("🏦 FundTrace AI – Fraud Intelligence Dashboard")

uploaded_file = st.file_uploader("Upload Transactions CSV", type=["csv"])


# ---------------- PDF GENERATOR ----------------
def generate_pdf(alerts):
    file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(file.name)
    styles = getSampleStyleSheet()

    content = [Paragraph("FundTrace AI - Fraud Report", styles['Title'])]

    for alert in alerts:
        text = f"Account: {alert['account']} | Risk: {alert['risk_score']} | {alert['reasons']}"
        content.append(Paragraph(text, styles['Normal']))

    doc.build(content)
    return file.name


# ---------------- MAIN ----------------
if uploaded_file is not None:

    df = pd.read_csv(uploaded_file)

    # Send file to backend
    files = {
        "file": ("transactions.csv", uploaded_file.getvalue(), "text/csv")
    }

    response = requests.post("http://127.0.0.1:8000/analyze", files=files)

    # Handle backend error safely
    if response.status_code != 200:
        st.error(f"Backend Error: {response.text}")
        st.stop()

    data = response.json()

    # ---------------- ALERTS ----------------
    st.subheader("🚨 Fraud Alerts (Explainable)")

    for alert in data["alerts"]:
        with st.expander(f"{alert['account']} | Score: {alert['risk_score']}"):

            if alert["severity"] == "HIGH":
                st.error("HIGH RISK")
            elif alert["severity"] == "MEDIUM":
                st.warning("MEDIUM RISK")
            else:
                st.info("LOW RISK")

            st.write("### 🔍 Detected Signals")
            st.write(alert["reasons"])

            st.write("### 🧠 Explanation")
            st.success(alert["explanation"])

            st.write("### 📊 Transaction Evidence")
            st.dataframe(alert["evidence"])

    # ---------------- FRAUD PATHS ----------------
    st.subheader("🧠 Detected Fraud Paths")

    for path in data.get("fraud_paths", []):
        st.error(path)

    # ---------------- GRAPH ----------------
    st.subheader("🌐 Interactive Transaction Network")

    net = Network(height="500px", width="100%", directed=True)
    net.barnes_hut()

    high_risk = [a["account"] for a in data["alerts"] if a["severity"] == "HIGH"]
    all_nodes = set(df["from"]).union(set(df["to"]))

    for node in all_nodes:
        color = "red" if node in high_risk else "skyblue"
        net.add_node(node, label=node, color=color)

    for _, row in df.iterrows():
        net.add_edge(
            row["from"],
            row["to"],
            label=f"₹{row['amount']}",
            title=str(row.get("channel", "Unknown")),
            arrows="to"
        )

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    net.save_graph(tmp_file.name)

    with open(tmp_file.name, "r", encoding="utf-8") as f:
        html_data = f.read()

    st.components.v1.html(html_data, height=500)

    # ---------------- INVESTIGATION ----------------
    st.subheader("🔍 Investigate Account")

    selected = st.selectbox("Select Account", list(all_nodes))

    if selected:
        st.write("### Outgoing Transactions")
        st.dataframe(df[df["from"] == selected])

        st.write("### Incoming Transactions")
        st.dataframe(df[df["to"] == selected])

    # ---------------- CHARTS ----------------
    st.subheader("📊 Insights Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        st.write("### Transaction Volume")
        st.bar_chart(df["from"].value_counts())

    with col2:
        st.write("### Amount Trend")
        st.line_chart(df["amount"])

    # ---------------- MAP ----------------
    if "lat" in df.columns and "lon" in df.columns:
        st.subheader("🗺️ Transaction Geography")
        st.map(df[["lat", "lon"]].dropna())

    # ---------------- PDF ----------------
    st.subheader("📄 Export Report")

    pdf_path = generate_pdf(data["alerts"])

    with open(pdf_path, "rb") as f:
        st.download_button(
            label="Download Fraud Report",
            data=f,
            file_name="fraud_report.pdf"
        )