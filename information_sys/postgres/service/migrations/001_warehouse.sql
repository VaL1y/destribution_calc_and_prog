CREATE SCHEMA IF NOT EXISTS warehouse AUTHORIZATION CURRENT_USER;

CREATE TABLE IF NOT EXISTS warehouse.categories (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name varchar(100) NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS warehouse.products (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku varchar(40) NOT NULL UNIQUE,
    name varchar(160) NOT NULL,
    category_id integer NOT NULL REFERENCES warehouse.categories(id),
    unit varchar(20) NOT NULL DEFAULT 'pcs',
    quantity integer NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    reorder_level integer NOT NULL DEFAULT 5 CHECK (reorder_level >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS warehouse.stock_movements (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id bigint NOT NULL REFERENCES warehouse.products(id) ON DELETE CASCADE,
    movement_type varchar(10) NOT NULL CHECK (movement_type IN ('in', 'out')),
    quantity integer NOT NULL CHECK (quantity > 0),
    note varchar(250),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS stock_movements_product_created_idx
    ON warehouse.stock_movements(product_id, created_at DESC);

INSERT INTO warehouse.categories(name)
VALUES ('Components'), ('Consumables'), ('Equipment')
ON CONFLICT (name) DO NOTHING;

INSERT INTO warehouse.products(sku, name, category_id, unit, quantity, reorder_level)
VALUES
    ('CAB-USB-C', 'USB-C cable, 1 m', (SELECT id FROM warehouse.categories WHERE name = 'Components'), 'pcs', 24, 8),
    ('PAP-A4', 'A4 paper, 500 sheets', (SELECT id FROM warehouse.categories WHERE name = 'Consumables'), 'pack', 7, 10),
    ('SCN-01', 'Barcode scanner', (SELECT id FROM warehouse.categories WHERE name = 'Equipment'), 'pcs', 3, 2)
ON CONFLICT (sku) DO NOTHING;

INSERT INTO warehouse.stock_movements(product_id, movement_type, quantity, note)
SELECT p.id, 'in', p.quantity, 'Initial stock'
FROM warehouse.products p
WHERE NOT EXISTS (
    SELECT 1 FROM warehouse.stock_movements m WHERE m.product_id = p.id
);

CREATE TABLE IF NOT EXISTS warehouse.inventory_events (
    event_id uuid PRIMARY KEY,
    source_node varchar(80) NOT NULL,
    product_id bigint NOT NULL REFERENCES warehouse.products(id),
    delta integer NOT NULL CHECK (delta > 0),
    note varchar(250),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS inventory_events_created_idx
    ON warehouse.inventory_events(created_at, event_id);
