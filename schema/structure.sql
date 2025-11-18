-- structure.db schema
-- Contains AST-parsed structural relationships from Python code

-- Core Entities

CREATE TABLE IF NOT EXISTS modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    last_parsed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_path CHECK (length(path) > 0)
);

CREATE INDEX idx_modules_path ON modules(path);
CREATE INDEX idx_modules_hash ON modules(file_hash);

CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    docstring TEXT,
    FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE,
    CONSTRAINT valid_lines CHECK (line_end >= line_start)
);

CREATE INDEX idx_classes_module ON classes(module_id);
CREATE INDEX idx_classes_name ON classes(name);

CREATE TABLE IF NOT EXISTS functions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    class_id INTEGER,
    name TEXT NOT NULL,
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    docstring TEXT,
    cyclomatic_complexity INTEGER DEFAULT 1,
    FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    CONSTRAINT valid_lines CHECK (line_end >= line_start),
    CONSTRAINT valid_complexity CHECK (cyclomatic_complexity >= 1)
);

CREATE INDEX idx_functions_module ON functions(module_id);
CREATE INDEX idx_functions_class ON functions(class_id);
CREATE INDEX idx_functions_name ON functions(name);
CREATE INDEX idx_functions_complexity ON functions(cyclomatic_complexity);

CREATE TABLE IF NOT EXISTS variables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    class_id INTEGER,
    function_id INTEGER,
    name TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (function_id) REFERENCES functions(id) ON DELETE CASCADE
);

CREATE INDEX idx_variables_module ON variables(module_id);
CREATE INDEX idx_variables_class ON variables(class_id);
CREATE INDEX idx_variables_function ON variables(function_id);
CREATE INDEX idx_variables_name ON variables(name);

-- Relationship Tables

CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_module_id INTEGER NOT NULL,
    to_module TEXT NOT NULL,
    import_name TEXT NOT NULL,
    alias TEXT,
    is_relative BOOLEAN DEFAULT 0,
    is_dynamic BOOLEAN DEFAULT 0,
    line_number INTEGER NOT NULL,
    FOREIGN KEY (from_module_id) REFERENCES modules(id) ON DELETE CASCADE
);

CREATE INDEX idx_imports_from ON imports(from_module_id);
CREATE INDEX idx_imports_to ON imports(to_module);
CREATE INDEX idx_imports_name ON imports(import_name);

CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_function_id INTEGER NOT NULL,
    to_function_id INTEGER,
    to_name TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    FOREIGN KEY (from_function_id) REFERENCES functions(id) ON DELETE CASCADE,
    FOREIGN KEY (to_function_id) REFERENCES functions(id) ON DELETE CASCADE
);

CREATE INDEX idx_calls_from ON calls(from_function_id);
CREATE INDEX idx_calls_to ON calls(to_function_id);
CREATE INDEX idx_calls_to_name ON calls(to_name);

CREATE TABLE IF NOT EXISTS inheritance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    base_class_id INTEGER,
    base_class_name TEXT NOT NULL,
    position INTEGER NOT NULL,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (base_class_id) REFERENCES classes(id) ON DELETE CASCADE,
    CONSTRAINT valid_position CHECK (position >= 0)
);

CREATE INDEX idx_inheritance_class ON inheritance(class_id);
CREATE INDEX idx_inheritance_base ON inheritance(base_class_id);
CREATE INDEX idx_inheritance_base_name ON inheritance(base_class_name);

CREATE TABLE IF NOT EXISTS decorators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type TEXT NOT NULL CHECK (target_type IN ('function', 'class')),
    target_id INTEGER NOT NULL,
    decorator_name TEXT NOT NULL,
    line_number INTEGER NOT NULL
);

CREATE INDEX idx_decorators_target ON decorators(target_type, target_id);
CREATE INDEX idx_decorators_name ON decorators(decorator_name);

CREATE TABLE IF NOT EXISTS type_hints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    function_id INTEGER,
    variable_id INTEGER,
    hint_type TEXT NOT NULL CHECK (hint_type IN ('parameter', 'return', 'variable')),
    parameter_name TEXT,
    type_annotation TEXT NOT NULL,
    FOREIGN KEY (function_id) REFERENCES functions(id) ON DELETE CASCADE,
    FOREIGN KEY (variable_id) REFERENCES variables(id) ON DELETE CASCADE,
    CONSTRAINT has_target CHECK (
        (function_id IS NOT NULL) OR (variable_id IS NOT NULL)
    )
);

CREATE INDEX idx_type_hints_function ON type_hints(function_id);
CREATE INDEX idx_type_hints_variable ON type_hints(variable_id);
CREATE INDEX idx_type_hints_type ON type_hints(hint_type);

-- Materialized Views for Common Queries

-- Afferent coupling (Ca): incoming dependencies to a module
CREATE VIEW IF NOT EXISTS afferent_coupling AS
SELECT
    m.id AS module_id,
    m.path AS module_path,
    COUNT(DISTINCT i.from_module_id) AS afferent_coupling
FROM modules m
LEFT JOIN imports i ON i.to_module = m.name OR i.to_module = m.path
GROUP BY m.id, m.path;

-- Efferent coupling (Ce): outgoing dependencies from a module
CREATE VIEW IF NOT EXISTS efferent_coupling AS
SELECT
    m.id AS module_id,
    m.path AS module_path,
    COUNT(DISTINCT i.to_module) AS efferent_coupling
FROM modules m
LEFT JOIN imports i ON i.from_module_id = m.id
GROUP BY m.id, m.path;

-- Instability metric: Ce / (Ca + Ce)
CREATE VIEW IF NOT EXISTS instability AS
SELECT
    m.id AS module_id,
    m.path AS module_path,
    COALESCE(ec.efferent_coupling, 0) AS ce,
    COALESCE(ac.afferent_coupling, 0) AS ca,
    CASE
        WHEN (COALESCE(ec.efferent_coupling, 0) + COALESCE(ac.afferent_coupling, 0)) = 0 THEN 0
        ELSE CAST(COALESCE(ec.efferent_coupling, 0) AS REAL) /
             (COALESCE(ec.efferent_coupling, 0) + COALESCE(ac.afferent_coupling, 0))
    END AS instability
FROM modules m
LEFT JOIN efferent_coupling ec ON m.id = ec.module_id
LEFT JOIN afferent_coupling ac ON m.id = ac.module_id;

-- Module complexity (sum of function complexities)
CREATE VIEW IF NOT EXISTS module_complexity AS
SELECT
    m.id AS module_id,
    m.path AS module_path,
    COUNT(DISTINCT f.id) AS function_count,
    SUM(f.cyclomatic_complexity) AS total_complexity,
    AVG(f.cyclomatic_complexity) AS avg_complexity,
    MAX(f.cyclomatic_complexity) AS max_complexity
FROM modules m
LEFT JOIN functions f ON f.module_id = m.id
GROUP BY m.id, m.path;
