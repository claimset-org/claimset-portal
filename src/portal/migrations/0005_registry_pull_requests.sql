-- Publication through registry pull requests (design §5): a confirmed submission is `publishing` while its pull
-- request is open. The identifier it was given is kept on the submission, so a retried round reuses it.
ALTER TABLE submissions DROP CONSTRAINT submissions_state_check;
ALTER TABLE submissions ADD CONSTRAINT submissions_state_check
    CHECK (state IN ('pending', 'confirmed', 'publishing', 'published', 'refused', 'expired'));

ALTER TABLE submissions
    ADD COLUMN pending_id text,             -- the identifier given, before publication (new claimsets)
    ADD COLUMN registry_pr integer,         -- the registry pull request
    ADD COLUMN registry_branch text,
    ADD COLUMN registry_version integer;
