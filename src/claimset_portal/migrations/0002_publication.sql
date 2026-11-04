-- Published claimsets. Everything here is an index of the registry and can be rebuilt from it
-- (`claimset-portal reindex`), except the identifier counters, which reindex restores from the registry too.

-- The last number given out per year: `liblm:<year>.<number>`. A number is never given out twice, even when the
-- publication it was given to fails.
CREATE TABLE id_counters (
    year integer PRIMARY KEY,
    last integer NOT NULL
);

CREATE TABLE papers (
    concept_id text PRIMARY KEY,           -- liblm:2026.000001
    url_key text NOT NULL UNIQUE,          -- 2026.000001
    folder text NOT NULL UNIQUE,           -- liblm_2026.000001, the registry folder
    current_version integer NOT NULL,
    title text NOT NULL,
    status text NOT NULL,
    first_published date NOT NULL,
    updated date NOT NULL
);

CREATE TABLE versions (
    concept_id text NOT NULL REFERENCES papers ON DELETE CASCADE,
    version integer NOT NULL,
    published date NOT NULL,
    status text NOT NULL,
    hash text NOT NULL,                    -- sha256 of the canonical JSON of the published file
    file jsonb NOT NULL,                   -- the published file
    classifier text,                       -- which classifier assigned the subfield and topics
    PRIMARY KEY (concept_id, version)
);

CREATE TABLE claims (
    concept_id text NOT NULL,
    version integer NOT NULL,
    claim_id text NOT NULL,
    role text,
    type text,
    novelty text,
    is_assumption boolean NOT NULL,
    statement text NOT NULL,
    tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', statement)) STORED,
    PRIMARY KEY (concept_id, version, claim_id),
    FOREIGN KEY (concept_id, version) REFERENCES versions ON DELETE CASCADE
);

CREATE INDEX claims_tsv ON claims USING gin (tsv);
CREATE INDEX claims_statement_trgm ON claims USING gin (statement gin_trgm_ops);
