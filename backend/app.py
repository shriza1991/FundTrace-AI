from fastapi import FastAPI, UploadFile
import pandas as pd

from backend.graph_builder import build_graph
from backend.fraud_detection import detect_cycles, detect_layering, detect_structuring
from backend.risk_scoring import calculate_risk
app = FastAPI()

@app.post("/analyze")
async def analyze(file: UploadFile):
    df = pd.read_csv(file.file)

    G = build_graph(df)

    cycles = detect_cycles(G)
    layering = detect_layering(G)
    structuring = detect_structuring(df)

    results = []

    for node in G.nodes:
        score, reasons = calculate_risk(node, cycles, layering, structuring)

        if score > 0:
            results.append({
                "account": node,
                "risk_score": score,
                "reasons": reasons
            })

    return {
        "alerts": results,
        "cycles": cycles,
        "layering": layering
    }