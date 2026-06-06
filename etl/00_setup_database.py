"""
etl/00_setup_database.py
Bước 0: Khởi tạo cơ sở dữ liệu MySQL.
- Tạo database olist_staging và olist_dwh nếu chưa có
- Chạy các file DDL SQL để tạo bảng
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from config import (
    MYSQL_URI, STAGING_URI, DWH_URI,
    STAGING_DB, DWH_DB, SQL_DIR
)
from logger import get_logger

log = get_logger("00_setup_db")


def run_sql_file(engine, filepath: str) -> None:
    """Đọc và chạy file .sql, tách theo dấu ';'."""
    log.info(f"Chạy SQL file: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    # Tách các statement, bỏ comment và statement rỗng
    statements = [
        s.strip() for s in raw.split(";")
        if s.strip() and not s.strip().startswith("--")
    ]

    with engine.connect() as conn:
        for i, stmt in enumerate(statements, 1):
            if not stmt:
                continue
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception as e:
                log.warning(f"Statement {i} warning: {e}")

    log.info(f"Hoàn thành {len(statements)} statements")


def create_databases(engine) -> None:
    """Tạo các database nếu chưa tồn tại."""
    with engine.connect() as conn:
        for db in [STAGING_DB, DWH_DB]:
            conn.execute(text(
                f"CREATE DATABASE IF NOT EXISTS `{db}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            ))
            conn.commit()
            log.info(f"Database '{db}' sẵn sàng")


def main():
    log.info("=" * 60)
    log.info("BƯỚC 0: SETUP DATABASE")
    log.info("=" * 60)

    # Kết nối không chỉ định database để tạo mới
    log.info("Kết nối MySQL server...")
    engine_root = create_engine(MYSQL_URI, echo=False)

    # Kiểm tra kết nối
    with engine_root.connect() as conn:
        result = conn.execute(text("SELECT VERSION()"))
        version = result.fetchone()[0]
        log.info(f"Kết nối thành công - MySQL {version}")

    # Tạo databases
    log.info("Tạo databases...")
    create_databases(engine_root)
    engine_root.dispose()

    # Chạy DDL staging
    log.info("Tạo staging tables...")
    engine_staging = create_engine(STAGING_URI, echo=False)
    run_sql_file(engine_staging, os.path.join(SQL_DIR, "01_create_staging.sql"))
    engine_staging.dispose()

    # Chạy DDL DWH
    log.info("Tạo DWH tables (star schema)...")
    engine_dwh = create_engine(DWH_URI, echo=False)
    run_sql_file(engine_dwh, os.path.join(SQL_DIR, "02_create_dwh.sql"))
    engine_dwh.dispose()

    log.info("")
    log.info("[BƯỚC 0 HOÀN THÀNH Database sẵn sàng cho ETL]")


if __name__ == "__main__":
    main()
