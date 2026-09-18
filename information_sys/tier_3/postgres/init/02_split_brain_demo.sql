CREATE TABLE warehouse.inventory_events (
    event_id uuid PRIMARY KEY,
    source_node varchar(40) NOT NULL,
    product_id bigint NOT NULL
        REFERENCES warehouse.products(id) ON DELETE RESTRICT,
    delta integer NOT NULL CHECK (delta > 0),
    note varchar(250),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX inventory_events_product_created_idx
    ON warehouse.inventory_events(product_id, created_at, event_id);

COMMENT ON TABLE warehouse.inventory_events IS
    'Append-only arrivals used to demonstrate split-brain reconciliation';

