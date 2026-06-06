-- Tạo Data Warehouse với Star Schema

CREATE DATABASE IF NOT EXISTS olist_dwh
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE olist_dwh;

--  DIMENSION TABLES

-- DIM_TIME: Calendar dimension

DROP TABLE IF EXISTS dim_time;
CREATE TABLE dim_time (
    time_key        INT          NOT NULL,   -- YYYYMMDD format
    full_date       DATE         NOT NULL,
    year            SMALLINT     NOT NULL,
    quarter         TINYINT      NOT NULL,   -- 1-4
    month           TINYINT      NOT NULL,   -- 1-12
    month_name      VARCHAR(10)  NOT NULL,
    week_of_year    TINYINT      NOT NULL,   -- 1-53
    day_of_month    TINYINT      NOT NULL,   -- 1-31
    day_of_week     TINYINT      NOT NULL,   -- 1=Mon ... 7=Sun
    day_name        VARCHAR(10)  NOT NULL,
    is_weekend      BOOLEAN      NOT NULL DEFAULT FALSE,
    PRIMARY KEY (time_key),
    INDEX idx_year_month (year, month)
) ENGINE=InnoDB COMMENT='Calendar dimension — one row per day';

-- DIM_CUSTOMER: Customer dimension (SCD Type 1)

DROP TABLE IF EXISTS dim_customer;
CREATE TABLE dim_customer (
    customer_key             INT          NOT NULL AUTO_INCREMENT,
    customer_id              VARCHAR(50)  NOT NULL,
    customer_unique_id       VARCHAR(50)  NOT NULL,
    customer_zip_code_prefix VARCHAR(10),
    customer_city            VARCHAR(100),
    customer_state           CHAR(2),
    _etl_loaded_at           DATETIME     DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (customer_key),
    UNIQUE KEY uq_customer_id (customer_id),
    INDEX idx_state (customer_state)
) ENGINE=InnoDB COMMENT='Customer dimension';

-- DIM_PRODUCT: Product dimension (SCD Type 1)

DROP TABLE IF EXISTS dim_product;
CREATE TABLE dim_product (
    product_key                    INT          NOT NULL AUTO_INCREMENT,
    product_id                     VARCHAR(50)  NOT NULL,
    product_category_name          VARCHAR(100),
    product_category_name_english  VARCHAR(100),
    product_weight_g               INT,
    product_length_cm              INT,
    product_height_cm              INT,
    product_width_cm               INT,
    _etl_loaded_at                 DATETIME     DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (product_key),
    UNIQUE KEY uq_product_id (product_id),
    INDEX idx_category (product_category_name_english)
) ENGINE=InnoDB COMMENT='Product dimension';

-- DIM_REGION: Geographic region dimension (Brazil states)

DROP TABLE IF EXISTS dim_region;
CREATE TABLE dim_region (
    region_key    INT          NOT NULL AUTO_INCREMENT,
    state_code    CHAR(2)      NOT NULL,
    state_name    VARCHAR(50)  NOT NULL,
    macro_region  VARCHAR(30)  NOT NULL,  -- Norte/Nordeste/Sudeste/Sul/Centro-Oeste
    PRIMARY KEY (region_key),
    UNIQUE KEY uq_state_code (state_code)
) ENGINE=InnoDB COMMENT='Brazil geographic region dimension';

-- DIM_SELLER: Seller dimension

DROP TABLE IF EXISTS dim_seller;
CREATE TABLE dim_seller (
    seller_key             INT          NOT NULL AUTO_INCREMENT,
    seller_id              VARCHAR(50)  NOT NULL,
    seller_zip_code_prefix VARCHAR(10),
    seller_city            VARCHAR(100),
    seller_state           CHAR(2),
    _etl_loaded_at         DATETIME     DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (seller_key),
    UNIQUE KEY uq_seller_id (seller_id),
    INDEX idx_state (seller_state)
) ENGINE=InnoDB COMMENT='Seller dimension';

--  FACT TABLE

-- FACT_ORDERS: Grain = one row per order item

DROP TABLE IF EXISTS fact_orders;
CREATE TABLE fact_orders (
    order_item_key          BIGINT        NOT NULL AUTO_INCREMENT,

    -- Degenerate dimensions (natural keys)
    order_id                VARCHAR(50)   NOT NULL,
    order_item_id           INT           NOT NULL,

    -- Foreign keys → dimensions
    customer_key            INT           NOT NULL,
    product_key             INT           NOT NULL,
    seller_key              INT           NOT NULL,
    purchase_time_key       INT           NOT NULL,   -- FK → dim_time
    delivery_time_key       INT,                      -- FK → dim_time (nullable)
    customer_region_key     INT           NOT NULL,   -- FK → dim_region (customer state)
    seller_region_key       INT,                      -- FK → dim_region (seller state)

    -- Measures (additive)
    price                   DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    freight_value           DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total_revenue           DECIMAL(10,2) NOT NULL DEFAULT 0.00,  -- price + freight
    payment_value           DECIMAL(10,2),
    payment_installments    INT,

    -- Semi-additive / non-additive
    review_score            TINYINT,
    delivery_days           INT,          -- days from purchase → delivered (NULL if not delivered)
    estimated_delivery_days INT,          -- days from purchase → estimated delivery
    delay_days              INT,          -- delivery_days - estimated_delivery_days (negative = early)
    is_on_time              BOOLEAN,      -- 1 = delivered on or before estimated

    -- Descriptive (degenerate)
    order_status            VARCHAR(20),
    payment_type            VARCHAR(30),

    -- Audit
    _etl_loaded_at          DATETIME      DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (order_item_key),
    UNIQUE KEY uq_order_item (order_id, order_item_id),
    FOREIGN KEY (customer_key)        REFERENCES dim_customer(customer_key),
    FOREIGN KEY (product_key)         REFERENCES dim_product(product_key),
    FOREIGN KEY (seller_key)          REFERENCES dim_seller(seller_key),
    FOREIGN KEY (purchase_time_key)   REFERENCES dim_time(time_key),
    FOREIGN KEY (customer_region_key) REFERENCES dim_region(region_key),
    INDEX idx_purchase_time (purchase_time_key),
    INDEX idx_customer      (customer_key),
    INDEX idx_product       (product_key),
    INDEX idx_order_status  (order_status)
) ENGINE=InnoDB COMMENT='Fact table — grain: one row per order item';
