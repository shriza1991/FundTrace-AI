import networkx as nx


def build_graph(df):
    """Build a directed transaction graph from the dataframe.

    Nodes  : account IDs (from_account / to_account)
    Edges  : one per transaction, carrying amount, timestamp, channel,
             location, and — when present — from_name, to_name,
             ifsc_from, ifsc_to for richer downstream analysis.

    Optimised: Uses nx.from_pandas_edgelist() for bulk edge creation
    instead of row-by-row iterrows() (10–100× faster at scale).
    """
    # ── Prepare edge attribute columns ────────────────────────────────────
    # Always-present attributes
    edge_attrs = ["amount", "timestamp"]

    # Optional columns — only include if they exist in the dataframe
    optional = ["channel", "location", "from_name", "to_name",
                "ifsc_from", "ifsc_to"]
    edge_attrs.extend(col for col in optional if col in df.columns)

    # Fill missing optional columns with defaults so the graph is uniform
    df_graph = df[["from_account", "to_account"] + edge_attrs].copy()
    if "channel" in df_graph.columns:
        df_graph["channel"] = df_graph["channel"].fillna("Unknown")
    if "location" in df_graph.columns:
        df_graph["location"] = df_graph["location"].fillna("Unknown")

    # ── Bulk graph creation (C-speed) ─────────────────────────────────────
    G = nx.from_pandas_edgelist(
        df_graph,
        source="from_account",
        target="to_account",
        edge_attr=edge_attrs,
        create_using=nx.DiGraph,
    )

    return G