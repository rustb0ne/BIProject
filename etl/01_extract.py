"""
etl/01_extract.py
Bước 1: Extract — Đọc raw CSV, validate và profiling dữ liệu.
Output: dict DataFrames + báo cáo profiling.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from tabulate import tabulate
from config import RAW_DATA_DIR, RAW_FILES, PROC_DATA_DIR
from logger import get_logger

log = get_logger("01_extract")

os.makedirs(PROC_DATA_DIR, exist_ok=True)

# Schema definitions (expected dtypes cho mỗi file)

SCHEMAS = {
    "orders": {
        "dtype": {
            "order_id": str, "customer_id": str, "order_status": str,
        },
        "parse_dates": [
            "order_purchase_timestamp", "order_approved_at",
            "order_delivered_carrier_date", "order_delivered_customer_date",
            "order_estimated_delivery_date"
        ]
    },
    "order_items": {
        "dtype": {
            "order_id": str, "order_item_id": int,
            "product_id": str, "seller_id": str,
            "price": float, "freight_value": float
        },
        "parse_dates": ["shipping_limit_date"]
    },
    "payments": {
        "dtype": {
            "order_id": str, "payment_sequential": int,
            "payment_type": str, "payment_installments": int,
            "payment_value": float
        },
        "parse_dates": []
    },
    "reviews": {
        "dtype": {
            "review_id": str, "order_id": str, "review_score": float,
            "review_comment_title": str, "review_comment_message": str
        },
        "parse_dates": ["review_creation_date", "review_answer_timestamp"]
    },
    "customers": {
        "dtype": {
            "customer_id": str, "customer_unique_id": str,
            "customer_zip_code_prefix": str, "customer_city": str,
            "customer_state": str
        },
        "parse_dates": []
    },
    "sellers": {
        "dtype": {
            "seller_id": str, "seller_zip_code_prefix": str,
            "seller_city": str, "seller_state": str
        },
        "parse_dates": []
    },
    "products": {
        "dtype": {
            "product_id": str, "product_category_name": str,
            "product_name_lenght": float, "product_description_lenght": float,
            "product_photos_qty": float, "product_weight_g": float,
            "product_length_cm": float, "product_height_cm": float,
            "product_width_cm": float
        },
        "parse_dates": []
    },
    "geolocation": {
        "dtype": {
            "geolocation_zip_code_prefix": str,
            "geolocation_lat": float, "geolocation_lng": float,
            "geolocation_city": str, "geolocation_state": str
        },
        "parse_dates": []
    },
    "translation": {
        "dtype": {
            "product_category_name": str,
            "product_category_name_english": str
        },
        "parse_dates": []
    },
}


def load_csv(key: str, sample_frac: float = None) -> pd.DataFrame:
    """Đọc một file CSV với schema đã định nghĩa."""
    filepath = os.path.join(RAW_DATA_DIR, RAW_FILES[key])
    schema   = SCHEMAS[key]

    log.info(f"Đọc: {RAW_FILES[key]}")
    df = pd.read_csv(
        filepath,
        dtype=schema["dtype"],
        parse_dates=schema.get("parse_dates", []),
        low_memory=False
    )

    if sample_frac and len(df) > 100_000:
        n_before = len(df)
        df = df.sample(frac=sample_frac, random_state=42).reset_index(drop=True)
        log.info(f"Sampling {sample_frac*100:.0f}%: {n_before:,} → {len(df):,} rows")

    return df


def profile_dataframe(name: str, df: pd.DataFrame) -> dict:
    """Tạo profiling report cho một DataFrame."""
    n_rows   = len(df)
    n_cols   = len(df.columns)
    null_counts = df.isnull().sum()
    null_pcts   = (null_counts / n_rows * 100).round(1)
    dup_count   = df.duplicated().sum()

    profile = {
        "name":       name,
        "rows":       n_rows,
        "cols":       n_cols,
        "duplicates": dup_count,
        "columns":    []
    }

    for col in df.columns:
        col_info = {
            "column":    col,
            "dtype":     str(df[col].dtype),
            "null_count": null_counts[col],
            "null_pct":  null_pcts[col],
            "unique":    df[col].nunique(),
        }
        # Thêm min/max cho numeric và date
        if pd.api.types.is_numeric_dtype(df[col]):
            col_info["min"] = df[col].min()
            col_info["max"] = df[col].max()
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            col_info["min"] = str(df[col].min())
            col_info["max"] = str(df[col].max())
        else:
            col_info["min"] = "-"
            col_info["max"] = "-"
        profile["columns"].append(col_info)

    return profile


def print_profile(profile: dict) -> None:
    """In profiling report đẹp ra console."""
    log.info(f"\n{'─'*70}")
    log.info(f"PROFILE: {profile['name'].upper()}")
    log.info(f"Rows: {profile['rows']:,}  |  Cols: {profile['cols']}  |  Duplicates: {profile['duplicates']:,}")
    log.info(f"{'─'*70}")

    rows = [(
        c["column"], c["dtype"],
        f"{c['null_count']:,} ({c['null_pct']}%)",
        f"{c['unique']:,}",
        c.get("min", "-"),
        c.get("max", "-")
    ) for c in profile["columns"]]

    print(tabulate(
        rows,
        headers=["Column", "Dtype", "Nulls", "Unique", "Min", "Max"],
        tablefmt="rounded_outline"
    ))


def validate_dataframe(name: str, df: pd.DataFrame) -> list[str]:
    """Thực hiện các kiểm tra validation cơ bản. Trả về list warnings."""
    warnings = []

    # Check empty
    if len(df) == 0:
        warnings.append(f"[{name}] EMPTY DATAFRAME!")
        return warnings

    # Check duplicates trên primary key
    pk_map = {
        "orders":      ["order_id"],
        "order_items": ["order_id", "order_item_id"],
        "payments":    ["order_id", "payment_sequential"],
        "reviews":     ["review_id"],
        "customers":   ["customer_id"],
        "sellers":     ["seller_id"],
        "products":    ["product_id"],
    }
    if name in pk_map:
        pk_cols = pk_map[name]
        available = [c for c in pk_cols if c in df.columns]
        if available:
            dups = df.duplicated(subset=available).sum()
            if dups > 0:
                warnings.append(f"[{name}] {dups} duplicate rows trên PK {available}")

    # Check negative values trong numeric measures
    for col in ["price", "freight_value", "payment_value", "review_score"]:
        if col in df.columns:
            neg = (df[col] < 0).sum()
            if neg > 0:
                warnings.append(f"[{name}] {neg} giá trị âm trong cột '{col}'")

    # Check review score range
    if "review_score" in df.columns:
        invalid = df["review_score"].notna() & ~df["review_score"].between(1, 5)
        if invalid.sum() > 0:
            warnings.append(f"[{name}] {invalid.sum()} review_score ngoài phạm vi 1-5")

    return warnings


def extract_all(geolocation_sample_frac: float = 0.2) -> dict:
    """
    Extract toàn bộ raw data.
    Trả về dict {key: DataFrame}.
    """
    log.info("=" * 60)
    log.info("BƯỚC 1: EXTRACT - Đọc và validate raw data")
    log.info("=" * 60)

    dfs = {}
    all_warnings = []
    profile_summary = []

    keys_to_load = list(SCHEMAS.keys())

    for key in keys_to_load:
        try:
            sample_frac = geolocation_sample_frac if key == "geolocation" else None
            df = load_csv(key, sample_frac=sample_frac)
            dfs[key] = df

            # Profile
            profile = profile_dataframe(key, df)
            print_profile(profile)
            profile_summary.append({
                "Dataset": key,
                "Rows": f"{profile['rows']:,}",
                "Cols": profile['cols'],
                "Duplicates": profile['duplicates'],
                "Null cols": sum(1 for c in profile["columns"] if c["null_count"] > 0)
            })

            # Validate
            warns = validate_dataframe(key, df)
            all_warnings.extend(warns)
            if warns:
                for w in warns:
                    log.warning(f"{w}")
            else:
                log.info(f"Validation passed")

        except Exception as e:
            log.error(f"Lỗi khi đọc {key}: {e}")
            raise

    # Summary table
    log.info(f"\n{'='*60}")
    log.info("TÓM TẮT EXTRACT")
    log.info("="*60)
    print(tabulate(profile_summary, headers="keys", tablefmt="rounded_outline"))

    if all_warnings:
        log.warning(f"\nTổng {len(all_warnings)} cảnh báo:")
        for w in all_warnings:
            log.warning(f"- {w}")
    else:
        log.info("\nKhông có cảnh báo validation")

    log.info("\n [BƯỚC 1 HOÀN THÀNH]")
    return dfs


if __name__ == "__main__":
    dfs = extract_all()
    log.info(f"Loaded {len(dfs)} datasets")
