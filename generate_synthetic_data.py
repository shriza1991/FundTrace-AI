"""
FundTrace-AI — Authentic Synthetic Banking Data Generator
Generates realistic Indian banking transaction data covering:
- All 5 fraud patterns from PS3
- Normal transactions for contrast
- Real Indian names, IFSC codes, account formats, cities
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

# ── Seed for reproducibility ──────────────────────────────────────────────────
random.seed(42)
np.random.seed(42)

# ── Real Indian Data ───────────────────────────────────────────────────────────

INDIAN_NAMES = [
    "Ramesh Kumar", "Priya Sharma", "Vikram Patel", "Sunita Mehta",
    "Arjun Singh", "Kavya Reddy", "Harish Joshi", "Meena Iyer",
    "Ravi Nair", "Deepa Pillai", "Suresh Gupta", "Anita Desai",
    "Manoj Tiwari", "Pooja Agarwal", "Rajesh Yadav", "Sneha Kulkarni",
    "Amit Verma", "Rekha Pandey", "Nitin Sinha", "Geeta Mishra",
    "Arun Bose", "Lalita Chatterjee", "Dinesh Shah", "Hema Malhotra",
    "Prakash Rao", "Usha Naik", "Sanjay Dubey", "Ananya Roy",
    "Mohan Lal", "Farida Sheikh", "Kishore Patil", "Sudha Menon",
    "Vinod Kapoor", "Asha Bhosle", "Ganesh Murthy", "Radha Krishnan",
]

# Real Indian city coordinates
CITIES = {
    "Mumbai":     (19.0760, 72.8777),
    "Delhi":      (28.7041, 77.1025),
    "Bengaluru":  (12.9716, 77.5946),
    "Hyderabad":  (17.3850, 78.4867),
    "Chennai":    (13.0827, 80.2707),
    "Pune":       (18.5204, 73.8567),
    "Kolkata":    (22.5726, 88.3639),
    "Ahmedabad":  (23.0225, 72.5714),
    "Jaipur":     (26.9124, 75.7873),
    "Surat":      (21.1702, 72.8311),
    "Lucknow":    (26.8467, 80.9462),
    "Nagpur":     (21.1458, 79.0882),
    "Indore":     (22.7196, 75.8577),
    "Bhopal":     (23.2599, 77.4126),
    "Patna":      (25.5941, 85.1376),
    "Vadodara":   (22.3072, 73.1812),
    "Coimbatore": (11.0168, 76.9558),
    "Kochi":      (9.9312,  76.2673),
    "Chandigarh": (30.7333, 76.7794),
    "Guwahati":   (26.1445, 91.7362),
}

# Real Union Bank IFSC codes (format: UBIN0XXXXXX)
IFSC_CODES = {
    "Mumbai":     "UBIN0531898",
    "Delhi":      "UBIN0532053",
    "Bengaluru":  "UBIN0532134",
    "Hyderabad":  "UBIN0531979",
    "Chennai":    "UBIN0531685",
    "Pune":       "UBIN0532097",
    "Kolkata":    "UBIN0531790",
    "Ahmedabad":  "UBIN0532215",
    "Jaipur":     "UBIN0532178",
    "Surat":      "UBIN0532241",
    "Lucknow":    "UBIN0532302",
    "Nagpur":     "UBIN0531912",
    "Indore":     "UBIN0532389",
    "Bhopal":     "UBIN0532412",
    "Patna":      "UBIN0531856",
    "Vadodara":   "UBIN0532256",
    "Coimbatore": "UBIN0531734",
    "Kochi":      "UBIN0531801",
    "Chandigarh": "UBIN0532467",
    "Guwahati":   "UBIN0532523",
}

CHANNELS = ["UPI", "NEFT", "RTGS", "IMPS", "NACH", "CHEQUE"]

CHANNEL_WEIGHTS = {
    "UPI":    0.45,   # dominant in India
    "NEFT":   0.25,
    "IMPS":   0.15,
    "RTGS":   0.08,   # only for large amounts (>₹2L)
    "NACH":   0.04,
    "CHEQUE": 0.03,
}

OCCUPATIONS = [
    "Salaried - IT",
    "Salaried - Government",
    "Salaried - Private",
    "Self Employed - Trader",
    "Self Employed - Doctor",
    "Self Employed - Lawyer",
    "Retired",
    "Student",
    "Agriculturist",
    "Business Owner",
]

# Realistic monthly income ranges by occupation (INR)
INCOME_RANGES = {
    "Salaried - IT":            (45000,  200000),
    "Salaried - Government":    (25000,   80000),
    "Salaried - Private":       (20000,   80000),
    "Self Employed - Trader":   (30000,  150000),
    "Self Employed - Doctor":   (80000,  400000),
    "Self Employed - Lawyer":   (50000,  300000),
    "Retired":                  (15000,   50000),
    "Student":                  (5000,    15000),
    "Agriculturist":            (10000,   40000),
    "Business Owner":           (50000,  500000),
}

# ── Account Generation ─────────────────────────────────────────────────────────

def generate_account_id(index):
    """Generate realistic Indian bank account number (14 digits)"""
    prefix = "052"  # Union Bank account prefix
    return f"ACC{prefix}{str(index).zfill(11)}"

def build_customer_profiles(n=40):
    """Build realistic customer KYC profiles"""
    profiles = {}
    names_used = random.sample(INDIAN_NAMES, min(n, len(INDIAN_NAMES)))
    # If n > available names, cycle through
    while len(names_used) < n:
        names_used.append(random.choice(INDIAN_NAMES) + f" {random.randint(2,9)}")

    for i in range(n):
        acc_id = generate_account_id(i + 1)
        city = random.choice(list(CITIES.keys()))
        occ = random.choice(OCCUPATIONS)
        income_min, income_max = INCOME_RANGES[occ]
        monthly_income = random.randint(income_min, income_max)
        lat, lon = CITIES[city]

        profiles[acc_id] = {
            "name":           names_used[i],
            "occupation":     occ,
            "monthly_income": monthly_income,
            "city":           city,
            "lat":            lat + random.uniform(-0.05, 0.05),
            "lon":            lon + random.uniform(-0.05, 0.05),
            "ifsc":           IFSC_CODES[city],
            "account_opened": datetime(2018, 1, 1) + timedelta(days=random.randint(0, 1800)),
            "kyc_status":     random.choices(["Complete", "Pending"], weights=[0.9, 0.1])[0],
        }
    return profiles

# ── Channel selector ──────────────────────────────────────────────────────────

def pick_channel(amount):
    if amount >= 200000:
        return random.choices(["RTGS", "NEFT"], weights=[0.6, 0.4])[0]
    elif amount >= 100000:
        return random.choices(["NEFT", "RTGS", "IMPS"], weights=[0.5, 0.2, 0.3])[0]
    elif amount >= 10000:
        return random.choices(["NEFT", "IMPS", "UPI"], weights=[0.3, 0.3, 0.4])[0]
    else:
        return random.choices(["UPI", "IMPS"], weights=[0.75, 0.25])[0]

# ── Transaction builder ───────────────────────────────────────────────────────

txn_counter = [1]

def make_txn(from_acc, to_acc, amount, ts, profiles, channel=None, note=""):
    p_from = profiles.get(from_acc, {})
    p_to   = profiles.get(to_acc, {})
    city   = p_from.get("city", "Mumbai")
    lat    = p_from.get("lat", 19.076)
    lon    = p_from.get("lon", 72.877)

    ch = channel or pick_channel(amount)

    txn = {
        "transaction_id":   f"T{txn_counter[0]:04d}",
        "from_account":     from_acc,
        "from_name":        p_from.get("name", "Unknown"),
        "from_occupation":  p_from.get("occupation", "Unknown"),
        "from_income":      p_from.get("monthly_income", 0),
        "to_account":       to_acc,
        "to_name":          p_to.get("name", "Unknown"),
        "amount":           round(amount, 2),
        "timestamp":        ts.strftime("%Y-%m-%d %H:%M:%S"),
        "channel":          ch,
        "ifsc_from":        p_from.get("ifsc", "UBIN0531898"),
        "ifsc_to":          p_to.get("ifsc", "UBIN0531898"),
        "location":         city,
        "lat":              round(lat, 4),
        "lon":              round(lon, 4),
        "transaction_type": "CR" if amount > 0 else "DR",
        "note":             note,
    }
    txn_counter[0] += 1
    return txn

# ═══════════════════════════════════════════════════════════════════════════════
# FRAUD SCENARIO GENERATORS
# ═══════════════════════════════════════════════════════════════════════════════

def generate_round_trip(profiles, accs, base_ts):
    """
    Fraud Pattern 1: Round-tripping / Circular transactions
    Money leaves ACC-A, hops through 4-6 accounts, returns to ACC-A
    Small deductions at each hop simulate 'fees' to appear legitimate
    """
    txns = []
    chain = accs[:6]
    amount = random.uniform(180000, 250000)
    ts = base_ts

    for i in range(len(chain)):
        frm = chain[i]
        to  = chain[(i + 1) % len(chain)]
        amount *= random.uniform(0.97, 0.99)   # slight reduction each hop
        ts += timedelta(minutes=random.randint(6, 15))
        txns.append(make_txn(frm, to, amount, ts, profiles,
                             note="round_trip_fraud"))
    return txns


def generate_structuring(profiles, initiator, targets, base_ts):
    """
    Fraud Pattern 2: Structuring / Smurfing
    Multiple transactions just below ₹10L reporting threshold
    All within a short window to stay under radar
    """
    txns = []
    ts = base_ts
    # 9 transactions between ₹85,000–₹99,000 (all below ₹1L threshold)
    for target in targets:
        amount = random.uniform(85000, 99500)
        ts += timedelta(minutes=random.randint(8, 22))
        txns.append(make_txn(initiator, target, amount, ts, profiles,
                             channel="NEFT", note="structuring_fraud"))
    return txns


def generate_layering(profiles, accs, base_ts):
    """
    Fraud Pattern 3: Layering — multi-hop chain to obscure origin
    Long chain (6-8 hops) through accounts in different cities
    Each hop uses a different channel to complicate tracing
    """
    txns = []
    channels = ["NEFT", "IMPS", "UPI", "RTGS", "NEFT", "IMPS", "UPI", "NEFT"]
    amount = random.uniform(300000, 500000)
    ts = base_ts

    for i in range(len(accs) - 1):
        amount *= random.uniform(0.94, 0.98)
        ts += timedelta(hours=random.randint(2, 8))
        txns.append(make_txn(accs[i], accs[i+1], amount, ts, profiles,
                             channel=channels[i % len(channels)],
                             note="layering_fraud"))
    return txns


def generate_dormant_activation(profiles, dormant_acc, receiver_accs, base_ts):
    """
    Fraud Pattern 4: Dormant account suddenly activated
    Account silent for 270+ days then suddenly receives large sum
    Immediately disperses funds to multiple accounts
    """
    txns = []

    # Large inflow into dormant account
    feeder = random.choice([a for a in profiles if a != dormant_acc])
    inflow_amount = random.uniform(380000, 520000)
    activation_ts = base_ts
    txns.append(make_txn(feeder, dormant_acc, inflow_amount, activation_ts,
                         profiles, channel="NEFT", note="dormant_activation_fraud"))

    # Rapid dispersal within 12 minutes
    ts = activation_ts
    share = inflow_amount / len(receiver_accs)
    for acc in receiver_accs:
        ts += timedelta(minutes=random.randint(2, 5))
        txns.append(make_txn(dormant_acc, acc, share * random.uniform(0.9, 1.0),
                             ts, profiles, channel="IMPS",
                             note="dormant_dispersal_fraud"))
    return txns


def generate_velocity_fraud(profiles, source_acc, targets, base_ts):
    """
    Fraud Pattern 5: High-velocity transactions
    Many transactions in very short time window — automated mule behavior
    """
    txns = []
    ts = base_ts
    for target in targets:
        amount = random.uniform(4000, 12000)
        ts += timedelta(minutes=random.randint(1, 4))
        txns.append(make_txn(source_acc, target, amount, ts, profiles,
                             channel="UPI", note="velocity_fraud"))
    return txns


def generate_profile_mismatch(profiles, acc, targets, base_ts):
    """
    Fraud Pattern 6: Profile mismatch
    Agriculturist / student account transacting crores — inconsistent with KYC
    """
    txns = []
    ts = base_ts
    # Large inflow completely inconsistent with declared income
    feeder = random.choice([a for a in profiles if a != acc])
    txns.append(make_txn(feeder, acc, random.uniform(800000, 1200000),
                         ts, profiles, channel="RTGS",
                         note="profile_mismatch_inflow"))
    ts += timedelta(hours=1)
    for target in targets:
        amount = random.uniform(200000, 350000)
        ts += timedelta(minutes=random.randint(15, 40))
        txns.append(make_txn(acc, target, amount, ts, profiles,
                             channel="NEFT", note="profile_mismatch_outflow"))
    return txns


def generate_shell_network(profiles, shell_accs, real_acc, base_ts):
    """
    Fraud Pattern 7: Shell account network
    Multiple recently-opened accounts with no real activity
    funnel money toward one consolidation account
    """
    txns = []
    ts = base_ts
    for shell in shell_accs:
        # Each shell receives from 'outside' (unknown source)
        amount = random.uniform(90000, 150000)
        txns.append(make_txn(shell, real_acc, amount, ts, profiles,
                             channel=random.choice(["NEFT", "IMPS"]),
                             note="shell_network_fraud"))
        ts += timedelta(minutes=random.randint(10, 25))
    return txns


# ═══════════════════════════════════════════════════════════════════════════════
# NORMAL TRANSACTION GENERATORS
# ═══════════════════════════════════════════════════════════════════════════════

def generate_salary_credits(profiles, employer_acc, employee_accs, base_ts):
    """Monthly salary credits — most common normal transaction"""
    txns = []
    for acc in employee_accs:
        income = profiles[acc]["monthly_income"]
        # Salary on 1st or 5th of month
        ts = base_ts.replace(day=random.choice([1, 5]),
                             hour=random.randint(8, 10),
                             minute=random.randint(0, 59))
        txns.append(make_txn(employer_acc, acc, income, ts, profiles,
                             channel="NACH", note="salary_credit"))
    return txns


def generate_utility_payments(profiles, acc, base_ts):
    """Electricity, water, phone bills — small regular payments"""
    txns = []
    utilities = [
        ("UTIL_BESCOM", random.uniform(800,  3500),  "electricity_bill"),
        ("UTIL_BSNL",   random.uniform(300,  1200),  "phone_bill"),
        ("UTIL_LPG",    random.uniform(800,  1100),  "lpg_refill"),
        ("UTIL_OTT",    random.uniform(149,   649),  "ott_subscription"),
    ]
    ts = base_ts
    for util_acc, amount, note in utilities:
        # Add utility as a pseudo-account if not in profiles
        ts += timedelta(days=random.randint(1, 5))
        txn = make_txn(acc, util_acc, amount, ts, profiles,
                       channel="UPI", note=note)
        txn["to_name"] = util_acc.replace("UTIL_", "").title() + " Bill"
        txns.append(txn)
    return txns


def generate_emi_payments(profiles, acc, base_ts):
    """Home loan / car loan EMIs via NACH"""
    txns = []
    emi_types = [
        ("LOAN_HDFC_HL",  random.uniform(18000, 55000), "home_loan_emi"),
        ("LOAN_BAJAJ_PL", random.uniform(5000,  15000), "personal_loan_emi"),
    ]
    ts = base_ts.replace(day=5, hour=9, minute=0)
    for loan_acc, amount, note in random.sample(emi_types, 1):
        txn = make_txn(acc, loan_acc, amount, ts, profiles,
                       channel="NACH", note=note)
        txn["to_name"] = "Loan EMI Auto-Debit"
        txns.append(txn)
    return txns


def generate_merchant_payments(profiles, acc, base_ts):
    """UPI payments to shops, restaurants, petrol, groceries"""
    txns = []
    merchants = [
        ("MER_DMART",    random.uniform(1500, 8000),  "grocery_shopping"),
        ("MER_PETROL",   random.uniform(1000, 4000),  "fuel"),
        ("MER_AMAZON",   random.uniform(500,  12000), "online_shopping"),
        ("MER_ZOMATO",   random.uniform(200,  800),   "food_delivery"),
        ("MER_SWIGGY",   random.uniform(150,  600),   "food_delivery"),
        ("MER_FLIPKART", random.uniform(300,  5000),  "online_shopping"),
        ("MER_MEDPLUS",  random.uniform(200,  3000),  "pharmacy"),
        ("MER_IRCTC",    random.uniform(400,  3500),  "train_ticket"),
    ]
    ts = base_ts
    sample_size = random.randint(1, 2)
    for mer_acc, amount, note in random.sample(merchants, sample_size):
        ts += timedelta(days=random.randint(1, 4), hours=random.randint(0, 12))
        txn = make_txn(acc, mer_acc, amount, ts, profiles,
                       channel="UPI", note=note)
        txn["to_name"] = mer_acc.replace("MER_", "").title()
        txns.append(txn)
    return txns


def generate_p2p_transfers(profiles, accs, base_ts):
    """Normal person-to-person transfers — splitting bills, rent, etc."""
    txns = []
    ts = base_ts
    for _ in range(random.randint(2, 4)):
        frm, to = random.sample(accs, 2)
        amount = random.uniform(200, 8000)
        ts += timedelta(days=random.randint(1, 6), hours=random.randint(8, 22))
        txns.append(make_txn(frm, to, amount, ts, profiles,
                             channel="UPI", note="p2p_transfer_normal"))
    return txns


def generate_fd_rd_transactions(profiles, acc, base_ts):
    """Fixed Deposit / Recurring Deposit — bank to self"""
    txns = []
    fd_acc = f"FD_{acc[-6:]}"
    amount = profiles[acc]["monthly_income"] * random.uniform(1, 3)
    ts = base_ts.replace(day=1, hour=10)
    txn = make_txn(acc, fd_acc, amount, ts, profiles,
                   channel="NEFT", note="fd_rd_investment")
    txn["to_name"] = "Fixed Deposit Account"
    txns.append(txn)
    return txns


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def generate_all_data():
    print("Building customer profiles...")
    profiles = build_customer_profiles(40)
    accs = list(profiles.keys())

    all_txns = []
    base = datetime(2025, 9, 1, 9, 0, 0)   # start 6 months back

    # ── Mark dormant account (no transactions for 270+ days) ─────────────────
    dormant_acc = accs[10]
    dormant_accounts = {dormant_acc}

    # ── FRAUD SCENARIOS ───────────────────────────────────────────────────────

    print("Generating fraud scenarios...")

    # 1. Round-trip — 3 independent cycles
    for offset_days in [0, 45, 90]:
        chain = random.sample([a for a in accs if a not in dormant_accounts], 6)
        ts = base + timedelta(days=offset_days, hours=random.randint(9, 14))
        all_txns += generate_round_trip(profiles, chain, ts)

    # 2. Structuring — 2 separate structuring events
    for offset_days in [10, 75]:
        initiator = random.choice([a for a in accs[:15] if a not in dormant_accounts])
        targets = random.sample([a for a in accs if a != initiator], 9)
        ts = base + timedelta(days=offset_days, hours=10)
        all_txns += generate_structuring(profiles, initiator, targets, ts)

    # 3. Layering — 2 chains
    for offset_days in [20, 110]:
        chain = random.sample([a for a in accs if a not in dormant_accounts], 8)
        ts = base + timedelta(days=offset_days, hours=8)
        all_txns += generate_layering(profiles, chain, ts)

    # 4. Dormant account activation — 2 events
    receivers = random.sample([a for a in accs if a not in dormant_accounts], 3)
    ts = base + timedelta(days=270, hours=11)   # 270 days after dormancy
    all_txns += generate_dormant_activation(profiles, dormant_acc, receivers, ts)

    dormant_acc2 = accs[18]
    dormant_accounts.add(dormant_acc2)
    receivers2 = random.sample([a for a in accs if a not in dormant_accounts], 4)
    ts2 = base + timedelta(days=300, hours=14)
    all_txns += generate_dormant_activation(profiles, dormant_acc2, receivers2, ts2)

    # 5. Velocity fraud — 3 events
    for offset_days in [5, 60, 130]:
        source = random.choice([a for a in accs if a not in dormant_accounts])
        targets = random.sample([a for a in accs if a != source], 8)
        ts = base + timedelta(days=offset_days, hours=random.randint(22, 23))
        all_txns += generate_velocity_fraud(profiles, source, targets, ts)

    # 6. Profile mismatch — pick low-income accounts
    low_income = sorted(
        [a for a in accs if a not in dormant_accounts],
        key=lambda a: profiles[a]["monthly_income"]
    )[:5]
    for acc in low_income[:2]:
        targets = random.sample([a for a in accs if a != acc], 3)
        ts = base + timedelta(days=random.randint(30, 150), hours=10)
        all_txns += generate_profile_mismatch(profiles, acc, targets, ts)

    # 7. Shell account network
    shell_accs = random.sample([a for a in accs if a not in dormant_accounts], 5)
    consolidation = random.choice([a for a in accs if a not in shell_accs
                                   and a not in dormant_accounts])
    ts = base + timedelta(days=55, hours=9)
    all_txns += generate_shell_network(profiles, shell_accs, consolidation, ts)

    # ── NORMAL TRANSACTIONS ───────────────────────────────────────────────────

    print("Generating normal transactions...")

    normal_accs = [a for a in accs if a not in dormant_accounts]
    employer_acc = accs[0]

    # Salary credits — 1 month × employees
    for month_offset in range(1):
        month_ts = base + timedelta(days=30 * month_offset)
        employees = random.sample(normal_accs[1:], 8)
        all_txns += generate_salary_credits(profiles, employer_acc, employees, month_ts)

    # Utility payments for 20 accounts × 1 month
    for acc in random.sample(normal_accs, 20):
        for month_offset in range(1):
            ts = base + timedelta(days=30 * month_offset + random.randint(1, 10))
            all_txns += generate_utility_payments(profiles, acc, ts)

    # EMI payments for 15 accounts × 1 month
    for acc in random.sample(normal_accs, 15):
        for month_offset in range(1):
            ts = base + timedelta(days=30 * month_offset)
            all_txns += generate_emi_payments(profiles, acc, ts)

    # Merchant payments — 1 month only
    for acc in normal_accs:
        for month_offset in range(1):
            ts = base + timedelta(days=30 * month_offset)
            all_txns += generate_merchant_payments(profiles, acc, ts)

    # P2P transfers
    for _ in range(1):
        group = random.sample(normal_accs, 8)
        ts = base + timedelta(days=random.randint(0, 150))
        all_txns += generate_p2p_transfers(profiles, group, ts)

    # FD/RD investments
    for acc in random.sample(normal_accs, 10):
        ts = base + timedelta(days=random.randint(0, 30))
        all_txns += generate_fd_rd_transactions(profiles, acc, ts)

    # ── BUILD DATAFRAME ───────────────────────────────────────────────────────

    df = pd.DataFrame(all_txns)
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["transaction_id"] = [f"T{str(i+1).zfill(4)}" for i in range(len(df))]

    # ── ADD FRAUD LABEL (for your own reference / testing) ────────────────────
    df["is_fraud"] = df["note"].apply(
        lambda x: 1 if any(w in str(x) for w in
                           ["fraud", "dormant", "shell", "mismatch"]) else 0
    )

    return df, profiles


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO-SPECIFIC CSVs (for one-click demo buttons)
# ═══════════════════════════════════════════════════════════════════════════════

def extract_scenario_csvs(df, profiles):
    """Extract clean scenario CSVs for the 3 demo buttons"""

    cols = ["transaction_id", "from_account", "from_name", "to_account",
            "to_name", "amount", "timestamp", "channel",
            "ifsc_from", "ifsc_to", "location", "lat", "lon", "note"]

    # Scenario 1 — Round-trip
    rt = df[df["note"] == "round_trip_fraud"].head(6)[cols]
    rt.to_csv("data/scenario_roundtrip.csv", index=False)
    print(f"  ✅ scenario_roundtrip.csv — {len(rt)} transactions")

    # Scenario 2 — Structuring (first event only)
    struct_df = df[df["note"] == "structuring_fraud"]
    first_event_start = struct_df["timestamp"].min()
    first_event_end = (pd.to_datetime(first_event_start) +
                       timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
    struct = struct_df[struct_df["timestamp"] <= first_event_end][cols]
    struct.to_csv("data/scenario_structuring.csv", index=False)
    print(f"  ✅ scenario_structuring.csv — {len(struct)} transactions")

    # Scenario 3 — Dormant account
    dorm = df[df["note"].isin(
        ["dormant_activation_fraud", "dormant_dispersal_fraud"])
    ].head(5)[cols]
    dorm.to_csv("data/scenario_dormant.csv", index=False)
    print(f"  ✅ scenario_dormant.csv — {len(dorm)} transactions")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)

    print("\n🏦 FundTrace-AI Synthetic Data Generator")
    print("=" * 50)

    df, profiles = generate_all_data()

    # Save master dataset
    master_cols = [
        "transaction_id", "from_account", "from_name", "from_occupation",
        "from_income", "to_account", "to_name", "amount", "timestamp",
        "channel", "ifsc_from", "ifsc_to", "location", "lat", "lon",
        "transaction_type", "note", "is_fraud"
    ]
    df[master_cols].to_csv("data/transactions.csv", index=False)

    # Save scenario CSVs
    print("\nExtracting scenario CSVs...")
    extract_scenario_csvs(df, profiles)

    # Save customer profiles
    prof_df = pd.DataFrame(profiles).T.reset_index()
    prof_df.columns = ["account_id"] + list(prof_df.columns[1:])
    prof_df.drop(columns=["account_opened"], errors="ignore").to_csv(
        "data/customer_profiles.csv", index=False)

    # Summary
    fraud_count  = df["is_fraud"].sum()
    normal_count = len(df) - fraud_count
    print(f"\n📊 Dataset Summary")
    print(f"  Total transactions : {len(df)}")
    print(f"  Fraud transactions : {fraud_count} "
          f"({fraud_count/len(df)*100:.1f}%)")
    print(f"  Normal transactions: {normal_count} "
          f"({normal_count/len(df)*100:.1f}%)")
    print(f"\n  Fraud patterns included:")
    for pattern in ["round_trip", "structuring", "layering",
                    "dormant", "velocity", "profile_mismatch", "shell_network"]:
        count = df["note"].str.contains(pattern, na=False).sum()
        print(f"    • {pattern:<22} {count} transactions")

    print(f"\n✅ Files saved:")
    print(f"  data/transactions.csv        — master dataset")
    print(f"  data/scenario_roundtrip.csv  — demo button 1")
    print(f"  data/scenario_structuring.csv— demo button 2")
    print(f"  data/scenario_dormant.csv    — demo button 3")
    print(f"  data/customer_profiles.csv   — KYC reference")
    print(f"\n🎯 Run: python generate_synthetic_data.py")