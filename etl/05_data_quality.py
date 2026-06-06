"""
etl/05_data_quality.py
Bước 5: Data Quality Checks — kiểm tra toàn diện dữ liệu trong DWH.
Các kiểm tra bao gồm:
  - Row count checks
  - Null checks trên measures bắt buộc
  - Referential integrity (orphan FK)
  - Business rule validation
  - Thống kê phân phối measures
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from sqlalchemy import create_engine, text
from tabulate import tabulate
from config import DWH_URI, STAGING_URI
from logger import get_logger

log = get_logger("05_data_quality")


class DataQualityChecker:
    """Lớp thực hiện toàn bộ data quality checks."""

    def __init__(self, dwh_engine, staging_engine):
        self.dwh     = dwh_engine
        self.staging = staging_engine
        self.results = []   # [(check_name, status, detail)]
        self.errors  = 0
        self.warnings = 0

    def _query_dwh(self, sql: str) -> pd.DataFrame:
        with self.dwh.connect() as conn:
            return pd.read_sql(text(sql), conn)

    def _query_staging(self, sql: str) -> pd.DataFrame:
        with self.staging.connect() as conn:
            return pd.read_sql(text(sql), conn)

    def _add_result(self, name: str, passed: bool, detail: str, is_warning: bool = False):
        status = "PASS" if passed else ("WARN" if is_warning else "FAIL")
        self.results.append((name, status, detail))
        if not passed:
            if is_warning:
                self.warnings += 1
                log.warning(f"  {status}  {name}: {detail}")
            else:
                self.errors += 1
                log.error(f"  {status}  {name}: {detail}")
        else:
            log.info(f"  {status}  {name}: {detail}")

    # CHECK 1: Row counts
    def check_row_counts(self):
        log.info("\n[CHECK 1] Row Count Checks")
        tables_min = {
            "dim_time":     500,
            "dim_region":   27,
            "dim_customer": 90_000,
            "dim_product":  30_000,
            "dim_seller":   3_000,
            "fact_orders":  100_000,
        }
        for table, min_rows in tables_min.items():
            df = self._query_dwh(f"SELECT COUNT(*) AS cnt FROM {table}")
            cnt = df["cnt"].iloc[0]
            passed = cnt >= min_rows
            self._add_result(
                f"row_count_{table}",
                passed,
                f"{cnt:,} rows (min expected: {min_rows:,})"
            )

    # CHECK 2: Staging vs DWH consistency
    def check_staging_vs_dwh(self):
        log.info("\n[CHECK 2] Staging vs DWH Consistency")

        # Orders: staging orders → fact_orders
        stg_orders = self._query_staging(
            "SELECT COUNT(DISTINCT order_id) AS cnt FROM stg_orders")["cnt"].iloc[0]
        dwh_orders = self._query_dwh(
            "SELECT COUNT(DISTINCT order_id) AS cnt FROM fact_orders")["cnt"].iloc[0]
        pct_match = dwh_orders / stg_orders * 100 if stg_orders > 0 else 0
        passed = pct_match >= 90  # Chấp nhận 10% loss (cancelled orders, etc.)
        self._add_result(
            "staging_vs_dwh_orders",
            passed,
            f"Staging: {stg_orders:,} | DWH: {dwh_orders:,} | Match: {pct_match:.1f}%",
            is_warning=not passed
        )

        # Customers: staging → dim_customer
        stg_cust = self._query_staging(
            "SELECT COUNT(*) AS cnt FROM stg_customers")["cnt"].iloc[0]
        dwh_cust = self._query_dwh(
            "SELECT COUNT(*) AS cnt FROM dim_customer")["cnt"].iloc[0]
        passed = abs(stg_cust - dwh_cust) <= 100
        self._add_result(
            "staging_vs_dwh_customers",
            passed,
            f"Staging: {stg_cust:,} | DWH: {dwh_cust:,}"
        )

    # CHECK 3: Null checks trên measures bắt buộc
    def check_null_measures(self):
        log.info("\n[CHECK 3] Null Checks trên Measures Bắt Buộc")
        checks = [
            ("fact_orders", "price",         "price IS NULL OR price < 0"),
            ("fact_orders", "freight_value",  "freight_value IS NULL"),
            ("fact_orders", "total_revenue",  "total_revenue IS NULL OR total_revenue < 0"),
            ("fact_orders", "customer_key",   "customer_key IS NULL"),
            ("fact_orders", "product_key",    "product_key IS NULL"),
            ("fact_orders", "purchase_time_key", "purchase_time_key IS NULL"),
        ]
        for table, col, condition in checks:
            df = self._query_dwh(f"SELECT COUNT(*) AS cnt FROM {table} WHERE {condition}")
            cnt = df["cnt"].iloc[0]
            passed = cnt == 0
            self._add_result(
                f"null_check_{col}",
                passed,
                f"{cnt:,} rows với điều kiện: {condition}"
            )

    # CHECK 4: Referential integrity
    def check_referential_integrity(self):
        log.info("\n[CHECK 4] Referential Integrity Checks")
        fk_checks = [
            ("fact_orders f LEFT JOIN dim_customer c ON f.customer_key = c.customer_key",
             "c.customer_key IS NULL", "orphan customer_key"),
            ("fact_orders f LEFT JOIN dim_product p ON f.product_key = p.product_key",
             "p.product_key IS NULL", "orphan product_key"),
            ("fact_orders f LEFT JOIN dim_seller s ON f.seller_key = s.seller_key",
             "s.seller_key IS NULL", "orphan seller_key"),
            ("fact_orders f LEFT JOIN dim_time t ON f.purchase_time_key = t.time_key",
             "t.time_key IS NULL", "orphan purchase_time_key"),
            ("fact_orders f LEFT JOIN dim_region r ON f.customer_region_key = r.region_key",
             "r.region_key IS NULL", "orphan customer_region_key"),
        ]
        for join_clause, where_clause, desc in fk_checks:
            sql = f"SELECT COUNT(*) AS cnt FROM {join_clause} WHERE {where_clause}"
            cnt = self._query_dwh(sql)["cnt"].iloc[0]
            passed = cnt == 0
            self._add_result(f"fk_{desc.replace(' ', '_')}", passed,
                             f"{cnt:,} orphan records")

    # CHECK 5: Business rules
    def check_business_rules(self):
        log.info("\n[CHECK 5] Business Rule Validation")

        # Review score phải từ 1-5
        df = self._query_dwh(
            "SELECT COUNT(*) AS cnt FROM fact_orders "
            "WHERE review_score IS NOT NULL AND review_score NOT BETWEEN 1 AND 5")
        cnt = df["cnt"].iloc[0]
        self._add_result("review_score_range", cnt == 0,
                         f"{cnt:,} records với review_score ngoài phạm vi 1-5")

        # delivery_days > 0 nếu có
        df = self._query_dwh(
            "SELECT COUNT(*) AS cnt FROM fact_orders "
            "WHERE delivery_days IS NOT NULL AND delivery_days <= 0")
        cnt = df["cnt"].iloc[0]
        self._add_result("delivery_days_positive", cnt == 0,
                         f"{cnt:,} records với delivery_days <= 0",
                         is_warning=cnt > 0)

        # Tỉ lệ orders delivered
        df = self._query_dwh(
            "SELECT order_status, COUNT(*) AS cnt FROM fact_orders "
            "GROUP BY order_status ORDER BY cnt DESC")
        total = df["cnt"].sum()
        delivered_row = df[df["order_status"] == "delivered"]
        delivered = delivered_row["cnt"].iloc[0] if len(delivered_row) > 0 else 0
        pct = delivered / total * 100 if total > 0 else 0
        passed = pct >= 85
        self._add_result("delivered_rate", passed,
                         f"{pct:.1f}% orders delivered ({delivered:,}/{total:,})")

        # Avg review score phải hợp lý (3.0 - 4.5)
        df = self._query_dwh(
            "SELECT ROUND(AVG(review_score), 2) AS avg_score FROM fact_orders "
            "WHERE review_score IS NOT NULL")
        avg = df["avg_score"].iloc[0]
        passed = 2.5 <= float(avg) <= 5.0
        self._add_result("avg_review_score", passed,
                         f"Avg review score = {avg} (expected 2.5–5.0)")

    # CHECK 6: Distribution statistics───────────────────────
    def check_distributions(self):
        log.info("\n[CHECK 6] Distribution Statistics")

        sql = """
        SELECT
            COUNT(*)                           AS total_items,
            COUNT(DISTINCT order_id)           AS total_orders,
            COUNT(DISTINCT customer_key)       AS unique_customers,
            ROUND(MIN(price), 2)               AS min_price,
            ROUND(MAX(price), 2)               AS max_price,
            ROUND(AVG(price), 2)               AS avg_price,
            ROUND(AVG(review_score), 2)        AS avg_review,
            ROUND(AVG(delivery_days), 1)       AS avg_delivery_days,
            ROUND(100.0 * SUM(CASE WHEN is_on_time = 1 THEN 1 ELSE 0 END)
                  / SUM(CASE WHEN is_on_time IS NOT NULL THEN 1 ELSE 0 END), 1) AS pct_on_time
        FROM fact_orders
        WHERE order_status = 'delivered'
        """
        df = self._query_dwh(sql)
        row = df.iloc[0]

        log.info(f"\nDELIVERED ORDERS STATISTICS:")
        stats = [
            ["Total items",       f"{row['total_items']:,}"],
            ["Total orders",      f"{row['total_orders']:,}"],
            ["Unique customers",  f"{row['unique_customers']:,}"],
            ["Price range",       f"R$ {row['min_price']} – R$ {row['max_price']}"],
            ["Avg item price",    f"R$ {row['avg_price']}"],
            ["Avg review score",  f"{row['avg_review']}"],
            ["Avg delivery days", f"{row['avg_delivery_days']} days"],
            ["On-time rate",      f"{row['pct_on_time']}%"],
        ]
        print(tabulate(stats, headers=["Metric", "Value"], tablefmt="rounded_outline"))

        # Top categories
        sql_cat = """
        SELECT p.product_category_name_english AS category,
               COUNT(*) AS items, ROUND(SUM(f.price), 0) AS revenue
        FROM fact_orders f
        JOIN dim_product p ON f.product_key = p.product_key
        WHERE f.order_status = 'delivered'
        GROUP BY p.product_category_name_english
        ORDER BY revenue DESC LIMIT 10
        """
        df_cat = self._query_dwh(sql_cat)
        log.info("\nTOP 10 CATEGORIES BY REVENUE:")
        print(tabulate(df_cat.values.tolist(),
                       headers=["Category", "Items", "Revenue (R$)"],
                       tablefmt="rounded_outline"))

        self._add_result("distribution_stats", True,
                         f"Avg price=R${row['avg_price']}, "
                         f"Avg review={row['avg_review']}, "
                         f"On-time={row['pct_on_time']}%")

    # MAIN RUN
    def run_all(self):
        log.info("=" * 60)
        log.info("BƯỚC 5: DATA QUALITY CHECKS")
        log.info("=" * 60)

        self.check_row_counts()
        self.check_staging_vs_dwh()
        self.check_null_measures()
        self.check_referential_integrity()
        self.check_business_rules()
        self.check_distributions()

        # Final Report
        log.info(f"\n{'='*60}")
        log.info("DATA QUALITY REPORT")
        log.info(f"{'='*60}")
        print(tabulate(
            self.results,
            headers=["Check", "Status", "Detail"],
            tablefmt="rounded_outline"
        ))

        total = len(self.results)
        passed = total - self.errors - self.warnings
        log.info(f"\n  Tổng: {total} checks | "
                 f"Pass: {passed} | "
                 f"Warn: {self.warnings} | "
                 f"Fail: {self.errors}")

        if self.errors == 0:
            log.info("[BƯỚC 5 HOÀN THÀNH - Data Quality OK]")
        else:
            log.error(f"[BƯỚC 5 CÓ {self.errors} LỖI - Cần xem xét]")

        return self.errors == 0


def run_quality_checks() -> bool:
    """Entry point cho data quality checks."""
    dwh_engine     = create_engine(DWH_URI,     echo=False)
    staging_engine = create_engine(STAGING_URI, echo=False)

    checker = DataQualityChecker(dwh_engine, staging_engine)
    success = checker.run_all()

    dwh_engine.dispose()
    staging_engine.dispose()
    return success


if __name__ == "__main__":
    run_quality_checks()
