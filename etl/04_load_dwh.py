"""
etl/04_load_dwh.py
Bước 4: Load transformed DataFrames vào Data Warehouse (star schema).
Thứ tự: Dimensions trước → Fact table sau (đảm bảo FK integrity).
Sử dụng INSERT IGNORE để idempotent (có thể chạy lại an toàn).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from tqdm import tqdm
from config import DWH_URI, CHUNK_SIZE
from logger import get_logger

log = get_logger("04_load_dwh")


def upsert_table(engine, df: pd.DataFrame, table_name: str,
                 chunk_size: int = CHUNK_SIZE) -> int:
    """
    Load DataFrame vào DWH table.
    - Lần đầu: TRUNCATE rồi INSERT
    - Idempotent: an toàn khi chạy lại
    """
    total_rows = len(df)
    log.info(f"Loading {table_name}: {total_rows:,} rows")

    # Replace NaN với None để MySQL nhận NULL đúng
    df_clean = df.where(pd.notnull(df), None)

    # Truncate trước khi load (đảm bảo clean slate)
    with engine.connect() as conn:
        conn.execute(text(f"SET FOREIGN_KEY_CHECKS = 0"))
        conn.execute(text(f"TRUNCATE TABLE {table_name}"))
        conn.execute(text(f"SET FOREIGN_KEY_CHECKS = 1"))
        conn.commit()

    rows_loaded = 0
    with tqdm(total=total_rows, desc=f"  {table_name}",
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}]") as pbar:
        for i in range(0, total_rows, chunk_size):
            chunk = df_clean.iloc[i: i + chunk_size].copy()
            chunk.to_sql(
                name=table_name,
                con=engine,
                if_exists="append",
                index=False,
                method="multi"
            )
            rows_loaded += len(chunk)
            pbar.update(len(chunk))

    log.info(f"{rows_loaded:,} rows → {table_name}")
    return rows_loaded


def prepare_dim_time_for_db(df: pd.DataFrame) -> pd.DataFrame:
    """Convert full_date sang string cho MySQL."""
    df = df.copy()
    df["full_date"] = df["full_date"].astype(str)
    df["is_weekend"] = df["is_weekend"].astype(int)
    return df


def prepare_fact_for_db(df: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn bị fact_orders cho database load."""
    df = df.copy()

    # Convert pandas Int64 (nullable) sang Python int/None
    nullable_int_cols = [
        "delivery_time_key", "seller_region_key",
        "delivery_days", "estimated_delivery_days", "delay_days",
        "payment_installments", "review_score"
    ]
    for col in nullable_int_cols:
        if col in df.columns:
            df[col] = df[col].astype(object).where(df[col].notna(), None)

    # Convert is_on_time (bool/None) → tinyint
    df["is_on_time"] = df["is_on_time"].map(
        lambda x: 1 if x is True else (0 if x is False else None)
    )

    # Đảm bảo price và freight không null
    df["price"]         = df["price"].fillna(0.0)
    df["freight_value"] = df["freight_value"].fillna(0.0)
    df["total_revenue"] = df["total_revenue"].fillna(0.0)

    return df


def load_dwh(transformed: dict) -> None:
    """Main function: load tất cả DWH tables theo đúng thứ tự."""
    log.info("=" * 60)
    log.info("BƯỚC 4: LOAD DATA WAREHOUSE")
    log.info("=" * 60)

    engine = create_engine(
        DWH_URI, echo=False,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={"connect_timeout": 60}
    )

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    log.info("Kết nối olist_dwh thành công")

    total_loaded = 0

    # 1. DIM_TIME
    log.info("\n[1/5] dim_time")
    dt = prepare_dim_time_for_db(transformed["dim_time"])
    total_loaded += upsert_table(engine, dt, "dim_time")

    # 2. DIM_REGION
    log.info("\n[2/5] dim_region")
    total_loaded += upsert_table(engine, transformed["dim_region"], "dim_region")

    # 3. DIM_CUSTOMER
    log.info("\n[3/5] dim_customer")
    dc = transformed["dim_customer"].copy()
    total_loaded += upsert_table(engine, dc, "dim_customer")

    # 4. DIM_PRODUCT
    log.info("\n[4/5] dim_product")
    dp = transformed["dim_product"].copy()
    total_loaded += upsert_table(engine, dp, "dim_product")

    # 5. DIM_SELLER
    log.info("\n[5/5] dim_seller")
    ds = transformed["dim_seller"].copy()
    total_loaded += upsert_table(engine, ds, "dim_seller")

    # 6. FACT_ORDERS
    log.info("\n[FACT] fact_orders")
    fact = prepare_fact_for_db(transformed["fact_orders"])
    total_loaded += upsert_table(engine, fact, "fact_orders", chunk_size=2000)

    engine.dispose()

    # Verify row counts
    log.info("\nVERIFY ROW COUNTS")
    engine_verify = create_engine(DWH_URI, echo=False)
    tables = ["dim_time", "dim_region", "dim_customer",
              "dim_product", "dim_seller", "fact_orders"]
    with engine_verify.connect() as conn:
        from tabulate import tabulate
        rows_info = []
        for t in tables:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).fetchone()[0]
            rows_info.append([t, f"{count:,}"])
        print(tabulate(rows_info, headers=["Table", "Rows"], tablefmt="rounded_outline"))
    engine_verify.dispose()

    log.info(f"\nTổng cộng: {total_loaded:,} rows loaded vào DWH")
    log.info("[BƯỚC 4 HOÀN THÀNH]")


if __name__ == "__main__":
    from etl.extract import extract_all
    from etl.transform import transform_all
    dfs = extract_all()
    transformed = transform_all(dfs)
    load_dwh(transformed)
