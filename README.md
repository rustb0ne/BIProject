# Olist E-Commerce BI Project

End-to-end Business Intelligence pipeline built on the Brazilian Olist e-commerce dataset — featuring automated ETL, a Star Schema Data Warehouse, and self-hosted Metabase dashboards.

---

## Objectives

Answer key business questions using a **Data Warehouse + BI Dashboard** system:

- Which product category generates the most revenue?
- How does revenue trend across months and quarters?
- Which states and regions contribute the most orders?
- How does late delivery impact customer review scores?

---

## Project Structure

```
BIProject/
├── data/
│   ├── raw/            # 9 original CSV files from Kaggle
│   └── processed/      # Cleaned / transformed data
├── etl/
│   ├── 00_setup_database.py    # Create databases
│   ├── 01_extract.py           # Read & profile raw CSVs
│   ├── 02_transform.py         # Clean data, build Star Schema
│   ├── 03_load_staging.py      # Load into olist_staging
│   ├── 04_load_dwh.py          # Load into olist_dwh
│   ├── 05_data_quality.py      # Post-load quality checks
│   ├── config.py               # Centralised configuration
│   ├── logger.py               # Logging utility
│   └── run_etl_pipeline.py     # Master pipeline runner
├── sql/
│   ├── 01_create_staging.sql   # Staging DDL
│   ├── 02_create_dwh.sql       # Data Warehouse DDL (Star Schema)
│   └── 03_analytical_queries.sql # Sample analytical queries
├── logs/                       # ETL log files
├── metabase.jar                # Self-hosted Metabase
└── requirements.txt
```

---

## Architecture

```
CSV Files (9 files)
    │
    ▼  ETL Pipeline (Python + pandas)
    │
    ├──► MySQL: olist_staging  (raw data replica)
    │
    └──► MySQL: olist_dwh      (Star Schema)
              │
              ▼
         Metabase Dashboard
```

### Star Schema (`olist_dwh`)

| Table | Type | Rows | Description |
|---|---|---|---|
| `fact_orders` | Fact | ~112,650 | Grain: one row per order item |
| `dim_time` | Dimension | 800 | Calendar dimension (ETL-generated) |
| `dim_customer` | Dimension | ~99,441 | Customer information |
| `dim_product` | Dimension | ~32,951 | Products + English category names |
| `dim_seller` | Dimension | ~3,095 | Seller information |
| `dim_region` | Dimension | 27 | 27 Brazilian states → 5 macro-regions |

---

## Tech Stack

| Component | Tool |
|---|---|
| ETL Language | Python 3.10 + pandas 2.x |
| Database | MySQL 8.x |
| DB Connector | SQLAlchemy + PyMySQL |
| BI Dashboard | Metabase (self-hosted) |
| Source Dataset | [Olist — Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) |

---

## Getting Started

### 1. Set up the environment

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Configure the database connection

Edit `etl/config.py` with your MySQL credentials:

```python
DB_HOST     = "127.0.0.1"
DB_PORT     = 3306
DB_USER     = "root"
DB_PASSWORD = ""
```

### 3. Place raw data files

Download the 9 CSV files from Kaggle and place them in `data/raw/`.

### 4. Run the full ETL pipeline

```bash
python etl/run_etl_pipeline.py
```

The pipeline executes 6 sequential steps automatically:
**Setup → Extract → Transform → Load Staging → Load DWH → Data Quality Check**

### 5. Launch Metabase

```bash
java --add-opens java.base/java.nio=ALL-UNNAMED -jar metabase.jar
# Open: http://localhost:3000
```

---

## Dataset

| Attribute | Details |
|---|---|
| **Source** | Brazilian E-Commerce Public Dataset by Olist (Kaggle) |
| **Period** | September 2016 — October 2018 |
| **Scale** | ~99,441 orders · ~112,650 order items · 27 states |
| **License** | CC BY-NC-SA 4.0 (academic use only) |

---

## Full Report

See [`BI_Project_Group_09`](BI_Project_Group_09.pdf) for the complete analysis: dataset profiling, Data Warehouse design rationale, ETL process walkthrough, dashboard screenshots, and business insights.
