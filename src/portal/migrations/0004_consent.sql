-- ORCID sign-in for consent (design §4.2 step 4). One row per sign-in started from a consent page: the OAuth
-- `state` ties ORCID's callback to the consent link it came from, and is used once.
CREATE TABLE consent_signins (
    state text PRIMARY KEY,
    token_hash text NOT NULL REFERENCES submission_guarantors (token_hash) ON DELETE CASCADE,
    started timestamptz NOT NULL DEFAULT now(),
    used timestamptz
);
