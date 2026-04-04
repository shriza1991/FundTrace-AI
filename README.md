# 🏦 FundTrace-AI

> **Anti-Money Laundering (AML) Fraud Detection System for Union Bank of India**  
> Powered by graph analytics, ML anomaly detection, and Gemini AI — built with FastAPI + Streamlit.

---

## ⚡ Quick Start

> **First time?** Complete the [Setup](#️-setup-first-time) section below first, then come back here.

**Step 1 — Activate virtual environment**

# cmd
venv\Scripts\activate

```powershell
# Windows
venv\Scripts\Activate.ps1
```
#bash
```bash
# macOS / Linux
source venv/bin/activate
```

**Step 2 — Start the Backend** *(Terminal 1)*

> ⚠️ **Must be run from the project root** `D:\Projects\FundTrace-AI\` — NOT from inside the `backend\` folder.

```bash
uvicorn backend.app:app --reload
```
✅ API running at → `http://127.0.0.1:8000`  
📖 Swagger docs → `http://127.0.0.1:8000/docs`

**Step 3 — Start the Frontend** *(Terminal 2)*

```bash
streamlit run frontend/app.py
```
✅ Dashboard running at → `http://localhost:8501`

---

## 🗂️ Project Structure

```
FundTrace-AI/
├── backend/
│   ├── app.py               # FastAPI server (REST API)
│   ├── fraud_detection.py   # AML detection rules
│   ├── graph_builder.py     # Transaction graph construction
│   ├── risk_scoring.py      # Risk score calculator
│   └── explain.py           # Explainability module
├── frontend/
│   └── app.py               # Streamlit dashboard
├── data/                    # Transaction CSV files
├── generate_synthetic_data.py
├── requirements.txt
├── .env                     # API keys (never commit this)
└── .gitignore
```

---

## ⚙️ Prerequisites

- Python **3.10+**
- A **Gemini API key** — get one free at [Google AI Studio](https://aistudio.google.com/app/apikey)

---

## 🚀 Setup (First Time)

### 1. Clone & enter the project

```bash
git clone https://github.com/your-username/FundTrace-AI.git
cd FundTrace-AI
```

### 2. Create and activate a virtual environment

**Windows (PowerShell)**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your API key

Open `.env` and replace the placeholder with your real Gemini API key:

```env
GEMINI_API_KEY=your_actual_gemini_key_here
```

> ⚠️ This file is in `.gitignore` and will never be committed. Keep it secret.

### 5. Generate synthetic transaction data (optional)

Run this once to create demo scenario CSVs used by the Quick Demo buttons:

```bash
python generate_synthetic_data.py
```

---

## ▶️ Running the App

Open **two terminals** (both with the virtual environment activated).

### Terminal 1 — Start the Backend (FastAPI)

```bash
uvicorn backend.app:app --reload
```

The API will be available at:  
- Swagger UI → [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)  
- Health check → [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### Terminal 2 — Start the Frontend (Streamlit)

```bash
streamlit run frontend/app.py
```

The dashboard will open automatically at:  
👉 [http://localhost:8501](http://localhost:8501)

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Liveness probe |
| `POST` | `/analyze` | Upload CSV → run fraud detection |
| `POST` | `/generate-str` | Generate a Suspicious Transaction Report (STR) via Gemini AI |
| `POST` | `/ask` | Ask a natural-language question about transaction data |

### `/analyze` — Request
Upload a CSV file with these **required columns**:

| Column | Type | Description |
|--------|------|-------------|
| `from_account` | string | Sender account ID |
| `to_account` | string | Receiver account ID |
| `amount` | float | Transaction amount (INR) |
| `timestamp` | datetime | Transaction timestamp |

Optional enrichment columns: `from_name`, `to_name`, `from_occupation`, `from_income`, `ifsc_from`, `ifsc_to`, `channel`, `location`, `lat`, `lon`, `transaction_type`, `note`, `is_fraud`

---

## 🧠 Fraud Detection Signals

| Signal | Description |
|--------|-------------|
| **Cycle Detection** | Circular fund flows (A → B → C → A) |
| **Layering** | Multi-hop transaction chains to obscure origin |
| **Structuring / Smurfing** | Transactions split to stay below reporting thresholds |
| **Velocity** | Abnormally high transaction frequency |
| **Anomaly Detection** | Statistical outlier transactions |
| **Dormant Account Reactivation** | Sudden activity in long-inactive accounts |
| **ML Anomaly** | Isolation Forest unsupervised anomaly detection |

---

## 🤖 AI Features (Gemini 2.0 Flash)

- **STR Generator** — Produces a full, PMLA 2002-compliant Suspicious Transaction Report with regulatory citations
- **Ask AI** — Natural-language Q&A over your transaction data (answers in ₹ lakh / ₹ crore format)

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---------|-----|
| `Cannot reach the backend` | Make sure `uvicorn` is running in Terminal 1 |
| `Missing required columns` | Ensure your CSV has `from_account`, `to_account`, `amount`, `timestamp` |
| `AI service temporarily unavailable` | Check your `GEMINI_API_KEY` in `.env` is valid |
| `Scenario file not found` | Run `python generate_synthetic_data.py` first |
| Streamlit `ModuleNotFoundError` | Activate your `venv` before running Streamlit |

---

## 📄 License

Internal tool — Union Bank of India AML Compliance Division.  
Not for public distribution.
