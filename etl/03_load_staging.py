"""
etl/03_load_staging.py
Bước 3: Load raw data (sau basic cleaning) vào olist_staging MySQL.
Sử dụng bulk insert theo chunk để xử lý file lớn hiệu quả.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from sqlalchemy import create_engine, text
from tqdm import tqdm
from config import STAGING_URI, CHUNK_SIZE, GEOLOCATION_SAMPLE_FRAC
from logger import get_logger

log = get_logger("03_load_staging")


def load_table(engine, df: pd.DataFrame, table_name: str,
               if_exists: str = "replace", chunk_size: int = CHUNK_SIZE) -> int:
    """
    Load DataFrame vào MySQL table theo chunks.
    Trả về số rows đã insert.
    """
    total_rows = len(df)
    log.info(f"Loading {table_name}: {total_rows:,} rows → chunk_size={chunk_size}")

    # Xóa bảng cũ và insert mới
    with engine.connect() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table_name}"))
        conn.commit()

    n_chunks = (total_rows // chunk_size) + 1
    rows_loaded = 0

    with tqdm(total=total_rows, desc=f"  {table_name}", unit="rows",
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}]") as pbar:
        for i in range(0, total_rows, chunk_size):
            chunk = df.iloc[i: i + chunk_size]
            chunk.to_sql(
                name=table_name,
                con=engine,
                if_exists="append",
                index=False,
                method="multi"
            )
            rows_loaded += len(chunk)
            pbar.update(len(chunk))

    log.info(f"{rows_loaded:,} rows loaded vào {table_name}")
    return rows_loaded


def prepare_staging_dfs(dfs: dict) -> dict:
    """
    Chuẩn bị DataFrames cho staging — thêm cột _etl_loaded_at,
    chọn đúng columns theo schema staging.
    """
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    staging = {}

    # stg_orders
    df = dfs["orders"].copy()
    df["_etl_loaded_at"] = now
    # Convert datetime columns
    for col in ["order_purchase_timestamp", "order_approved_at",
                "order_delivered_carrier_date", "order_delivered_customer_date",
                "order_estimated_delivery_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
            df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S").where(df[col].notna(), None)
    # Drop duplicates on PK
    df = df.drop_duplicates(subset=["order_id"])
    staging["stg_orders"] = df

    # stg_order_items
    df = dfs["order_items"].copy()
    df["_etl_loaded_at"] = now
    df["shipping_limit_date"] = pd.to_datetime(df["shipping_limit_date"], errors="coerce")
    df["shipping_limit_date"] = df["shipping_limit_date"].dt.strftime("%Y-%m-%d %H:%M:%S").where(
        df["shipping_limit_date"].notna(), None)
    df = df.drop_duplicates(subset=["order_id", "order_item_id"])
    staging["stg_order_items"] = df

    # stg_order_payments
    df = dfs["payments"].copy()
    df["_etl_loaded_at"] = now
    df = df.drop_duplicates(subset=["order_id", "payment_sequential"])
    staging["stg_order_payments"] = df

    # stg_order_reviews
    df = dfs["reviews"].copy()
    df["_etl_loaded_at"] = now
    for col in ["review_creation_date", "review_answer_timestamp"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
            df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S").where(df[col].notna(), None)
    df = df.drop_duplicates(subset=["review_id"])
    # Fill NaN string columns
    for col in ["review_comment_title", "review_comment_message"]:
        df[col] = df[col].where(df[col].notna(), None)
    staging["stg_order_reviews"] = df

    # stg_customers
    df = dfs["customers"].copy()
    df["_etl_loaded_at"] = now
    df = df.drop_duplicates(subset=["customer_id"])
    staging["stg_customers"] = df

    # stg_sellers
    df = dfs["sellers"].copy()
    df["_etl_loaded_at"] = now
    df = df.drop_duplicates(subset=["seller_id"])
    staging["stg_sellers"] = df

    # stg_products — merge translation
    df = dfs["products"].copy()
    trans = dfs["translation"].copy()
    df = df.merge(trans, on="product_category_name", how="left")
    df["product_category_name_english"] = df.get("product_category_name_english", pd.Series())
    df["product_category_name"] = df["product_category_name"].fillna("unknown")
    df["product_category_name_english"] = df["product_category_name_english"].fillna(
        df["product_category_name"])
    # Numeric cols
    for col in ["product_name_lenght", "product_description_lenght", "product_photos_qty",
                "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    df["_etl_loaded_at"] = now
    df = df.drop_duplicates(subset=["product_id"])
    staging["stg_products"] = df[[
        "product_id", "product_category_name", "product_category_name_english",
        "product_name_lenght", "product_description_lenght", "product_photos_qty",
        "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm",
        "_etl_loaded_at"
    ]]

    # stg_geolocation (sample)
    df = dfs["geolocation"].copy()
    df["_etl_loaded_at"] = now
    staging["stg_geolocation"] = df

    return staging


def load_staging(dfs: dict) -> None:
    """Main function: load tất cả staging tables."""
    log.info("=" * 60)
    log.info("BƯỚC 3: LOAD STAGING")
    log.info("=" * 60)

    engine = create_engine(STAGING_URI, echo=False,
                           pool_pre_ping=True,
                           connect_args={"connect_timeout": 30})

    # Verify connection
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    log.info("Kết nối olist_staging thành công")

    # Chuẩn bị DataFrames
    log.info("Chuẩn bị staging DataFrames...")
    staging_dfs = prepare_staging_dfs(dfs)

    # Load từng bảng
    total_loaded = 0
    for table_name, df in staging_dfs.items():
        rows = load_table(engine, df, table_name)
        total_loaded += rows

    engine.dispose()

    log.info(f"\nTổng cộng: {total_loaded:,} rows loaded vào staging")
    log.info("[BƯỚC 3 HOÀN THÀNH]")


if __name__ == "__main__":
    from etl.extract import extract_all
    dfs = extract_all()
    load_staging(dfs)
