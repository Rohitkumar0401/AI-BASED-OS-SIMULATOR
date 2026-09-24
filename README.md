# AI-Based OS Algorithm Simulator + Recommendation Engine

A unified simulator covering the core Operating Systems algorithms — CPU
scheduling, memory/page replacement, disk scheduling, and deadlock detection —
paired with an AI recommendation layer that explains *why* one algorithm
outperformed the others for a given input.

Unlike typical OS simulators that just show output for one algorithm at a
time, this project runs every algorithm in a category on the same input,
logs the results into a relational database, and uses that self-generated
data to train a machine learning model that recommends the best algorithm
for new inputs — with a plain-language explanation.

## Subjects covered
- **OS**: CPU scheduling, memory management, disk scheduling, deadlock detection
- **DBMS**: Normalized (3NF) relational schema, foreign keys, multi-table joins
- **AI/ML**: Classifier trained on our own simulation data (not an external dataset)

## Tech stack
- **Backend**: Python + Flask
- **Database**: Oracle (via SQL Command Line / SQL*Plus)
- **AI/ML**: scikit-learn
- **Frontend**: HTML / CSS / JavaScript

## Modules
| Module | Algorithms |
|---|---|
| CPU Scheduling | FCFS, SJF, SRTF, Round Robin |
| Memory Management | FIFO, LRU, Optimal |
| Disk Scheduling | FCFS, SSTF, SCAN / C-SCAN |
| Deadlock Detection | Banker's Algorithm |

## Project structure
```
ai-based-os-simulator/
├── backend/
│   ├── app.py
│   ├── cpu_scheduling/
│   ├── memory_management/
│   ├── disk_scheduling/
│   ├── deadlock/
│   ├── ai/
│   └── db/
│       ├── schema.sql
│       └── db_connector.py
├── frontend/
├── docs/
├── .gitignore
└── README.md
```

## Setup
1. Open SQL Command Line (or SQL*Plus), connect to your Oracle user, and run `backend/db/schema.sql`.
2. Update the credentials in `backend/db/db_connector.py` (user, password, dsn).
3. Install dependencies: `pip install flask oracledb scikit-learn pandas`
4. Run the app: `python backend/app.py`

## Team
| Member | Owns |
|---|---|
| Member A | CPU Scheduling module |
| Member B | Memory Management + Disk Scheduling |
| Member C | Deadlock Detection + database schema/normalization |
| Member D | AI recommendation engine (training pipeline + explanations) |
