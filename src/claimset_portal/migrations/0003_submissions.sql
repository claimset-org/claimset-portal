-- Pending submissions (design §4.2): valid submissions waiting for their guarantors' consent. Not public; deleted
-- 48 hours after receipt unless every guarantor has confirmed.

CREATE TABLE submissions (
    id text PRIMARY KEY,                    -- sub_<random>: unguessable, never part of the published record
    received timestamptz NOT NULL DEFAULT now(),
    expires timestamptz NOT NULL,
    state text NOT NULL CHECK (state IN ('pending', 'confirmed', 'published', 'refused', 'expired')),
    kind text NOT NULL CHECK (kind IN ('new', 'correction')),
    target text,                            -- the claimset a correction names
    title text,
    file_name text,                         -- the stored upload, under the submissions directory; null once deleted
    sha256 text NOT NULL,
    size bigint NOT NULL,
    report jsonb NOT NULL,                  -- warnings and the verifiability the platform will compute
    client_ip inet,
    published_id text,                      -- liblm:…@v<n>, once published
    detail text                             -- why it was refused, when it was
);

CREATE INDEX submissions_pending ON submissions (state, expires);
CREATE INDEX submissions_ip ON submissions (client_ip, state);

CREATE TABLE submission_guarantors (
    submission_id text NOT NULL REFERENCES submissions ON DELETE CASCADE,
    orcid text NOT NULL,
    name text,
    token_hash text NOT NULL UNIQUE,        -- sha256 of the consent link's token; the token itself is never stored
    confirmed timestamptz,
    PRIMARY KEY (submission_id, orcid)
);
