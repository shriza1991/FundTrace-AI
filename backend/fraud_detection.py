import networkx as nx
import pandas as pd

def detect_cycles(G):
    return [c for c in nx.simple_cycles(G) if len(c) > 2]


def detect_layering(G):
    paths = []
    for s in G.nodes:
        for t in G.nodes:
            if s != t:
                for path in nx.all_simple_paths(G, s, t, cutoff=5):
                    if len(path) >= 4:
                        paths.append(path)
    return paths


def detect_structuring(df):
    counts = df.groupby('from')['amount'].count()
    return counts[counts > 3].index.tolist()


def detect_velocity(df):
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    suspicious = []

    for acc in df['from'].unique():
        user_txns = df[df['from'] == acc].sort_values('timestamp')
        if len(user_txns) >= 3:
            time_diff = (user_txns.iloc[-1]['timestamp'] - user_txns.iloc[0]['timestamp']).seconds
            if time_diff < 3600:
                suspicious.append(acc)

    return suspicious


def detect_anomaly(df):
    threshold = df['amount'].mean() + 2 * df['amount'].std()
    return df[df['amount'] > threshold]['from'].unique().tolist()


def detect_dormant(df):
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    suspicious = []

    for acc in df['from'].unique():
        user_txns = df[df['from'] == acc].sort_values('timestamp')
        if len(user_txns) > 1:
            gap = (user_txns.iloc[-1]['timestamp'] - user_txns.iloc[0]['timestamp']).days
            if gap > 7:
                suspicious.append(acc)

    return suspicious


# 🤖 ML anomaly
from sklearn.ensemble import IsolationForest

def ml_anomaly(df):
    model = IsolationForest(contamination=0.1)
    df["anomaly"] = model.fit_predict(df[["amount"]])
    return df[df["anomaly"] == -1]["from"].unique().tolist()