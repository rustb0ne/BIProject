"""
etl/config.py
Cấu hình tập trung cho toàn bộ ETL pipeline.
"""

import os

# Database connections
DB_HOST     = "127.0.0.1"
DB_PORT     = 3306
DB_USER     = "root"
DB_PASSWORD = ""

STAGING_DB  = "olist_staging"
DWH_DB      = "olist_dwh"

STAGING_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{STAGING_DB}?charset=utf8mb4"
DWH_URI     = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DWH_DB}?charset=utf8mb4"
MYSQL_URI   = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/?charset=utf8mb4"

# File paths 
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR  = os.path.join(BASE_DIR, "data", "raw")
PROC_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
SQL_DIR       = os.path.join(BASE_DIR, "sql")
LOG_DIR       = os.path.join(BASE_DIR, "logs")

# Raw files mapping
RAW_FILES = {
    "orders":       "olist_orders_dataset.csv",
    "order_items":  "olist_order_items_dataset.csv",
    "payments":     "olist_order_payments_dataset.csv",
    "reviews":      "olist_order_reviews_dataset.csv",
    "customers":    "olist_customers_dataset.csv",
    "sellers":      "olist_sellers_dataset.csv",
    "products":     "olist_products_dataset.csv",
    "geolocation":  "olist_geolocation_dataset.csv",
    "translation":  "product_category_name_translation.csv",
}

# ETL settings
CHUNK_SIZE      = 5000
GEOLOCATION_SAMPLE_FRAC = 0.2   # sample 20% of 1M geolocation rows

# Brazil state reference
BRAZIL_STATES = {
    "AC": ("Acre",                "Norte"),
    "AL": ("Alagoas",             "Nordeste"),
    "AP": ("Amapá",               "Norte"),
    "AM": ("Amazonas",            "Norte"),
    "BA": ("Bahia",               "Nordeste"),
    "CE": ("Ceará",               "Nordeste"),
    "DF": ("Distrito Federal",    "Centro-Oeste"),
    "ES": ("Espírito Santo",      "Sudeste"),
    "GO": ("Goiás",               "Centro-Oeste"),
    "MA": ("Maranhão",            "Nordeste"),
    "MT": ("Mato Grosso",         "Centro-Oeste"),
    "MS": ("Mato Grosso do Sul",  "Centro-Oeste"),
    "MG": ("Minas Gerais",        "Sudeste"),
    "PA": ("Pará",                "Norte"),
    "PB": ("Paraíba",             "Nordeste"),
    "PR": ("Paraná",              "Sul"),
    "PE": ("Pernambuco",          "Nordeste"),
    "PI": ("Piauí",               "Nordeste"),
    "RJ": ("Rio de Janeiro",      "Sudeste"),
    "RN": ("Rio Grande do Norte", "Nordeste"),
    "RS": ("Rio Grande do Sul",   "Sul"),
    "RO": ("Rondônia",            "Norte"),
    "RR": ("Roraima",             "Norte"),
    "SC": ("Santa Catarina",      "Sul"),
    "SP": ("São Paulo",           "Sudeste"),
    "SE": ("Sergipe",             "Nordeste"),
    "TO": ("Tocantins",           "Norte"),
}
