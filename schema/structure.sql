-- structure.db schema
-- Contains AST-parsed structural relationships from source code
-- Supports multiple programming languages through language-agnostic core with language-specific extensions

-- =============================================================================
-- LANGUAGE SUPPORT
-- =============================================================================

CREATE TABLE IF NOT EXISTS languages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    version TEXT,
    CONSTRAINT valid_language CHECK (name IN ('python', 'typescript', 'javascript', 'csharp', 'java', 'rust', 'cpp', 'go'))
);

-- Pre-populate supported languages
INSERT OR IGNORE INTO languages (id, name) VALUES
    (1, 'python'),
    (2, 'typescript'),
    (3, 'javascript'),
    (4, 'csharp'),
    (5, 'java'),
    (6, 'rust'),
    (7, 'cpp'),
    (8, 'go');

-- =============================================================================
-- CORE ENTITIES (Language-Agnostic)
-- =============================================================================

-- Modules/Files - Source code files
-- Universal: All languages have files as compilation/module units
CREATE TABLE IF NOT EXISTS modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id INTEGER NOT NULL DEFAULT 1,
    path TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    last_parsed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (language_id) REFERENCES languages(id) ON DELETE RESTRICT,
    CONSTRAINT valid_path CHECK (length(path) > 0)
);

CREATE INDEX idx_modules_path ON modules(path);
CREATE INDEX idx_modules_hash ON modules(file_hash);
CREATE INDEX idx_modules_language ON modules(language_id);
CREATE INDEX idx_modules_name ON modules(name);

-- Classes/Types - Object-oriented types, structs, interfaces, traits
-- Maps to: Python class, TypeScript class/interface, C# class/interface/struct,
--          Java class/interface, Rust struct/enum/trait, C++ class/struct
CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    qualified_name TEXT,
    kind TEXT CHECK (kind IN ('class', 'interface', 'struct', 'trait', 'enum', 'protocol', 'abstract_class', 'type_alias')),
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    docstring TEXT,
    is_abstract BOOLEAN DEFAULT 0,
    is_generic BOOLEAN DEFAULT 0,
    FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE,
    CONSTRAINT valid_lines CHECK (line_end >= line_start)
);

CREATE INDEX idx_classes_module ON classes(module_id);
CREATE INDEX idx_classes_name ON classes(name);
CREATE INDEX idx_classes_qualified ON classes(qualified_name);
CREATE INDEX idx_classes_kind ON classes(kind);

-- Functions/Methods - Callable units of code
-- Maps to: functions, methods, procedures across all languages
CREATE TABLE IF NOT EXISTS functions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    class_id INTEGER,
    name TEXT NOT NULL,
    qualified_name TEXT,
    kind TEXT CHECK (kind IN ('function', 'method', 'constructor', 'destructor', 'lambda', 'closure', 'property', 'async_function')),
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    docstring TEXT,
    cyclomatic_complexity INTEGER DEFAULT 1,
    is_static BOOLEAN DEFAULT 0,
    is_async BOOLEAN DEFAULT 0,
    is_abstract BOOLEAN DEFAULT 0,
    FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    CONSTRAINT valid_lines CHECK (line_end >= line_start),
    CONSTRAINT valid_complexity CHECK (cyclomatic_complexity >= 1)
);

CREATE INDEX idx_functions_module ON functions(module_id);
CREATE INDEX idx_functions_class ON functions(class_id);
CREATE INDEX idx_functions_name ON functions(name);
CREATE INDEX idx_functions_qualified ON functions(qualified_name);
CREATE INDEX idx_functions_complexity ON functions(cyclomatic_complexity);
CREATE INDEX idx_functions_kind ON functions(kind);

-- Variables/Fields/Properties - Data storage entities
-- Maps to: variables, fields, properties, constants across all languages
CREATE TABLE IF NOT EXISTS variables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    class_id INTEGER,
    function_id INTEGER,
    name TEXT NOT NULL,
    kind TEXT CHECK (kind IN ('field', 'property', 'constant', 'local', 'parameter', 'global')),
    line_number INTEGER NOT NULL,
    is_static BOOLEAN DEFAULT 0,
    is_const BOOLEAN DEFAULT 0,
    FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (function_id) REFERENCES functions(id) ON DELETE CASCADE
);

CREATE INDEX idx_variables_module ON variables(module_id);
CREATE INDEX idx_variables_class ON variables(class_id);
CREATE INDEX idx_variables_function ON variables(function_id);
CREATE INDEX idx_variables_name ON variables(name);
CREATE INDEX idx_variables_kind ON variables(kind);

-- =============================================================================
-- RELATIONSHIP TABLES (Language-Agnostic)
-- =============================================================================

-- Imports/Dependencies/Using/Include statements
-- Maps to: Python import, TypeScript import, C# using, Java import,
--          Rust use, C++ #include, Go import
CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_module_id INTEGER NOT NULL,
    to_module TEXT NOT NULL,
    import_name TEXT NOT NULL,
    alias TEXT,
    import_kind TEXT CHECK (import_kind IN ('import', 'require', 'using', 'include', 'use')),
    is_relative BOOLEAN DEFAULT 0,
    is_dynamic BOOLEAN DEFAULT 0,
    is_wildcard BOOLEAN DEFAULT 0,
    line_number INTEGER NOT NULL,
    FOREIGN KEY (from_module_id) REFERENCES modules(id) ON DELETE CASCADE
);

CREATE INDEX idx_imports_from ON imports(from_module_id);
CREATE INDEX idx_imports_to ON imports(to_module);
CREATE INDEX idx_imports_name ON imports(import_name);
CREATE INDEX idx_imports_kind ON imports(import_kind);

-- Function/Method calls
-- Universal: All languages have function invocation
CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_function_id INTEGER NOT NULL,
    to_function_id INTEGER,
    to_name TEXT NOT NULL,
    call_kind TEXT CHECK (call_kind IN ('call', 'invoke', 'construct', 'async_call')),
    line_number INTEGER NOT NULL,
    FOREIGN KEY (from_function_id) REFERENCES functions(id) ON DELETE CASCADE,
    FOREIGN KEY (to_function_id) REFERENCES functions(id) ON DELETE CASCADE
);

CREATE INDEX idx_calls_from ON calls(from_function_id);
CREATE INDEX idx_calls_to ON calls(to_function_id);
CREATE INDEX idx_calls_to_name ON calls(to_name);
CREATE INDEX idx_calls_kind ON calls(call_kind);

-- Inheritance/Extension/Implementation relationships
-- Maps to: Python inheritance, TypeScript extends/implements, C# : base,
--          Java extends/implements, Rust trait implementation
CREATE TABLE IF NOT EXISTS inheritance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    base_class_id INTEGER,
    base_class_name TEXT NOT NULL,
    relationship_kind TEXT CHECK (relationship_kind IN ('inherits', 'implements', 'extends', 'trait_impl')),
    position INTEGER NOT NULL,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (base_class_id) REFERENCES classes(id) ON DELETE CASCADE,
    CONSTRAINT valid_position CHECK (position >= 0)
);

CREATE INDEX idx_inheritance_class ON inheritance(class_id);
CREATE INDEX idx_inheritance_base ON inheritance(base_class_id);
CREATE INDEX idx_inheritance_base_name ON inheritance(base_class_name);
CREATE INDEX idx_inheritance_kind ON inheritance(relationship_kind);

-- =============================================================================
-- LANGUAGE-SPECIFIC FEATURES
-- =============================================================================

-- Decorators/Annotations/Attributes
-- Primary languages: Python (@decorator), TypeScript (@decorator), C# ([Attribute]), Java (@Annotation)
-- Also applicable: Rust procedural macros
CREATE TABLE IF NOT EXISTS decorators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type TEXT NOT NULL CHECK (target_type IN ('function', 'class', 'variable', 'parameter')),
    target_id INTEGER NOT NULL,
    decorator_name TEXT NOT NULL,
    arguments TEXT,
    line_number INTEGER NOT NULL
);

CREATE INDEX idx_decorators_target ON decorators(target_type, target_id);
CREATE INDEX idx_decorators_name ON decorators(decorator_name);

-- Type Hints/Annotations
-- Primary languages: Python (type hints), TypeScript (type annotations), Java (generics), C# (generics)
-- Also applicable: Rust (type annotations), C++ (in comments or modern syntax)
CREATE TABLE IF NOT EXISTS type_hints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    function_id INTEGER,
    variable_id INTEGER,
    hint_type TEXT NOT NULL CHECK (hint_type IN ('parameter', 'return', 'variable', 'generic')),
    parameter_name TEXT,
    type_annotation TEXT NOT NULL,
    is_nullable BOOLEAN DEFAULT 0,
    is_optional BOOLEAN DEFAULT 0,
    FOREIGN KEY (function_id) REFERENCES functions(id) ON DELETE CASCADE,
    FOREIGN KEY (variable_id) REFERENCES variables(id) ON DELETE CASCADE,
    CONSTRAINT has_target CHECK (
        (function_id IS NOT NULL) OR (variable_id IS NOT NULL)
    )
);

CREATE INDEX idx_type_hints_function ON type_hints(function_id);
CREATE INDEX idx_type_hints_variable ON type_hints(variable_id);
CREATE INDEX idx_type_hints_type ON type_hints(hint_type);

-- Generic/Template Parameters
-- For languages with parameterized types: TypeScript, C#, Java, C++, Rust
CREATE TABLE IF NOT EXISTS generic_parameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_type TEXT NOT NULL CHECK (owner_type IN ('class', 'function')),
    owner_id INTEGER NOT NULL,
    parameter_name TEXT NOT NULL,
    position INTEGER NOT NULL,
    constraint_expression TEXT,
    default_value TEXT,
    CONSTRAINT valid_position CHECK (position >= 0)
);

CREATE INDEX idx_generic_params_owner ON generic_parameters(owner_type, owner_id);

-- Language-specific metadata (flexible key-value storage)
-- Use for language-specific features that don't warrant dedicated tables
-- Examples: Rust lifetimes, Python metaclasses, C# partial classes, etc.
CREATE TABLE IF NOT EXISTS language_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('module', 'class', 'function', 'variable')),
    entity_id INTEGER NOT NULL,
    language_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    FOREIGN KEY (language_id) REFERENCES languages(id) ON DELETE CASCADE,
    CONSTRAINT unique_metadata UNIQUE (entity_type, entity_id, key)
);

CREATE INDEX idx_language_metadata_entity ON language_metadata(entity_type, entity_id);
CREATE INDEX idx_language_metadata_key ON language_metadata(key);
CREATE INDEX idx_language_metadata_language ON language_metadata(language_id);

-- =============================================================================
-- MATERIALIZED VIEWS (Language-Agnostic Metrics)
-- =============================================================================

-- Afferent coupling (Ca): incoming dependencies to a module
CREATE VIEW IF NOT EXISTS afferent_coupling AS
SELECT
    m.id AS module_id,
    m.path AS module_path,
    l.name AS language,
    COUNT(DISTINCT i.from_module_id) AS afferent_coupling
FROM modules m
LEFT JOIN languages l ON m.language_id = l.id
LEFT JOIN imports i ON i.to_module = m.name OR i.to_module = m.path
GROUP BY m.id, m.path, l.name;

-- Efferent coupling (Ce): outgoing dependencies from a module
CREATE VIEW IF NOT EXISTS efferent_coupling AS
SELECT
    m.id AS module_id,
    m.path AS module_path,
    l.name AS language,
    COUNT(DISTINCT i.to_module) AS efferent_coupling
FROM modules m
LEFT JOIN languages l ON m.language_id = l.id
LEFT JOIN imports i ON i.from_module_id = m.id
GROUP BY m.id, m.path, l.name;

-- Instability metric: Ce / (Ca + Ce)
CREATE VIEW IF NOT EXISTS instability AS
SELECT
    m.id AS module_id,
    m.path AS module_path,
    l.name AS language,
    COALESCE(ec.efferent_coupling, 0) AS ce,
    COALESCE(ac.afferent_coupling, 0) AS ca,
    CASE
        WHEN (COALESCE(ec.efferent_coupling, 0) + COALESCE(ac.afferent_coupling, 0)) = 0 THEN 0
        ELSE CAST(COALESCE(ec.efferent_coupling, 0) AS REAL) /
             (COALESCE(ec.efferent_coupling, 0) + COALESCE(ac.afferent_coupling, 0))
    END AS instability
FROM modules m
LEFT JOIN languages l ON m.language_id = l.id
LEFT JOIN efferent_coupling ec ON m.id = ec.module_id
LEFT JOIN afferent_coupling ac ON m.id = ac.module_id;

-- Module complexity (sum of function complexities)
CREATE VIEW IF NOT EXISTS module_complexity AS
SELECT
    m.id AS module_id,
    m.path AS module_path,
    l.name AS language,
    COUNT(DISTINCT f.id) AS function_count,
    SUM(f.cyclomatic_complexity) AS total_complexity,
    AVG(f.cyclomatic_complexity) AS avg_complexity,
    MAX(f.cyclomatic_complexity) AS max_complexity
FROM modules m
LEFT JOIN languages l ON m.language_id = l.id
LEFT JOIN functions f ON f.module_id = m.id
GROUP BY m.id, m.path, l.name;

-- Language distribution in repository
CREATE VIEW IF NOT EXISTS language_stats AS
SELECT
    l.name AS language,
    COUNT(DISTINCT m.id) AS file_count,
    SUM(COALESCE(mc.function_count, 0)) AS total_functions,
    AVG(COALESCE(mc.total_complexity, 0)) AS avg_file_complexity
FROM languages l
LEFT JOIN modules m ON m.language_id = l.id
LEFT JOIN module_complexity mc ON mc.module_id = m.id
GROUP BY l.name
HAVING file_count > 0;
