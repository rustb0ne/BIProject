# Olist E-Commerce BI Project

Phân tích toàn diện dữ liệu thương mại điện tử Brazil bằng Python ETL + MySQL Data Warehouse + Metabase Dashboard.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Database | MySQL 8.4 (Laragon) |
| ETL | Python 3.12 (.venv) |
| BI Dashboard | Metabase (JAR) |
| Data | Olist Brazilian E-Commerce (Kaggle) |

---

## Dataset

**Brazilian E-Commerce Public Dataset by Olist**
- ~99,441 orders | ~32,951 products | ~3,095 sellers
- Thời gian: 09/2016 – 10/2018

| File | Rows |
|---|---|
| olist_orders_dataset.csv | 99,441 |
| olist_order_items_dataset.csv | 112,650 |
| olist_order_payments_dataset.csv | 103,886 |
| olist_order_reviews_dataset.csv | 99,224 |
| olist_customers_dataset.csv | 99,441 |
| olist_sellers_dataset.csv | 3,095 |
| olist_products_dataset.csv | 32,951 |
| olist_geolocation_dataset.csv | 1,000,163 |
| product_category_name_translation.csv | 71 |

---

## Cấu trúc thư mục

```
BIProject/
├── .venv/                        # Python virtual environment
├── data/
│   ├── raw/                      # 9 file CSV gốc
│   └── processed/                # Output processed (nếu cần)
├── etl/
│   ├── config.py                 # DB credentials, paths, constants
│   ├── logger.py                 # Colored logger
│   ├── 00_setup_database.py      # Tạo MySQL databases + tables
│   ├── 01_extract.py             # Đọc CSV, profiling, validate
│   ├── 02_transform.py           # Làm sạch, tính metrics, build star schema
│   ├── 03_load_staging.py        # Bulk load → olist_staging
│   ├── 04_load_dwh.py            # Load → olist_dwh (star schema)
│   ├── 05_data_quality.py        # 24 automated quality checks
│   └── run_etl_pipeline.py       # Master pipeline runner
├── sql/
│   ├── 01_create_staging.sql     # DDL: staging tables
│   ├── 02_create_dwh.sql         # DDL: star schema (fact + 5 dims)
│   └── 03_analytical_queries.sql # Analytical SQL queries
├── reports/
│   └── insight_report.md         # Báo cáo phân tích đầy đủ
├── logs/                         # ETL execution logs
├── requirements.txt
└── README.md
```

---

## Data Warehouse - Star Schema

```
dim_time ──────────────────────────────────────────────┐
dim_customer ──────────────────────────────────────┐   │
dim_product ────────────────────────────────────┐  │   │
dim_seller ──────────────────────────────────┐  │  │   │
dim_region ───────────────────────────────┐  │  │  │   │
                                          ▼  ▼  ▼  ▼   ▼
                                        ┌──────────────────┐
                                        │   fact_orders    │
                                        │ ─────────────── │
                                        │ price            │
                                        │ freight_value    │
                                        │ total_revenue    │
                                        │ review_score     │
                                        │ delivery_days    │
                                        │ is_on_time       │
                                        │ delay_days       │
                                        └──────────────────┘
```

**DWH sau khi load:**
| Table | Rows |
|---|---|
| dim_time | 800 |
| dim_region | 27 |
| dim_customer | 99,441 |
| dim_product | 32,951 |
| dim_seller | 3,095 |
| fact_orders | 112,650 |

---

## Cài đặt & Chạy

### Prerequisites
- Python 3.12
- MySQL (Laragon) đang chạy trên port 3306
- Metabase JAR (metabase.jar)

### 1. Cài dependencies

```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt
```

### 2. Chạy toàn bộ ETL pipeline (một lệnh)

```powershell
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe etl\run_etl_pipeline.py
```

Pipeline sẽ chạy tự động:
- **Bước 0**: Setup MySQL databases
- **Bước 1**: Extract - đọc CSV, profiling
- **Bước 2**: Transform - làm sạch, xây dựng star schema
- **Bước 3**: Load Staging → `olist_staging`
- **Bước 4**: Load DWH → `olist_dwh`
- **Bước 5**: Data Quality - 24 automated checks

### 3. Kết nối Metabase

```powershell
java --add-opens java.base/java.nio=ALL-UNNAMED -jar metabase.jar
```

Truy cập http://localhost:3000. rồi:
Username: biadmin@gmail.com
Password: BI@12345678

---

## Kết quả ETL (đã verify)

```
24 checks | Pass: 23 | Warn: 1 | Fail: 0

Key metrics (delivered orders):
  Avg item price   : R$ 119.98
  Avg review score : 4.08 / 5.0
  Avg delivery time: 12.0 days
  On-time rate     : 92.1%
  Staging coverage : 99.2%

Top 3 categories by revenue:
  1. health_beauty         R$ 1,233,130
  2. watches_gifts         R$ 1,166,180
  3. bed_bath_table        R$ 1,023,440
```

---

## Analytical Queries

File `sql/03_analytical_queries.sql` chứa 8 nhóm query phân tích:
1. Executive KPIs
2. Top sản phẩm bán chạy (doanh thu & số lượng)
3. Doanh thu theo thời gian (tháng, quý, ngày trong tuần)
4. Phân tích địa lý theo bang
5. RFM Analysis (Champions, Loyal, At Risk, Lost...)
6. Vận hành & giao hàng
7. Seller performance ranking
8. Cohort Analysis
