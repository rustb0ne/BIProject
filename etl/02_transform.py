"""
etl/02_transform.py
Bước 2: Transform — Làm sạch, chuẩn hóa, tính toán business metrics,
và tạo toàn bộ dimension + fact DataFrames cho star schema.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import timedelta
from config import BRAZIL_STATES
from logger import get_logger

log = get_logger("02_transform")

# HELPER FUNCTIONS

def _log_step(step: str, before: int, after: int, reason: str = ""):
    removed = before - after
    if removed > 0:
        suffix = f" ({reason})" if reason else ""
        log.info(f"Loại bỏ {removed:,} rows{suffix}: {before:,} → {after:,}")
    else:
        log.info(f"Giữ nguyên {after:,} rows")


def clean_city_name(series: pd.Series) -> pd.Series:
    """Chuẩn hóa tên thành phố: lowercase → title case, strip."""
    return series.astype(str).str.strip().str.lower().str.title()


def safe_int(series: pd.Series) -> pd.Series:
    """Convert float cột sang Int64 (nullable int)."""
    return series.fillna(0).astype(int)


# DIMENSION TRANSFORMATIONS

def build_dim_time(orders_df: pd.DataFrame) -> pd.DataFrame:
    """
    Xây dựng bảng dim_time — mỗi ngày 1 dòng.
    Phạm vi: từ ngày đầu tiên đến ngày cuối cùng trong dataset.
    """
    log.info("[dim_time] Tạo calendar dimension...")

    # Lấy phạm vi ngày từ orders
    all_dates = pd.concat([
        orders_df["order_purchase_timestamp"].dropna(),
        orders_df["order_delivered_customer_date"].dropna(),
        orders_df["order_estimated_delivery_date"].dropna(),
    ])
    min_date = all_dates.min().date()
    max_date = all_dates.max().date()

    log.info(f"Phạm vi: {min_date} → {max_date}")

    # Tạo tất cả ngày trong phạm vi
    date_range = pd.date_range(start=min_date, end=max_date, freq="D")

    MONTH_NAMES = ["January","February","March","April","May","June",
                   "July","August","September","October","November","December"]
    DAY_NAMES   = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

    records = []
    for d in date_range:
        records.append({
            "time_key":      int(d.strftime("%Y%m%d")),
            "full_date":     d.date(),
            "year":          d.year,
            "quarter":       d.quarter,
            "month":         d.month,
            "month_name":    MONTH_NAMES[d.month - 1],
            "week_of_year":  d.isocalendar().week,
            "day_of_month":  d.day,
            "day_of_week":   d.dayofweek + 1,   # 1=Mon ... 7=Sun
            "day_name":      DAY_NAMES[d.dayofweek],
            "is_weekend":    d.dayofweek >= 5,
        })

    dim_time = pd.DataFrame(records)
    log.info(f"{len(dim_time):,} ngày trong dim_time")
    return dim_time


def build_dim_customer(customers_df: pd.DataFrame) -> pd.DataFrame:
    """Xây dựng dim_customer với surrogate key."""
    log.info("[dim_customer] Làm sạch dữ liệu khách hàng...")
    df = customers_df.copy()

    # Chuẩn hóa tên thành phố
    df["customer_city"] = clean_city_name(df["customer_city"])

    # Chuẩn hóa state code
    df["customer_state"] = df["customer_state"].astype(str).str.strip().str.upper()

    # Loại bỏ duplicates trên customer_id (giữ first)
    n_before = len(df)
    df = df.drop_duplicates(subset=["customer_id"]).reset_index(drop=True)
    _log_step("customer dedup", n_before, len(df), "duplicate customer_id")

    # Surrogate key
    df.insert(0, "customer_key", range(1, len(df) + 1))

    log.info(f"{len(df):,} unique customers")
    return df[["customer_key", "customer_id", "customer_unique_id",
               "customer_zip_code_prefix", "customer_city", "customer_state"]]


def build_dim_product(products_df: pd.DataFrame, translation_df: pd.DataFrame) -> pd.DataFrame:
    """Xây dựng dim_product với tên category tiếng Anh."""
    log.info("[dim_product] Làm sạch dữ liệu sản phẩm...")
    df = products_df.copy()

    # Merge với bảng translation
    df = df.merge(translation_df, on="product_category_name", how="left")

    # Fill NULL category
    df["product_category_name"] = df["product_category_name"].fillna("unknown")
    df["product_category_name_english"] = df["product_category_name_english"].fillna(
        df["product_category_name"]
    )

    # Convert dimensions sang int (bỏ NaN → 0)
    for col in ["product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]:
        df[col] = safe_int(df[col].fillna(0))

    # Loại bỏ duplicates trên product_id
    n_before = len(df)
    df = df.drop_duplicates(subset=["product_id"]).reset_index(drop=True)
    _log_step("product dedup", n_before, len(df), "duplicate product_id")

    # Surrogate key
    df.insert(0, "product_key", range(1, len(df) + 1))

    log.info(f"{len(df):,} unique products, "
             f"{df['product_category_name_english'].nunique()} categories")
    return df[["product_key", "product_id", "product_category_name",
               "product_category_name_english", "product_weight_g",
               "product_length_cm", "product_height_cm", "product_width_cm"]]


def build_dim_region() -> pd.DataFrame:
    """Xây dựng dim_region từ reference data Brazil states."""
    log.info("[dim_region] Tạo Brazil region dimension...")
    records = []
    for i, (code, (name, macro)) in enumerate(BRAZIL_STATES.items(), 1):
        records.append({
            "region_key":   i,
            "state_code":   code,
            "state_name":   name,
            "macro_region": macro,
        })
    df = pd.DataFrame(records)
    log.info(f"{len(df)} states, {df['macro_region'].nunique()} macro regions")
    return df


def build_dim_seller(sellers_df: pd.DataFrame) -> pd.DataFrame:
    """Xây dựng dim_seller với surrogate key."""
    log.info("[dim_seller] Làm sạch dữ liệu người bán...")
    df = sellers_df.copy()

    df["seller_city"]  = clean_city_name(df["seller_city"])
    df["seller_state"] = df["seller_state"].astype(str).str.strip().str.upper()

    n_before = len(df)
    df = df.drop_duplicates(subset=["seller_id"]).reset_index(drop=True)
    _log_step("seller dedup", n_before, len(df), "duplicate seller_id")

    df.insert(0, "seller_key", range(1, len(df) + 1))

    log.info(f"{len(df):,} unique sellers")
    return df[["seller_key", "seller_id", "seller_zip_code_prefix",
               "seller_city", "seller_state"]]

# FACT TABLE TRANSFORMATION

def build_fact_orders(
    orders_df: pd.DataFrame,
    order_items_df: pd.DataFrame,
    payments_df: pd.DataFrame,
    reviews_df: pd.DataFrame,
    dim_customer: pd.DataFrame,
    dim_product: pd.DataFrame,
    dim_seller: pd.DataFrame,
    dim_time: pd.DataFrame,
    dim_region: pd.DataFrame,
) -> pd.DataFrame:
    """
    Xây dựng fact_orders: grain = 1 row per order item.
    """
    log.info("[fact_orders] Bắt đầu build fact table...")

    # 1. Base: order_items JOIN orders────────────────────────
    log.info("Join order_items + orders...")
    fact = order_items_df.merge(
        orders_df[[
            "order_id", "customer_id", "order_status",
            "order_purchase_timestamp", "order_delivered_customer_date",
            "order_estimated_delivery_date"
        ]],
        on="order_id", how="inner"
    )
    log.info(f"{len(fact):,} rows sau join orders")

    # 2. Aggregate payments theo order
    log.info("Aggregate payments...")
    pay_agg = payments_df.sort_values("payment_sequential").groupby("order_id").agg(
        payment_value        = ("payment_value", "sum"),
        payment_type         = ("payment_type", "first"),      # phương thức đầu tiên
        payment_installments = ("payment_installments", "max") # số kỳ cao nhất
    ).reset_index()

    fact = fact.merge(pay_agg, on="order_id", how="left")
    log.info(f"Sau merge payments: {fact['payment_value'].notna().sum():,} orders có payment data")

    # 3. Lấy review score (1 đơn → 1 review)
    log.info("Merge review scores...")
    rev = reviews_df.drop_duplicates(subset=["order_id"])[["order_id", "review_score"]]
    fact = fact.merge(rev, on="order_id", how="left")

    # 4. Tính toán delivery metrics
    log.info("Tính delivery metrics...")
    fact["delivery_days"] = (
        fact["order_delivered_customer_date"] - fact["order_purchase_timestamp"]
    ).dt.days

    fact["estimated_delivery_days"] = (
        fact["order_estimated_delivery_date"] - fact["order_purchase_timestamp"]
    ).dt.days

    fact["delay_days"] = (
        fact["order_delivered_customer_date"] - fact["order_estimated_delivery_date"]
    ).dt.days

    fact["is_on_time"] = (
        fact["order_delivered_customer_date"] <= fact["order_estimated_delivery_date"]
    )
    # is_on_time = None nếu chưa delivered
    mask_not_delivered = fact["order_delivered_customer_date"].isna()
    fact.loc[mask_not_delivered, "is_on_time"]    = None
    fact.loc[mask_not_delivered, "delivery_days"] = None
    fact.loc[mask_not_delivered, "delay_days"]    = None

    # 5. Tính total_revenue
    fact["total_revenue"] = fact["price"] + fact["freight_value"]

    # 6. Lookup surrogate keys từ dimensions
    log.info("Lookup surrogate keys từ dimensions...")

    # Customer key
    cust_map = dim_customer.set_index("customer_id")["customer_key"]
    fact["customer_key"] = fact["customer_id"].map(cust_map)

    # Product key
    prod_map = dim_product.set_index("product_id")["product_key"]
    fact["product_key"] = fact["product_id"].map(prod_map)

    # Seller key
    sell_map = dim_seller.set_index("seller_id")["seller_key"]
    fact["seller_key"] = fact["seller_id"].map(sell_map)

    # Purchase time key (YYYYMMDD int)
    fact["purchase_time_key"] = (
        fact["order_purchase_timestamp"].dt.strftime("%Y%m%d")
        .astype("Int64")
    )

    # Delivery time key
    fact["delivery_time_key"] = (
        fact["order_delivered_customer_date"].dt.strftime("%Y%m%d")
        .astype("Int64")
    )

    # Region keys — cần customer state và seller state
    # Merge customer state
    cust_state = dim_customer[["customer_key", "customer_state"]].copy()
    fact = fact.merge(cust_state.rename(columns={"customer_state": "_cust_state"}),
                      on="customer_key", how="left")

    # Merge seller state
    sell_state = dim_seller[["seller_key", "seller_state"]].copy()
    fact = fact.merge(sell_state.rename(columns={"seller_state": "_sell_state"}),
                      on="seller_key", how="left")

    # Map region key
    region_map = dim_region.set_index("state_code")["region_key"]
    fact["customer_region_key"] = fact["_cust_state"].map(region_map)
    fact["seller_region_key"]   = fact["_sell_state"].map(region_map)

    # 7. Loại bỏ rows không có key bắt buộc
    required_keys = ["customer_key", "product_key", "seller_key",
                     "purchase_time_key", "customer_region_key"]
    n_before = len(fact)
    fact = fact.dropna(subset=required_keys)
    _log_step("fact required keys", n_before, len(fact), "thiếu surrogate key bắt buộc")

    # 8. Type conversions
    int_cols = ["customer_key", "product_key", "seller_key",
                "purchase_time_key", "customer_region_key"]
    for col in int_cols:
        fact[col] = fact[col].astype(int)

    nullable_int_cols = ["delivery_time_key", "seller_region_key",
                         "delivery_days", "estimated_delivery_days", "delay_days",
                         "payment_installments", "review_score"]
    for col in nullable_int_cols:
        if col in fact.columns:
            fact[col] = fact[col].astype("Int64")

    # 9. Chọn và sắp xếp columns cuối cùng
    final_cols = [
        "order_id", "order_item_id",
        "customer_key", "product_key", "seller_key",
        "purchase_time_key", "delivery_time_key",
        "customer_region_key", "seller_region_key",
        "price", "freight_value", "total_revenue",
        "payment_value", "payment_installments",
        "review_score",
        "delivery_days", "estimated_delivery_days", "delay_days", "is_on_time",
        "order_status", "payment_type",
    ]
    fact = fact[final_cols].reset_index(drop=True)

    # 10. Thống kê cuối
    log.info(f"fact_orders: {len(fact):,} rows")
    log.info(f"Orders: {fact['order_id'].nunique():,}")
    log.info(f"Delivered: {(fact['order_status']=='delivered').sum():,}")
    log.info(f"Total revenue: R$ {fact['price'].sum():,.2f}")
    log.info(f"Avg price: R$ {fact['price'].mean():.2f}")
    log.info(f"Avg review: {fact['review_score'].mean():.2f}")
    log.info(f"Avg delivery: {fact['delivery_days'].mean():.1f} days")

    return fact

# MAIN TRANSFORM FUNCTION

def transform_all(dfs: dict) -> dict:
    """
    Nhận dict raw DataFrames → Trả về dict transformed DataFrames.
    Keys: dim_time, dim_customer, dim_product, dim_region, dim_seller, fact_orders
    """
    log.info("=" * 60)
    log.info("BƯỚC 2: TRANSFORM - Làm sạch và xây dựng star schema")
    log.info("=" * 60)

    result = {}

    # Build Dimensions
    log.info("\n [DIMENSION TABLES]")

    result["dim_time"]     = build_dim_time(dfs["orders"])
    result["dim_customer"] = build_dim_customer(dfs["customers"])
    result["dim_product"]  = build_dim_product(dfs["products"], dfs["translation"])
    result["dim_region"]   = build_dim_region()
    result["dim_seller"]   = build_dim_seller(dfs["sellers"])

    # Build Fact Table 
    log.info("\n [FACT TABLE]")

    result["fact_orders"] = build_fact_orders(
        orders_df      = dfs["orders"],
        order_items_df = dfs["order_items"],
        payments_df    = dfs["payments"],
        reviews_df     = dfs["reviews"],
        dim_customer   = result["dim_customer"],
        dim_product    = result["dim_product"],
        dim_seller     = result["dim_seller"],
        dim_time       = result["dim_time"],
        dim_region     = result["dim_region"],
    )

    # Summary 
    log.info("\n [TRANSFORM SUMMARY]")
    from tabulate import tabulate
    summary = [(k, f"{len(v):,}", len(v.columns)) for k, v in result.items()]
    print(tabulate(summary, headers=["Table", "Rows", "Cols"], tablefmt="rounded_outline"))

    log.info("\n[BƯỚC 2 HOÀN THÀNH]")
    return result


if __name__ == "__main__":
    from etl.extract import extract_all
    dfs = extract_all()
    transformed = transform_all(dfs)
