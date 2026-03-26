import networkx as nx

def detect_cycles(G):
    cycles = list(nx.simple_cycles(G))
    return [cycle for cycle in cycles if len(cycle) > 2]


def detect_layering(G):
    suspicious_paths = []

    for source in G.nodes:
        for target in G.nodes:
            if source != target:
                paths = list(nx.all_simple_paths(G, source, target, cutoff=4))
                for path in paths:
                    if len(path) >= 4:
                        suspicious_paths.append(path)

    return suspicious_paths


def detect_structuring(df):
    counts = df.groupby('from')['amount'].count()
    return counts[counts > 3].index.tolist()