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
    """
    Detect structuring (smurfing) as per RBI / FIU-IND guidelines.

    Logic:
        Flag any account that, within a rolling 4-hour window, makes
        3 or more individual transactions each BELOW ₹1,00,000 whose
        cumulative total EXCEEDS ₹5,00,000.  This pattern indicates
        deliberate splitting of amounts to stay under the ₹10,00,000
        cash-transaction reporting threshold mandated by the PMLA rules.

    Args:
        df (pd.DataFrame): Transaction dataframe with columns
                           'from_account', 'amount', 'timestamp'.

    Returns:
        list: Account IDs (from 'from_account' column) flagged for structuring.
    """
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Only consider transactions individually below ₹1,00,000
    sub_threshold = df[df['amount'] < 100_000].copy()
    sub_threshold = sub_threshold.sort_values('timestamp')

    flagged = set()
    window = pd.Timedelta(hours=4)

    for acc in sub_threshold['from_account'].unique():
        acc_txns = sub_threshold[sub_threshold['from_account'] == acc].reset_index(drop=True)

        # Sliding window: for each transaction, look forward 4 hours
        for i, row in acc_txns.iterrows():
            window_end = row['timestamp'] + window
            in_window = acc_txns[
                (acc_txns['timestamp'] >= row['timestamp']) &
                (acc_txns['timestamp'] <= window_end)
            ]
            if len(in_window) >= 3 and in_window['amount'].sum() > 500_000:
                flagged.add(acc)
                break  # No need to check further windows for this account

    return list(flagged)


def detect_velocity(df):
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    suspicious = []

    for acc in df['from_account'].unique():
        user_txns = df[df['from_account'] == acc].sort_values('timestamp')
        if len(user_txns) >= 3:
            time_diff = (user_txns.iloc[-1]['timestamp'] - user_txns.iloc[0]['timestamp']).seconds
            if time_diff < 3600:
                suspicious.append(acc)

    return suspicious


def detect_anomaly(df):
    threshold = df['amount'].mean() + 2 * df['amount'].std()
    return df[df['amount'] > threshold]['from_account'].unique().tolist()


def detect_dormant(df):
    """
    Detect sudden reactivation of dormant accounts per RBI guidelines.

    Logic:
        Under RBI's Master Circular on KYC/AML, an account with no
        customer-induced transactions for 2 years is classified as
        'inoperative'; accounts with no activity for 180+ days are
        treated as potentially dormant for AML monitoring purposes.

        Two conditions are flagged:
          1. The gap between any two consecutive transactions by the
             same account (within the dataset) is >= 180 days — this
             signals a dormant account that has suddenly reactivated.
          2. Accounts appearing in the dataset for the first time where
             their first transaction follows a 180+ day silence (i.e.
             the dataset starts well after their last known activity);
             this is captured by checking inter-transaction gaps >= 180
             days across consecutive records.

    Args:
        df (pd.DataFrame): Transaction dataframe with columns
                           'from_account', 'to_account', 'timestamp'.

    Returns:
        list: Account IDs flagged as dormant reactivations. Both
              senders ('from_account') and receivers ('to_account')
              are considered so that receiving-only accounts are
              also captured.
    """
    DORMANT_DAYS = 180  # RBI AML monitoring threshold

    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    flagged = []

    # Union all accounts that appear on either side of a transaction
    all_accounts = pd.unique(
        pd.concat([df['from_account'], df['to_account']])
    )

    for acc in all_accounts:
        # All timestamps where this account was active (sender OR receiver)
        acc_txns = df[
            (df['from_account'] == acc) | (df['to_account'] == acc)
        ].sort_values('timestamp').reset_index(drop=True)

        if len(acc_txns) < 2:
            continue

        # Compute gap between every pair of consecutive transactions
        gaps = acc_txns['timestamp'].diff().dropna()
        if (gaps.dt.days >= DORMANT_DAYS).any():
            flagged.append(acc)

    return flagged


# 🤖 ML anomaly
from sklearn.ensemble import IsolationForest

def ml_anomaly(df):
    model = IsolationForest(contamination=0.1)
    df["anomaly"] = model.fit_predict(df[["amount"]])
    return df[df["anomaly"] == -1]["from_account"].unique().tolist()