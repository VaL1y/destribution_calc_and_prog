CREATE SCHEMA IF NOT EXISTS warehouse AUTHORIZATION CURRENT_USER;

CREATE TABLE warehouse.categories (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name varchar(100) NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE warehouse.products (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku varchar(40) NOT NULL UNIQUE,
    name varchar(160) NOT NULL,
    category_id integer NOT NULL REFERENCES warehouse.categories(id),
    unit varchar(20) NOT NULL DEFAULT 'шт.',
    quantity integer NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    reorder_level integer NOT NULL DEFAULT 5 CHECK (reorder_level >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE warehouse.stock_movements (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id bigint NOT NULL REFERENCES warehouse.products(id) ON DELETE CASCADE,
    movement_type varchar(10) NOT NULL CHECK (movement_type IN ('in', 'out')),
    quantity integer NOT NULL CHECK (quantity > 0),
    note varchar(250),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX stock_movements_product_created_idx
    ON warehouse.stock_movements(product_id, created_at DESC);

INSERT INTO warehouse.categories(name)
VALUES ('Комплектующие'), ('Расходники'), ('Оборудование');

INSERT INTO warehouse.products(sku, name, category_id, unit, quantity, reorder_level)
VALUES
    ('CAB-USB-C', 'Кабель USB-C, 1 м', 1, 'шт.', 24, 8),
    ('PAP-A4', 'Бумага А4, 500 листов', 2, 'пач.', 7, 10),
    ('SCN-01', 'Сканер штрихкодов', 3, 'шт.', 3, 2);

INSERT INTO warehouse.stock_movements(product_id, movement_type, quantity, note)
VALUES
    (1, 'in', 24, 'Начальный остаток'),
    (2, 'in', 7, 'Начальный остаток'),
    (3, 'in', 3, 'Начальный остаток');
