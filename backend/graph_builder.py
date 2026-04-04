import networkx as nx


def build_graph(df):
    """Build a directed transaction graph from the dataframe.

    Nodes  : account IDs (from_account / to_account)
    Edges  : one per transaction, carrying amount, timestamp, channel,
             location, and — when present — from_name, to_name,
             ifsc_from, ifsc_to for richer downstream analysis.
    """
    G = nx.DiGraph()

    has_from_name  = "from_name"  in df.columns
    has_to_name    = "to_name"    in df.columns
    has_ifsc_from  = "ifsc_from"  in df.columns
    has_ifsc_to    = "ifsc_to"    in df.columns

    for _, row in df.iterrows():
        edge_attrs = {
            "amount":    row["amount"],
            "timestamp": row["timestamp"],
            "channel":   row.get("channel",   "Unknown"),
            "location":  row.get("location",  "Unknown"),
        }
        if has_from_name:
            edge_attrs["from_name"] = row["from_name"]
        if has_to_name:
            edge_attrs["to_name"] = row["to_name"]
        if has_ifsc_from:
            edge_attrs["ifsc_from"] = row["ifsc_from"]
        if has_ifsc_to:
            edge_attrs["ifsc_to"] = row["ifsc_to"]

        G.add_edge(row["from_account"], row["to_account"], **edge_attrs)

    return G