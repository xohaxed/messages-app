CREATE TABLE IF NOT EXISTS messages (
    id         SERIAL PRIMARY KEY,
    author     VARCHAR(50)  NOT NULL,
    content    VARCHAR(500) NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);
