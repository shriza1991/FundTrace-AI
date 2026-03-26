from fastapi import FastAPI, UploadFile
import pandas as pd

from backend.graph_builder import build_graph
from backend.fraud_detection import *
from backend.risk_scoring import calculate_risk

app = FastAPI()

@app.post("/analyze")
async def analyze(file: UploadFile):
    df = pd.read_csv(file.file)

    G = build_graph(df)

    signals = {
        "cycle": [node for cycle in detect_cycles(G) for node in cycle],
        "layering": [node for path in detect_layering(G) for node in path],
        "structuring": detect_structuring(df),
        "velocity": detect_velocity(df),
        "anomaly": detect_anomaly(df),
        "dormant": detect_dormant(df)
    }

    results = []

    for node in G.nodes:
        score, severity, reasons = calculate_risk(node, signals)

        if score > 0:
            results.append({
                "account": node,
                "risk_score": score,
                "severity": severity,
                "reasons": reasons
            })

    return {
        "alerts": sorted(results, key=lambda x: x['risk_score'], reverse=True),
        "signals": signals
    }