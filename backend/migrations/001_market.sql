CREATE SCHEMA IF NOT EXISTS market;
CREATE TABLE IF NOT EXISTS market.datasets (
    id uuid PRIMARY KEY, window_start date NOT NULL, window_end date NOT NULL,
    published_at timestamptz NOT NULL DEFAULT now(), demo boolean NOT NULL DEFAULT false,
    CHECK (window_start <= window_end),
    CHECK (window_start >= (window_end - interval '35 months')::date)
);
CREATE TABLE IF NOT EXISTS market.state (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    active uuid REFERENCES market.datasets(id), previous uuid REFERENCES market.datasets(id)
);
INSERT INTO market.state(singleton) VALUES (true) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS market.facts (
    dataset uuid NOT NULL REFERENCES market.datasets(id) ON DELETE CASCADE,
    kind text NOT NULL CHECK (kind IN ('listing','sold')),
    listing_key text NOT NULL, month date NOT NULL,
    county text NOT NULL, city text NOT NULL, zip text NOT NULL, subtype text NOT NULL,
    close_price numeric(16,2), days_on_market double precision, price_sqft double precision,
    price_ratio double precision, agent_id text NOT NULL, agent_name text NOT NULL,
    office_id text NOT NULL, office_name text NOT NULL,
    grid_lat double precision, grid_lng double precision,
    modified_at timestamptz,
    PRIMARY KEY(dataset,kind,listing_key),
    CHECK (month = date_trunc('month',month)::date),
    CHECK (days_on_market IS NULL OR (days_on_market >= 0 AND days_on_market < 'Infinity'::float8)),
    CHECK (price_sqft IS NULL OR (price_sqft >= 0 AND price_sqft < 'Infinity'::float8)),
    CHECK (price_ratio IS NULL OR (price_ratio >= 0 AND price_ratio < 'Infinity'::float8)),
    CHECK (close_price IS NULL OR (close_price >= 0 AND close_price < 'Infinity'::numeric))
);
CREATE INDEX IF NOT EXISTS facts_period ON market.facts(dataset,month,kind);
CREATE INDEX IF NOT EXISTS facts_county ON market.facts(dataset,county,month);
CREATE INDEX IF NOT EXISTS facts_zip ON market.facts(dataset,zip,month);
CREATE INDEX IF NOT EXISTS facts_city ON market.facts(dataset,city,month);
CREATE INDEX IF NOT EXISTS facts_subtype ON market.facts(dataset,subtype,month);
CREATE TABLE IF NOT EXISTS market.mortgage (
    dataset uuid REFERENCES market.datasets(id) ON DELETE CASCADE,
    month date NOT NULL, rate double precision,
    PRIMARY KEY(dataset,month), CHECK (rate IS NULL OR (rate >= 0 AND rate < 'Infinity'::float8))
);
CREATE TABLE IF NOT EXISTS market.geographies (
    dataset uuid REFERENCES market.datasets(id) ON DELETE CASCADE,
    county text NOT NULL, city text NOT NULL, zip text NOT NULL, subtype text NOT NULL,
    PRIMARY KEY(dataset,county,city,zip,subtype)
);
CREATE TABLE IF NOT EXISTS market.monthly_aggregates (
    dataset uuid REFERENCES market.datasets(id) ON DELETE CASCADE,
    month date NOT NULL, county text NOT NULL, metrics jsonb NOT NULL,
    PRIMARY KEY(dataset,month,county)
);
CREATE TABLE IF NOT EXISTS market.competitive_aggregates (
    dataset uuid REFERENCES market.datasets(id) ON DELETE CASCADE,
    month date NOT NULL, entity_type text NOT NULL, entity_id text NOT NULL,
    sales bigint NOT NULL, volume numeric NOT NULL,
    PRIMARY KEY(dataset,month,entity_type,entity_id)
);
CREATE TABLE IF NOT EXISTS market.ingestion_runs (
    id uuid PRIMARY KEY, started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz, status text NOT NULL, reporting_month date NOT NULL,
    details jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE IF NOT EXISTS market.schema_migrations (name text PRIMARY KEY, applied_at timestamptz DEFAULT now());
