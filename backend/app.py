from fastapi import FastAPI, UploadFile
import pandas as pd

from backend.graph_builder import build_graph
from backend.fraud_detection import *
from backend.risk_scoring import calculate_risk
from backend.explain import generate_explanation

app = FastAPI()


def get_fraud_paths(cycles):
    paths = []
    for cycle in cycles:
        path = " → ".join(cycle + [cycle[0]])
        paths.append(path)
    return paths


@app.post("/analyze")
async def analyze(file: UploadFile):

    df = pd.read_csv(file.file)

    G = build_graph(df)

    cycles = detect_cycles(G)

    signals = {
        "cycle": [n for c in cycles for n in c],
        "layering": [n for p in detect_layering(G) for n in p],
        "structuring": detect_structuring(df),
        "velocity": detect_velocity(df),
        "anomaly": detect_anomaly(df),
        "dormant": detect_dormant(df),
        "ml_anomaly": ml_anomaly(df)
    }

    results = []

    # ✅ THIS LOOP MUST BE INSIDE FUNCTION
    for node in G.nodes:

        score, severity, reasons = calculate_risk(node, signals)

        explanation = generate_explanation(node, df, signals)

        if score > 0:
            results.append({
                "account": node,
                "risk_score": score,
                "severity": severity,
                "reasons": reasons,
                "explanation": explanation["summary"],
                "evidence": explanation["evidence"]
            })

    fraud_paths = get_fraud_paths(cycles)

    return {
        "alerts": sorted(results, key=lambda x: x['risk_score'], reverse=True),
        "signals": signals,
        "fraud_paths": fraud_paths
    }