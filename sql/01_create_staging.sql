-- Tạo database staging và các bảng 1:1 với raw CSV

CREATE DATABASE IF NOT EXISTS olist_staging
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE olist_staging;

-- STG_ORDERS: từ olist_orders_dataset.csv

DROP TABLE IF EXISTS stg_orders;
CREATE TABLE stg_orders (
    order_id                       VARCHAR(50)  NOT NULL,
    customer_id                    VARCHAR(50)  NOT NULL,
    order_status                   VARCHAR(20),
    order_purchase_timestamp       DATETIME,
    order_approved_at              DATETIME,
    order_delivered_carrier_date   DATETIME,
    order_delivered_customer_date  DATETIME,
    order_estimated_delivery_date  DATETIME,
    -- ETL audit columns
    _etl_loaded_at                 DATETIME     DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id)
) ENGINE=InnoDB;

-- STG_ORDER_ITEMS: từ olist_order_items_dataset.csv

DROP TABLE IF EXISTS stg_order_items;
CREATE TABLE stg_order_items (
    order_id             VARCHAR(50)    NOT NULL,
    order_item_id        INT            NOT NULL,
    product_id           VARCHAR(50)    NOT NULL,
    seller_id            VARCHAR(50)    NOT NULL,
    shipping_limit_date  DATETIME,
    price                DECIMAL(10,2),
    freight_value        DECIMAL(10,2),
    _etl_loaded_at       DATETIME       DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id, order_item_id)
) ENGINE=InnoDB;

-- STG_ORDER_PAYMENTS: từ olist_order_payments_dataset.csv

DROP TABLE IF EXISTS stg_order_payments;
CREATE TABLE stg_order_payments (
    order_id              VARCHAR(50)  NOT NULL,
    payment_sequential    INT          NOT NULL,
    payment_type          VARCHAR(30),
    payment_installments  INT,
    payment_value         DECIMAL(10,2),
    _etl_loaded_at        DATETIME     DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id, payment_sequential)
) ENGINE=InnoDB;

-- STG_ORDER_REVIEWS: từ olist_order_reviews_dataset.csv

DROP TABLE IF EXISTS stg_order_reviews;
CREATE TABLE stg_order_reviews (
    review_id                VARCHAR(50)   NOT NULL,
    order_id                 VARCHAR(50)   NOT NULL,
    review_score             TINYINT,
    review_comment_title     VARCHAR(100),
    review_comment_message   TEXT,
    review_creation_date     DATETIME,
    review_answer_timestamp  DATETIME,
    _etl_loaded_at           DATETIME      DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (review_id)
) ENGINE=InnoDB;

-- STG_CUSTOMERS: từ olist_customers_dataset.csv

DROP TABLE IF EXISTS stg_customers;
CREATE TABLE stg_customers (
    customer_id              VARCHAR(50)  NOT NULL,
    customer_unique_id       VARCHAR(50)  NOT NULL,
    customer_zip_code_prefix VARCHAR(10),
    customer_city            VARCHAR(100),
    customer_state           CHAR(2),
    _etl_loaded_at           DATETIME     DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (customer_id)
) ENGINE=InnoDB;

-- STG_SELLERS: từ olist_sellers_dataset.csv

DROP TABLE IF EXISTS stg_sellers;
CREATE TABLE stg_sellers (
    seller_id              VARCHAR(50)  NOT NULL,
    seller_zip_code_prefix VARCHAR(10),
    seller_city            VARCHAR(100),
    seller_state           CHAR(2),
    _etl_loaded_at         DATETIME     DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (seller_id)
) ENGINE=InnoDB;

-- STG_PRODUCTS: từ olist_products_dataset.csv + translation

DROP TABLE IF EXISTS stg_products;
CREATE TABLE stg_products (
    product_id                     VARCHAR(50)  NOT NULL,
    product_category_name          VARCHAR(100),
    product_category_name_english  VARCHAR(100),
    product_name_lenght            INT,
    product_description_lenght     INT,
    product_photos_qty             INT,
    product_weight_g               INT,
    product_length_cm              INT,
    product_height_cm              INT,
    product_width_cm               INT,
    _etl_loaded_at                 DATETIME     DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id)
) ENGINE=InnoDB;

-- STG_GEOLOCATION: từ olist_geolocation_dataset.csv (sample)

DROP TABLE IF EXISTS stg_geolocation;
CREATE TABLE stg_geolocation (
    geolocation_zip_code_prefix  VARCHAR(10),
    geolocation_lat              DECIMAL(10,6),
    geolocation_lng              DECIMAL(10,6),
    geolocation_city             VARCHAR(100),
    geolocation_state            CHAR(2),
    _etl_loaded_at               DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_zip (geolocation_zip_code_prefix)
) ENGINE=InnoDB;
