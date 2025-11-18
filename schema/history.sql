-- history.db schema
-- Contains Git history analysis for temporal and behavioral metrics

-- Core Entities

CREATE TABLE IF NOT EXISTS commits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hash TEXT NOT NULL UNIQUE,
    author_name TEXT NOT NULL,
    author_email TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    message TEXT,
    CONSTRAINT valid_hash CHECK (length(hash) = 40)
);

CREATE INDEX idx_commits_hash ON commits(hash);
CREATE INDEX idx_commits_author_email ON commits(author_email);
CREATE INDEX idx_commits_timestamp ON commits(timestamp);

CREATE TABLE IF NOT EXISTS authors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);

CREATE INDEX idx_authors_email ON authors(email);
CREATE INDEX idx_authors_name ON authors(name);

CREATE TABLE IF NOT EXISTS file_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commit_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    lines_added INTEGER NOT NULL DEFAULT 0,
    lines_deleted INTEGER NOT NULL DEFAULT 0,
    change_type TEXT NOT NULL CHECK (change_type IN ('A', 'M', 'D', 'R', 'C')),
    old_path TEXT,
    FOREIGN KEY (commit_id) REFERENCES commits(id) ON DELETE CASCADE,
    CONSTRAINT valid_lines CHECK (lines_added >= 0 AND lines_deleted >= 0)
);

CREATE INDEX idx_file_changes_commit ON file_changes(commit_id);
CREATE INDEX idx_file_changes_path ON file_changes(file_path);
CREATE INDEX idx_file_changes_type ON file_changes(change_type);

-- Derived Data Tables

CREATE TABLE IF NOT EXISTS temporal_coupling (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_a TEXT NOT NULL,
    file_b TEXT NOT NULL,
    co_change_count INTEGER NOT NULL DEFAULT 0,
    jaccard_similarity REAL NOT NULL DEFAULT 0.0,
    CONSTRAINT ordered_pair CHECK (file_a < file_b),
    CONSTRAINT unique_pair UNIQUE (file_a, file_b),
    CONSTRAINT valid_count CHECK (co_change_count >= 0),
    CONSTRAINT valid_similarity CHECK (jaccard_similarity >= 0.0 AND jaccard_similarity <= 1.0)
);

CREATE INDEX idx_temporal_coupling_files ON temporal_coupling(file_a, file_b);
CREATE INDEX idx_temporal_coupling_similarity ON temporal_coupling(jaccard_similarity DESC);
CREATE INDEX idx_temporal_coupling_count ON temporal_coupling(co_change_count DESC);

CREATE TABLE IF NOT EXISTS author_ownership (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    commit_count INTEGER NOT NULL DEFAULT 0,
    lines_contributed INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE,
    CONSTRAINT unique_ownership UNIQUE (author_id, file_path),
    CONSTRAINT valid_counts CHECK (commit_count >= 0 AND lines_contributed >= 0)
);

CREATE INDEX idx_author_ownership_author ON author_ownership(author_id);
CREATE INDEX idx_author_ownership_file ON author_ownership(file_path);
CREATE INDEX idx_author_ownership_commits ON author_ownership(commit_count DESC);

-- Materialized Views for Common Queries

-- File churn metrics
CREATE VIEW IF NOT EXISTS churn_metrics AS
SELECT
    fc.file_path,
    COUNT(DISTINCT fc.commit_id) AS total_commits,
    SUM(fc.lines_added) AS total_lines_added,
    SUM(fc.lines_deleted) AS total_lines_deleted,
    SUM(fc.lines_added + fc.lines_deleted) AS total_churn,
    MIN(c.timestamp) AS first_commit_date,
    MAX(c.timestamp) AS last_commit_date,
    COUNT(DISTINCT c.author_email) AS author_count
FROM file_changes fc
JOIN commits c ON fc.commit_id = c.id
WHERE fc.change_type != 'D'
GROUP BY fc.file_path;

-- Author statistics
CREATE VIEW IF NOT EXISTS author_stats AS
SELECT
    a.id AS author_id,
    a.name,
    a.email,
    COUNT(DISTINCT c.id) AS total_commits,
    COUNT(DISTINCT fc.file_path) AS files_touched,
    SUM(fc.lines_added) AS total_lines_added,
    SUM(fc.lines_deleted) AS total_lines_deleted,
    MIN(c.timestamp) AS first_commit,
    MAX(c.timestamp) AS last_commit
FROM authors a
JOIN commits c ON c.author_email = a.email
LEFT JOIN file_changes fc ON fc.commit_id = c.id
GROUP BY a.id, a.name, a.email;

-- Commit frequency by file (commits per month)
CREATE VIEW IF NOT EXISTS commit_frequency AS
SELECT
    fc.file_path,
    strftime('%Y-%m', c.timestamp) AS month,
    COUNT(*) AS commit_count,
    SUM(fc.lines_added + fc.lines_deleted) AS churn
FROM file_changes fc
JOIN commits c ON fc.commit_id = c.id
WHERE fc.change_type != 'D'
GROUP BY fc.file_path, strftime('%Y-%m', c.timestamp);

-- Files that frequently change together (top temporal couplings)
CREATE VIEW IF NOT EXISTS high_temporal_coupling AS
SELECT
    tc.file_a,
    tc.file_b,
    tc.co_change_count,
    tc.jaccard_similarity,
    cm1.total_commits AS file_a_commits,
    cm2.total_commits AS file_b_commits
FROM temporal_coupling tc
LEFT JOIN churn_metrics cm1 ON tc.file_a = cm1.file_path
LEFT JOIN churn_metrics cm2 ON tc.file_b = cm2.file_path
WHERE tc.co_change_count >= 3 AND tc.jaccard_similarity >= 0.3
ORDER BY tc.jaccard_similarity DESC, tc.co_change_count DESC;

-- Code age by file (days since last modification)
CREATE VIEW IF NOT EXISTS code_age AS
SELECT
    file_path,
    last_commit_date,
    first_commit_date,
    julianday('now') - julianday(last_commit_date) AS days_since_last_change,
    julianday(last_commit_date) - julianday(first_commit_date) AS days_active,
    total_commits,
    CAST(total_commits AS REAL) /
        NULLIF((julianday(last_commit_date) - julianday(first_commit_date)) / 30.0, 0)
        AS commits_per_month
FROM churn_metrics;
