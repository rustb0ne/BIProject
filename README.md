# Olist E-Commerce BI Project

End-to-end Business Intelligence pipeline built on the Brazilian Olist e-commerce dataset - featuring automated ETL, a Star Schema Data Warehouse, and self-hosted Metabase dashboards.

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
| Source Dataset | [Olist - Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) |

---

## Getting Started

### Prerequisites

Ensure the following software is installed before proceeding:

| Software | Version | Download |
|---|---|---|
| **Python** | 3.10 or higher | https://www.python.org/downloads/ |
| **MySQL Server** | 8.0 or higher | https://dev.mysql.com/downloads/mysql/ |
| **Java (JRE/JDK)** | 11 or higher | https://adoptium.net/ (required for Metabase) |
| **Git** | Any | https://git-scm.com/ |

Verify installations:
```bash
python --version      # Expected: Python 3.10.x or higher
mysql --version       # Expected: mysql  Ver 8.x.x
java -version         # Expected: openjdk version "11.x.x" or higher
```

---

### Step 1 - Clone the Repository

```bash
git clone https://github.com/rustb0ne/BIProject.git
cd BIProject
```

---

### Step 2 - Set Up Python Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows Command Prompt / PowerShell)
.venv\Scripts\activate

# Activate (macOS / Linux)
source .venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

**Expected output** - all packages install without errors:
```
Successfully installed pandas-2.2.2 sqlalchemy-2.0.30 pymysql-1.1.1 ...
```

> If you see `pip` warnings about package versions, they can be safely ignored as long as the install completes successfully.

---

### Step 3 - Configure MySQL Connection

Open `etl/config.py` and update the database credentials to match your local MySQL setup:

```python
# etl/config.py  (lines 9–12)
DB_HOST     = "127.0.0.1"   # MySQL host - use 127.0.0.1 for local
DB_PORT     = 3306           # Default MySQL port
DB_USER     = "root"         # Your MySQL username
DB_PASSWORD = ""             # Your MySQL password (empty string if none)
```

> **Important:** The MySQL user must have privileges to `CREATE DATABASE`, `CREATE TABLE`, and perform `INSERT`/`SELECT` on any database. The `root` user has these by default.

You can verify your MySQL connection manually before running the pipeline:
```bash
mysql -u root -p -e "SELECT VERSION();"
```

---

### Step 4 - Verify the Dataset

> The dataset is already included in this repository - no download required.

All 9 CSV files are pre-placed in `data/raw/`. Simply confirm they are present:

```
data/raw/
├── olist_orders_dataset.csv
├── olist_order_items_dataset.csv
├── olist_order_payments_dataset.csv
├── olist_order_reviews_dataset.csv
├── olist_customers_dataset.csv
├── olist_sellers_dataset.csv
├── olist_products_dataset.csv
├── olist_geolocation_dataset.csv
└── product_category_name_translation.csv
```

> The file names must exactly match the list above. The pipeline will raise a `FileNotFoundError` if any file is missing or misnamed.

---

### Step 5 - Run the ETL Pipeline

With the virtual environment active and dataset in place, run the master pipeline script from the **project root directory**:

```bash
python etl/run_etl_pipeline.py
```

This single command automatically executes **6 sequential steps**:

| Step | Script | Action |
|---|---|---|
| **0** | `00_setup_database.py` | Creates `olist_staging` and `olist_dwh` databases; runs DDL SQL files to build all tables |
| **1** | `01_extract.py` | Reads all 9 CSV files into pandas DataFrames; runs data profiling |
| **2** | `02_transform.py` | Cleans data, normalizes city names, builds the Star Schema (dim tables + fact table) |
| **3** | `03_load_staging.py` | Bulk-loads raw data into `olist_staging` (replica of CSVs) |
| **4** | `04_load_dwh.py` | Loads the transformed Star Schema into `olist_dwh` |
| **5** | `05_data_quality.py` | Runs 24 automated data quality checks and prints a summary report |

**Total runtime: ~3–4 minutes** on a average laptop.

Detailed logs are saved to `logs/pipeline_YYYYMMDD.log` for debugging.

> **If the pipeline fails at Step 0:** Check that MySQL is running (`net start MySQL80` on Windows) and that `DB_USER`/`DB_PASSWORD` in `config.py` are correct.

---

### Step 6 - Verify the Data Warehouse

After the pipeline completes, confirm that data was loaded correctly by running these queries in any MySQL client (MySQL Workbench, DBeaver, or the `mysql` CLI):

```sql
USE olist_dwh;

-- Check all tables were created and loaded
SELECT TABLE_NAME, TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'olist_dwh'
ORDER BY TABLE_NAME;
```

**Expected output:**

| TABLE_NAME | TABLE_ROWS (approx.) |
|---|---|
| `dim_customer` | 99,441 |
| `dim_product` | 32,951 |
| `dim_region` | 27 |
| `dim_seller` | 3,095 |
| `dim_time` | 800 |
| `fact_orders` | 112,650 |

---

### Step 7 - Launch Metabase Dashboard

**Download `metabase.jar`**

The JAR file is not included in the repository due to its size (~575 MB). Download it before proceeding:

1. Go to the official Metabase release page: https://www.metabase.com/start/oss/
2. Click **"Download Metabase"** - this downloads `metabase.jar` directly
3. Move the downloaded file into the **project root directory** (`BIProject/`):

```
BIProject/
├── metabase.jar    ← place it here
├── etl/
├── data/
└── ...
```

**Run Metabase**

Once `metabase.jar` is in the project root, start the server:

```bash
java --add-opens java.base/java.nio=ALL-UNNAMED -jar metabase.jar
```

Wait ~30–60 seconds for startup, then open your browser:

```
http://localhost:3000
```

**First-time setup (one-time only):**

1. Create an admin account (any email/password - this is local only)
2. On the **"Add your data"** screen, select **MySQL** and enter:
   - **Display name:** `olist_dwh`
   - **Host:** `127.0.0.1`
   - **Port:** `3306`
   - **Database name:** `olist_dwh`
   - **Username / Password:** same as `config.py`
3. Click **Save** → Metabase will detect the Star Schema tables automatically

> Metabase stores its configuration in `metabase.db.mv.db` (already present in the repo). If this file exists, the admin account and database connection are already configured - skip to opening `http://localhost:3000` directly.


```
Preconfig account:
Email: biadmin@gmail.com
Password: BI@12345678
```


---

## Dataset

| Attribute | Details |
|---|---|
| **Source** | Brazilian E-Commerce Public Dataset by Olist (Kaggle) |
| **Period** | September 2016 - October 2018 |
| **Scale** | ~99,441 orders · ~112,650 order items · 27 states |
| **License** | CC BY-NC-SA 4.0 (academic use only) |

---

## Full Report

See [`BI_Project_Group_09`](BI_Project_Group_09.pdf) for the complete analysis: dataset profiling, Data Warehouse design rationale, ETL process walkthrough, dashboard screenshots, and business insights.
