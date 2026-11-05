-- The extensions the portal relies on. Tables arrive with the steps that use them (publication, submissions,
-- consent, search).
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
