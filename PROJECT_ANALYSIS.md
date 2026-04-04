# FundTrace-AI - Comprehensive Project Documentation

> **AI-Powered Fraud Detection & Anti-Money Laundering System**  
> Generated: March 31, 2026  
> Audience: Developers, AI models, system architects

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Architecture Diagram](#3-architecture-diagram)
4. [Folder Structure](#4-folder-structure-explained)
5. [Key File Explanations](#5-key-file-explanations)
6. [Execution Flow](#6-execution-flow)
7. [Dependencies](#7-dependencies-explained)
8. [Quality Analysis](#8-quality-analysis-ratings-1-10)
9. [Issues Detected](#9-issues-detected)
10. [Improvement Plan](#10-improvement-plan-priority-order)
11. [Summary](#11-summary-for-quick-understanding)

---

## 1. PROJECT OVERVIEW

**Project Name:** FundTrace-AI  
**Purpose:** AI-powered fraud detection and anti-money laundering (AML) system  
**Type:** Monolithic Python application with web-based frontend  
**Primary Use Case:** Analyze financial transaction networks to detect suspicious patterns indicative of money laundering

### Key Features:
- 🔁 **Cycle Detection** - Identifies circular fund flows (round-tripping)
- 🔄 **Layering Detection** - Detects multi-hop transactions to obscure origin
- 💰 **Structuring Detection** - Finds patterns of splitting large amounts into smaller ones
- ⚡ **Velocity Analysis** - Detects rapid-fire transactions
- 💤 **Dormant Account Activation** - Flags sudden activity after long inactivity
- 🤖 **ML Anomaly Detection** - Uses Isolation Forest for behavioral anomalies
- 📈 **Interactive Visualization** - Network graphs showing transaction flows

---

## 2. TECH STACK

### Backend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | **FastAPI** | REST API framework |
| Server | **Uvicorn** | ASGI app server |
| Language | **Python 3.x** | Core language |

### Frontend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| UI Framework | **Streamlit** | Web dashboard/UI |
| HTTP Client | **requests** | Call backend API |

### Data & Analysis
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Data Processing | **Pandas** | CSV parsing, data transformation |
| Graph Analysis | **NetworkX** | Directed graph creation, cycle detection |
| Visualization | **PyVis** | Interactive network visualization |
| Machine Learning | **Scikit-learn** | Isolation Forest for anomaly detection |
| PDF Generation | **ReportLab** | Generate fraud reports |

### Libraries Used
- **fastapi** - REST API framework
- **uvicorn** - ASGI server
- **pandas** - Data manipulation
- **networkx** - Graph algorithms
- **streamlit** - Web UI
- **matplotlib** - Static charts (imported but minimal use)
- **scikit-learn** - ML anomaly detection
- **python-multipart** - File upload handling
- **pyvis** - Interactive graphs
- **reportlab** - PDF generation

---

## 3. ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────┐
│         USER (Browser)                       │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│    FRONTEND (Streamlit)                      │
│    frontend/app.py                          │
│  - File upload interface                    │
│  - Display fraud alerts                     │
│  - Interactive graph visualization          │
│  - Investigation tools                      │
│  - PDF export                               │
└────────────────┬────────────────────────────┘
                 │ HTTP POST /analyze
                 ▼
┌─────────────────────────────────────────────┐
│      BACKEND API (FastAPI)                   │
│      backend/app.py                         │
└────────────────┬────────────────────────────┘
                 │
      ┌──────────┼──────────┐
      ▼          ▼          ▼
   ┌──────────────────────────────────────┐
   │   ANALYSIS PIPELINE                   │
   │                                       │
   │ 1. build_graph()                      │
   │    └─ Creates DirectedGraph from CSV │
   │                                       │
   │ 2. detect_signals()                   │
   │    ├─ detect_cycles()                │
   │    ├─ detect_layering()              │
   │    ├─ detect_structuring()           │
   │    ├─ detect_velocity()              │
   │    ├─ detect_anomaly()               │
   │    ├─ detect_dormant()               │
   │    └─ ml_anomaly()                   │
   │                                       │
   │ 3. calculate_risk()                   │
   │    └─ Weighted scoring on signals    │
   │                                       │
   │ 4. generate_explanation()             │
   │    └─ Human-readable explanations    │
   └──────────────────────────────────────┘
                 │
                 ▼
     JSON Response with Alerts
     (fraud_paths, signals, evidence)
                 │
                 ▼
        Display to User
```

---

## 4. FOLDER STRUCTURE EXPLAINED

```
FundTrace-AI/
│
├── backend/                    # Python FastAPI backend
│   ├── app.py                  # Main FastAPI application & /analyze endpoint
│   ├── graph_builder.py        # Constructs DirectedGraph from transactions
│   ├── fraud_detection.py      # 7 fraud detection algorithms
│   ├── risk_scoring.py         # Risk score calculation with weights
│   ├── explain.py              # Generate human-readable evidence
│   ├── utils.py                # (Currently empty - placeholder)
│   └── __init__.py             # Python package marker
│
├── frontend/                   # Streamlit web UI
│   └── app.py                  # Complete Streamlit dashboard
│
├── lib/                        # Third-party JS libraries
│   ├── bindings/
│   │   └── utils.js            # Node.js graph interaction helper
│   ├── tom-select/             # Dropdown component library
│   │   ├── tom-select.complete.min.js
│   │   └── tom-select.css
│   └── vis-9.1.2/              # VisualizationJS network graph library
│       ├── vis-network.min.js
│       └── vis-network.css
│
├── data/                       # Sample data
│   └── transactions.csv        # Sample transaction dataset (14 rows)
│
└── requirements.txt            # Python dependencies
```

### Directory Responsibilities:

**backend/** - Core fraud detection logic
- Receives CSV data from frontend
- Performs graph analysis
- Detects fraud patterns
- Returns risk assessments

**frontend/** - User-facing interface
- File upload UI
- Results display
- Interactive graph visualization
- Investigation & export tools

**lib/** - Client-side visualization assets
- Network graph rendering (PyVis + vis.js)
- Interactive graph controls
- UI component libraries

**data/** - Sample/test data
- Contains example transactions for development & testing

---

## 5. KEY FILE EXPLANATIONS

### 5.1 backend/app.py - Main FastAPI Application

**Purpose:** Entry point, API orchestrator

**Key Functions:**
- `get_fraud_paths(cycles)` → Converts cycle list to readable format (A → B → C → A)
- `POST /analyze` → Main endpoint that:
  1. Accepts CSV file upload
  2. Builds transaction graph
  3. Detects 7 fraud signals
  4. Calculates risk scores
  5. Generates explanations
  6. Returns comprehensive JSON response

**Response Structure:**
```json
{
  "alerts": [
    {
      "account": "A",
      "risk_score": 150,
      "severity": "HIGH",
      "reasons": ["cycle", "layering", "velocity"],
      "explanation": "🔁 Circular transactions detected...",
      "evidence": [transaction1, transaction2, ...]
    }
  ],
  "signals": {
    "cycle": [nodes],
    "layering": [nodes],
    "structuring": [nodes],
    ...
  },
  "fraud_paths": ["A → B → C → A", ...]
}
```

---

### 5.2 backend/fraud_detection.py - Signal Detection Algorithms

**Purpose:** Detect 7 different fraud patterns

| Signal | Function | Logic |
|--------|----------|-------|
| **Cycle** | `detect_cycles()` | Finds circular fund flows (len > 2) using NetworkX |
| **Layering** | `detect_layering()` | Finds multi-hop paths (len ≥ 4) |
| **Structuring** | `detect_structuring()` | Flags accounts with >3 outgoing transactions |
| **Velocity** | `detect_velocity()` | Flags if 3+ txns from same account within 1 hour |
| **Anomaly** | `detect_anomaly()` | Flags amounts > mean + 2σ |
| **Dormant** | `detect_dormant()` | Flags if account gap > 7 days |
| **ML Anomaly** | `ml_anomaly()` | Isolation Forest (contamination=0.1) on amounts |

---

### 5.3 backend/graph_builder.py - Transaction Graph

**Purpose:** Convert CSV data into a directed graph

**Function:** `build_graph(df)`
- Creates NetworkX DiGraph
- Adds nodes as sender/receiver
- Edges contain: amount, timestamp, channel, location
- Used for cycle/path detection

---

### 5.4 backend/risk_scoring.py - Risk Calculation

**Purpose:** Calculate holistic risk score per account

**Weights per Signal:**
```
cycle: 50 (high priority)
ml_anomaly: 40
anomaly: 35
layering: 30
structuring: 20
velocity: 25
dormant: 20
```

**Severity Levels:**
- HIGH: score ≥ 70
- MEDIUM: score ≥ 40
- LOW: score < 40

---

### 5.5 backend/explain.py - Explanation Generator

**Purpose:** Create human-readable fraud evidence

**Output:**
- Summary: concatenated emoji + explanation strings
- Evidence: top 3 transactions from flagged account

**Example:**
> 🔁 Circular transactions detected: funds leave and return to Account A...
> 🤖 ML anomaly detected: transaction behavior deviates from normal patterns...

---

### 5.6 frontend/app.py - Streamlit Dashboard

**Purpose:** Complete user interface (450+ lines)

**Key Sections:**
1. **File Upload** - Accept CSV with transactions
2. **Fraud Alerts** - Expandable alert cards with severity indicators
3. **Fraud Paths** - Display detected circular fund flows
4. **Interactive Network Graph** - PyVis-based visualization with:
   - Color-coded nodes (red = high risk)
   - Edge labels with amounts
   - Hover details with channel info
5. **Investigation Tool** - Select account → view all in/out transactions
6. **Analytics Dashboard** - Transaction volume & amount trends
7. **Geographic Map** - (If lat/lon columns present)
8. **PDF Export** - Generate downloadable fraud report

---

## 6. EXECUTION FLOW

### Step-by-Step Request Flow:

```
1. USER UPLOADS CSV
   └─ frontend/app.py: st.file_uploader()

2. FRONTEND PREPROCESSES
   └─ df = pd.read_csv(uploaded_file)

3. FRONTEND SENDS TO BACKEND
   └─ POST http://127.0.0.1:8000/analyze
   └─ Body: multipart/form-data {file: transactions.csv}

4. BACKEND RECEIVES & PROCESSES
   └─ backend/app.py: @app.post("/analyze")
   └─ df = pd.read_csv(file.file)

5. BUILD GRAPH
   └─ backend/graph_builder.py: build_graph(df)
   └─ Returns: nx.DiGraph with all transactions as edges

6. DETECT FRAUD SIGNALS (PARALLEL)
   ├─ detect_cycles(G) → finds cycles
   ├─ detect_layering(G) → finds long paths
   ├─ detect_structuring(df) → counts per account
   ├─ detect_velocity(df) → time windows
   ├─ detect_anomaly(df) → statistical outliers
   ├─ detect_dormant(df) → inactivity gaps
   └─ ml_anomaly(df) → Isolation Forest

7. FOR EACH NODE IN GRAPH
   ├─ backend/risk_scoring.py: calculate_risk(node, signals)
   │  └─ Sums weighted scores from matched signals
   ├─ backend/explain.py: generate_explanation(node, df, signals)
   │  └─ Creates human-readable summary + evidence
   └─ Add to results[] if risk_score > 0

8. COMPILE FRAUD PATHS
   └─ Convert cycles to A → B → C → A format

9. RETURN JSON
   └─ alerts[], signals{}, fraud_paths[]

10. FRONTEND DISPLAYS RESULTS
    ├─ st.expander() for each alert
    ├─ st.dataframe() for evidence
    ├─ PyVis network graph
    ├─ Charts & maps
    └─ PDF download button
```

### File Interactions:
```
app.py (frontend)
    ↓ (upload CSV)
app.py (backend)
    ├─→ graph_builder.py (create graph)
    ├─→ fraud_detection.py (7 detectors)
    ├─→ risk_scoring.py (score calculation)
    └─→ explain.py (explanations)
    ↓ (return JSON)
app.py (frontend)
    ├─→ lib/vis network graph
    └─→ Display to user
```

---

## 7. DEPENDENCIES EXPLAINED

| Package | Version | Purpose |
|---------|---------|---------|
| **fastapi** | latest | REST API framework with automatic OAPI docs |
| **uvicorn** | latest | ASGI server to run FastAPI |
| **pandas** | latest | CSV parsing, data manipulation, filtering |
| **networkx** | latest | Graph algorithms (cycles, paths, DiGraph) |
| **streamlit** | latest | Web UI framework (no explicit server needed) |
| **matplotlib** | latest | Static charting (imported but minimal use) |
| **scikit-learn** | latest | IsolationForest for ML anomaly detection |
| **python-multipart** | latest | File upload/multipart form parsing |
| **pyvis** | latest | Interactive network graph visualization |
| **reportlab** | latest | PDF generation for fraud reports |

### Missing Dependencies:
- ❌ No database (SQLite, PostgreSQL, etc.) - stateless single-file processing
- ❌ No authentication/authorization
- ❌ No caching layer
- ❌ No API key/rate limiting
- ❌ No structured logging

---

## 8. QUALITY ANALYSIS (Ratings 1-10)

| Aspect | Rating | Comments |
|--------|--------|----------|
| **Code Structure** | 6/10 | Good separation of concerns, but tight coupling between modules |
| **Readability** | 8/10 | Clear function names, decent comments, good emoji use |
| **Modularity** | 6/10 | Functions are single-purpose, but no clear interface contracts |
| **Scalability** | 3/10 | Single-threaded, in-memory, no optimization for large datasets |
| **Error Handling** | 4/10 | Minimal try-catch blocks, no input validation, assumes CSV format |
| **Security Practices** | 3/10 | No authentication, CORS wide open, no rate limiting |
| **Performance** | 4/10 | O(n²) cycle/layering detection, rebuilds graph per request |
| **Testing** | 1/10 | No test files present |
| **Documentation** | 5/10 | Function docstrings missing, no README, code is only documentation |
| **Maintainability** | 6/10 | Clear logic but tight coupling, hard to modify signals |

---

## 9. ISSUES DETECTED

### 🔴 Critical Issues

#### 1. No Input Validation
- ❌ No checks for required CSV columns
- ❌ No data type validation
- ❌ Will crash if columns missing: from, to, amount, timestamp

#### 2. API Security Problems
- ❌ No CORS configuration (open to all origins)
- ❌ No authentication/authorization
- ❌ No rate limiting (DOS risk)
- ❌ File upload size unbounded

#### 3. Performance Bottlenecks
- ❌ `detect_layering()` has O(n²) complexity with nested loops
- ❌ Graph rebuilt on every request (not cached)
- ❌ All detectors run sequentially (could parallelize)
- ❌ No optimization for large datasets (10k+ transactions)

#### 4. Data Type Issues
- ❌ Timestamp string conversion inconsistent (detect_velocity uses manual parsing)
- ❌ `df['timestamp']` converted multiple times per detector
- ❌ Dormant detection calculates `.days` on timedelta incorrectly

### 🟡 High-Priority Issues

#### 5. Error Handling
- ❌ Endpoint has no try-except, will return 500 on any error
- ❌ Backend error message not user-friendly (just thrown to frontend)
- ❌ Missing validation on file upload format

#### 6. Data Integrity
- ❌ ML anomaly (`ml_anomaly()`) modifies original df with "anomaly" column
- ❌ Isolation Forest contamination hardcoded (0.1) instead of configurable
- ❌ No handling of NaN/null values in transactions

#### 7. Graph Issues
- ❌ Duplicate edges not handled (same from-to pairs overwrite)
- ❌ Self-loops not explicitly excluded
- ❌ No weighted path detection (treats $1 same as $1M)

#### 8. Frontend Issues
- ❌ Hardcoded backend URL "http://127.0.0.1:8000" (not configurable)
- ❌ PDF generation uses only first 3 transactions per account (incomplete evidence)
- ❌ No error message if backend crashes

### 🟠 Medium-Priority Issues

#### 9. Code Smells
- ❌ `utils.py` is empty (dead code)
- ❌ `matplotlib` imported but never used in frontend
- ❌ Magic numbers everywhere (weights, thresholds, timeouts)
- ❌ Duplication of timestamp parsing

#### 10. Missing Features
- ❌ No logging (can't debug production issues)
- ❌ No caching of analysis results
- ❌ No database persistence
- ❌ No batch processing for large files
- ❌ No alert thresholds configuration

### 🔵 Low-Priority Issues

#### 11. Frontend Minor
- ❌ Graph visualization can be slow with 1000+ nodes
- ❌ No pagination for large alert lists
- ❌ PDF export incomplete (only sample transactions)
- ❌ Map requires lat/lon columns (not always present)

---

## 10. IMPROVEMENT PLAN (Priority Order)

### Phase 1: Critical Fixes (Do Immediately)

#### 1.1 Add Input Validation
```python
# In backend/app.py
REQUIRED_COLUMNS = ['from', 'to', 'amount', 'timestamp']
OPTIONAL_COLUMNS = ['channel', 'location', 'lat', 'lon']

@app.post("/analyze")
async def analyze(file: UploadFile):
    df = pd.read_csv(file.file)
    
    # Validate columns
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise HTTPException(400, f"Missing columns: {missing}")
    
    # Validate data types
    df['amount'] = pd.to_numeric(df['amount'], errors='raise')
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='raise')
```

#### 1.2 Add API Security
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Only Streamlit
    allow_methods=["POST"],
    allow_credentials=True,
)

# Add rate limiting
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/analyze")
@limiter.limit("5/minute")
async def analyze(request: Request, file: UploadFile):
    ...
```

#### 1.3 Add Error Handling
```python
@app.post("/analyze")
async def analyze(file: UploadFile):
    try:
        df = pd.read_csv(file.file)
        # ... analysis ...
        return results
    except ValueError as e:
        raise HTTPException(400, f"Invalid data: {str(e)}")
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(500, "Analysis failed")
```

---

### Phase 2: Performance Optimization

#### 2.1 Optimize detect_layering()
```python
# BEFORE: O(n²) with nested loops
# AFTER: Use BFS to find paths efficiently

from collections import deque

def detect_layering(G):
    """Find paths of length 4+ using BFS instead of all_simple_paths"""
    paths = []
    for start_node in G.nodes():
        visited = {start_node}
        queue = deque([(start_node, [start_node])])
        
        while queue:
            node, path = queue.popleft()
            if len(path) >= 4:
                paths.append(path)
            
            for neighbor in G.neighbors(node):
                if len(path) < 5 and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
    
    return paths
```

#### 2.2 Cache Timestamp Conversion
```python
# BEFORE: Convert in each detector
# AFTER: Convert once in app.py

df['timestamp'] = pd.to_datetime(df['timestamp'])

# Pass to all detectors
detect_velocity(df)  # Uses already-converted column
detect_dormant(df)
```

#### 2.3 Parallelize Signal Detection
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    cycle_future = executor.submit(detect_cycles, G)
    layering_future = executor.submit(detect_layering, G)
    velocity_future = executor.submit(detect_velocity, df)
    ml_future = executor.submit(ml_anomaly, df)
    
    signals = {
        "cycle": cycle_future.result(),
        "layering": layering_future.result(),
        "velocity": velocity_future.result(),
        "ml_anomaly": ml_future.result(),
    }
```

---

### Phase 3: Refactoring & Structure

#### 3.1 Create Configuration Module
```python
# config.py
SIGNAL_WEIGHTS = {
    "cycle": 50,
    "layering": 30,
    "structuring": 20,
    "velocity": 25,
    "anomaly": 35,
    "dormant": 20,
    "ml_anomaly": 40
}

RISK_THRESHOLDS = {
    "HIGH": 70,
    "MEDIUM": 40,
    "LOW": 0
}

ML_CONTAMINATION = 0.1
VELOCITY_WINDOW_SECONDS = 3600
DORMANT_DAYS = 7
```

#### 3.2 Create Data Models with Pydantic
```python
# models.py
from pydantic import BaseModel

class Transaction(BaseModel):
    from_account: str
    to_account: str
    amount: float
    timestamp: datetime
    channel: str = "Unknown"
    location: str = "Unknown"

class FraudAlert(BaseModel):
    account: str
    risk_score: float
    severity: str
    reasons: List[str]
    explanation: str
    evidence: List[Transaction]
```

#### 3.3 Add Logging
```python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.FileHandler("fraud_detection.log")
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# In app.py
@app.post("/analyze")
async def analyze(file: UploadFile):
    logger.info(f"Analyzing file: {file.filename}")
    try:
        # ... analysis ...
        logger.info(f"Found {len(results)} alerts")
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
```

---

### Phase 4: Advanced Features

#### 4.1 Add Database Persistence
```python
# Store results for historical analysis
from sqlalchemy import create_engine
engine = create_engine("sqlite:///fraud_history.db")

class AnalysisRecord(Base):
    __tablename__ = "analyses"
    
    id: int = Column(Integer, primary_key=True)
    timestamp: datetime = Column(DateTime)
    file_name: str = Column(String)
    results: JSON = Column(JSON)
```

#### 4.2 Add Configuration UI
```python
# frontend/config.py
st.sidebar.header("⚙️ Configuration")

# Allow users to adjust weights
weights = {
    "cycle": st.slider("Cycle weight", 0, 100, 50),
    "layering": st.slider("Layering weight", 0, 100, 30),
    ...
}
```

#### 4.3 Add Historical Analytics
```python
# frontend/analytics.py
st.subheader("📈 Historical Trends")

# Query database
historical = pd.read_sql("SELECT * FROM analyses", engine)
st.line_chart(historical.groupby('timestamp')['alert_count'].sum())
```

---

### Phase 5: Testing & Monitoring

#### 5.1 Add Unit Tests
```python
# tests/test_fraud_detection.py
import pytest
from backend.fraud_detection import detect_cycles

def test_detect_cycles():
    # Create mock graph
    G = nx.DiGraph()
    G.add_edges_from([(1,2), (2,3), (3,1)])
    
    cycles = detect_cycles(G)
    assert len(cycles) == 1
    assert set(cycles[0]) == {1, 2, 3}

def test_detect_velocity():
    df = pd.DataFrame({
        'from': ['A', 'A', 'A'],
        'timestamp': ['2026-01-01 10:00', '2026-01-01 10:15', '2026-01-01 10:30']
    })
    
    result = detect_velocity(df)
    assert 'A' in result
```

#### 5.2 Add Monitoring
```python
# Add Prometheus metrics
from prometheus_client import Counter, Histogram

analysis_counter = Counter('analyses_total', 'Total analyses')
analysis_duration = Histogram('analysis_duration_seconds', 'Analysis duration')

@app.post("/analyze")
@analysis_duration.time()
async def analyze(file: UploadFile):
    analysis_counter.inc()
    ...
```

---

### Phase 6: Better Folder Structure

**Proposed New Structure:**
```
FundTrace-AI/
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app initialization
│   ├── config.py               # Configuration & constants
│   ├── models.py               # Pydantic models
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints.py        # API routes
│   ├── services/
│   │   ├── __init__.py
│   │   ├── graph_service.py    # Graph building
│   │   ├── detection_service.py # Signal detection
│   │   ├── scoring_service.py  # Risk scoring
│   │   └── explain_service.py  # Explanations
│   ├── utils/
│   │   ├── __init__.py
│   │   └── validators.py       # Input validation
│   ├── db/
│   │   ├── __init__.py
│   │   └── models.py           # SQLAlchemy models
│   └── logs/
│
├── frontend/
│   ├── app.py
│   ├── pages/
│   │   ├── alerts.py
│   │   ├── graphs.py
│   │   └── reports.py
│   └── components/
│       └── chart_components.py
│
├── tests/
│   ├── __init__.py
│   ├── test_fraud_detection.py
│   ├── test_risk_scoring.py
│   ├── test_graph_builder.py
│   └── test_api.py
│
├── data/
│   └── transactions.csv
│
├── docs/
│   ├── README.md
│   ├── API.md
│   └── ARCHITECTURE.md
│
├── requirements.txt
├── .env.example              # Environment variables template
├── .gitignore
├── docker-compose.yml
└── Dockerfile
```

---

### Phase 7: Documentation Additions

**Create README.md:**
```markdown
# FundTrace-AI - Fraud Detection System

## Quick Start
1. Install dependencies: `pip install -r requirements.txt`
2. Run backend: `uvicorn backend.main:app --reload`
3. Run frontend: `streamlit run frontend/app.py`
4. Upload transactions CSV

## Configuration
See `.env.example` for settings

## API Documentation
Auto-generated at http://localhost:8000/docs
```

**Create API.md** documenting /analyze endpoint

**Create ARCHITECTURE.md** explaining design decisions

---

## 11. SUMMARY FOR QUICK UNDERSTANDING

### What is FundTrace-AI?
A **fraud detection & anti-money laundering system** that analyzes financial transaction networks to identify suspicious patterns.

### How Does It Work?
1. **User uploads CSV** with transaction data (from, to, amount, timestamp, etc.)
2. **Backend analyzes** using 7 fraud detection algorithms:
   - Cycle detection (round-tripping)
   - Layering (multi-hop obscuring)
   - Structuring (splitting large amounts)
   - Velocity (rapid transactions)
   - Anomaly (statistical outliers)
   - Dormancy (sudden account activation)
   - ML Anomaly (Isolation Forest)
3. **Risk scoring** assigns severity to flagged accounts
4. **Frontend displays** interactive results, fraud paths, network graphs

### Tech Stack
- **Backend:** FastAPI + Python
- **Frontend:** Streamlit
- **Analysis:** NetworkX (graphs) + Scikit-learn (ML)
- **Visualization:** PyVis (interactive networks)

### Current Strengths
✅ Clear module separation  
✅ Comprehensive fraud signal detection  
✅ Interactive visualization  
✅ AI-powered explanations  
✅ Multiple detection methods (rule-based + ML)

### Current Weaknesses
❌ No input validation or error handling  
❌ Performance issues with large datasets  
❌ No security (authentication, rate limiting, CORS)  
❌ No testing or logging  
❌ No database persistence  
❌ Hardcoded configuration

### Top 3 Immediate Fixes
1. **Add input validation & error handling** (prevent crashes)
2. **Fix performance bottleneck** in detect_layering() (O(n²))
3. **Add API security** (CORS, rate limiting, validation)

### Development Recommendations
- **Short-term:** Fix critical security/performance issues
- **Medium-term:** Add testing, logging, configuration
- **Long-term:** Add persistence, advanced analytics, monitoring

---

## 📌 Files at a Glance

| File | LOC | Purpose |
|------|-----|---------|
| backend/app.py | 60 | FastAPI endpoint orchestrator |
| backend/fraud_detection.py | 80 | 7 fraud detection algorithms |
| backend/graph_builder.py | 15 | Graph construction |
| backend/risk_scoring.py | 30 | Risk calculation |
| backend/explain.py | 40 | Explanation generation |
| frontend/app.py | 450 | Streamlit dashboard |
| **Total** | **~675** | Complete application |

---

## 🧭 Navigation Guide

- **For Architecture Overview:** See section 3
- **For Understanding Code:** See section 5
- **For Debugging Issues:** See section 9
- **For Improvement Steps:** See section 10
- **Quick Primer:** See section 11 (Summary)

---

*This documentation is AI-optimized for quick comprehension by Claude, ChatGPT, and other language models.*
