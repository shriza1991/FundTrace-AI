import networkx as nx

def build_graph(df):
    G = nx.DiGraph()

    for _, row in df.iterrows():
        G.add_edge(
            row['from'],
            row['to'],
            amount=row['amount'],
            timestamp=row['timestamp'],
            channel=row.get('channel', 'Unknown'),
            location=row.get('location', 'Unknown')
        )

    return G