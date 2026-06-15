# -*- coding: utf-8 -*-
"""
etl/run_etl_pipeline.py
Master ETL Pipeline Runner - chay toan bo 6 buoc theo thu tu.
Usage:
    python etl/run_etl_pipeline.py
"""

import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logger import get_logger
from config import GEOLOCATION_SAMPLE_FRAC

log = get_logger("pipeline")


def print_banner():
    banner = (
        "\n" +
        "=" * 62 + "\n" +
        "OLIST E-COMMERCE BI -- ETL PIPELINE\n" +
        "Dataset: Brazilian E-Commerce (Kaggle)\n" +
        "Target:  MySQL Star Schema (olist_dwh)\n" +
        "=" * 62 + "\n"
    )
    print(banner)


def run_step(step_num: int, name: str, fn, *args, **kwargs):
    # Chạy một bước ETL với timing và error handling.
    log.info(f"\n{'='*60}")
    log.info(f"  BƯỚC {step_num}: {name}")
    log.info(f"{'='*60}")
    start = time.time()
    try:
        result = fn(*args, **kwargs)
        elapsed = time.time() - start
        log.info(f"\n[Timer] Bước {step_num} hoàn thành trong {elapsed:.1f}s")
        return result
    except Exception as e:
        elapsed = time.time() - start
        log.error(f"\n[Error] Bước {step_num} THẤT BẠI sau {elapsed:.1f}s: {e}")
        raise


def main():
    print_banner()
    pipeline_start = time.time()
    log.info(f"Pipeline bắt đầu lúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # BƯỚC 0: Setup Database
    from etl_00_setup import main as setup_main
    run_step(0, "SETUP DATABASE", setup_main)

    # BƯỚC 1: Extract
    from etl_01_extract import extract_all
    dfs = run_step(1, "EXTRACT - Đọc raw CSV", extract_all,
                   geolocation_sample_frac=GEOLOCATION_SAMPLE_FRAC)

    # BƯỚC 2: Transform
    from etl_02_transform import transform_all
    transformed = run_step(2, "TRANSFORM — Làm sạch và build star schema",
                           transform_all, dfs)

    # BƯỚC 3: Load Staging
    from etl_03_load_staging import load_staging
    run_step(3, "LOAD STAGING", load_staging, dfs)

    # BƯỚC 4: Load DWH
    from etl_04_load_dwh import load_dwh
    run_step(4, "LOAD DATA WAREHOUSE", load_dwh, transformed)

    # BƯỚC 5: Data Quality
    from etl_05_data_quality import run_quality_checks
    quality_ok = run_step(5, "DATA QUALITY CHECKS", run_quality_checks)

    # TỔNG KẾT
    total_elapsed = time.time() - pipeline_start
    log.info(f"\n{'═'*60}")
    log.info(f"PIPELINE HOÀN THÀNH")
    log.info(f"Tổng thời gian: {total_elapsed/60:.1f} phút")
    log.info(f"Kết thúc lúc:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if quality_ok:
        log.info("[THÀNH CÔNG - DWH sẵn sàng cho Metabase]")
    else:
        log.warning("[CẢNH BÁO - Kiểm tra data quality report]")
    log.info(f"{'═'*60}\n")


# Import aliases để tránh lỗi tên file có số
import importlib, importlib.util

def _import_as(module_name: str, filepath: str):
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    mod  = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod

_etl_dir = os.path.dirname(os.path.abspath(__file__))

# Pre-register modules với alias names
_mods = {
    "etl_00_setup":       "00_setup_database.py",
    "etl_01_extract":     "01_extract.py",
    "etl_02_transform":   "02_transform.py",
    "etl_03_load_staging":"03_load_staging.py",
    "etl_04_load_dwh":    "04_load_dwh.py",
    "etl_05_data_quality":"05_data_quality.py",
}

for alias, fname in _mods.items():
    fpath = os.path.join(_etl_dir, fname)
    if os.path.exists(fpath):
        _import_as(alias, fpath)


if __name__ == "__main__":
    main()
