import streamlit as st
import requests
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

st.title("💸 FundTrace AI – Fraud Dashboard")

uploaded_file = st.file_uploader("Upload Transactions CSV", type=["csv"])

if uploaded_file:
    files = {"file": uploaded_file.getvalue()}
    response = requests.post("http://127.0.0.1:8000/analyze", files=files)

    data = response.json()

    st.subheader("🚨 Fraud Alerts")
    st.write(data["alerts"])

    df = pd.read_csv(uploaded_file)

    G = nx.DiGraph()
    for _, row in df.iterrows():
        G.add_edge(row['from'], row['to'])

    st.subheader("🌐 Transaction Graph")
    fig, ax = plt.subplots()
    nx.draw(G, with_labels=True, ax=ax)
    st.pyplot(fig)