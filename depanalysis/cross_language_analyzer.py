"""
Cross-language dependency analyzer.

Detects dependencies and relationships across different programming languages:
- API boundaries (REST endpoints, GraphQL, gRPC)
- Shared type definitions (Protocol Buffers, JSON schemas)
- Monorepo package dependencies
- Microservice coupling patterns
"""
import json
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional


class CrossLanguageAnalyzer:
    """
    Analyzes cross-language dependencies and API boundaries.

    Detects patterns like:
    - Python Flask/FastAPI routes called by TypeScript fetch()
    - Protocol Buffer definitions shared across languages
    - GraphQL schemas used by multiple services
    - Configuration files referencing different language modules
    """

    def __init__(self, repo_path: Path, structure_db: sqlite3.Connection,
                 history_db: Optional[sqlite3.Connection] = None):
        """
        Initialize cross-language analyzer.

        Args:
            repo_path: Path to the repository root
            structure_db: SQLite connection to structure.db
            history_db: Optional SQLite connection to history.db for temporal analysis
        """
        self.repo_path = Path(repo_path)
        self.structure_db = structure_db
        self.history_db = history_db
        self.cursor = structure_db.cursor()

        # Create cross-language tables if they don't exist
        self._initialize_tables()

    def _initialize_tables(self) -> None:
        """Create tables for cross-language dependencies."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_endpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id INTEGER NOT NULL,
                endpoint_type TEXT CHECK (endpoint_type IN ('rest', 'graphql', 'grpc', 'websocket')),
                method TEXT,
                path TEXT NOT NULL,
                handler_function_id INTEGER,
                line_number INTEGER NOT NULL,
                FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE,
                FOREIGN KEY (handler_function_id) REFERENCES functions(id) ON DELETE SET NULL
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_module_id INTEGER NOT NULL,
                from_function_id INTEGER,
                call_type TEXT CHECK (call_type IN ('fetch', 'axios', 'http', 'grpc', 'websocket')),
                method TEXT,
                url_pattern TEXT NOT NULL,
                line_number INTEGER NOT NULL,
                FOREIGN KEY (from_module_id) REFERENCES modules(id) ON DELETE CASCADE,
                FOREIGN KEY (from_function_id) REFERENCES functions(id) ON DELETE SET NULL
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS shared_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type_system TEXT CHECK (type_system IN ('protobuf', 'graphql', 'json_schema', 'openapi', 'thrift')),
                name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                definition TEXT
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS type_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shared_type_id INTEGER NOT NULL,
                module_id INTEGER NOT NULL,
                usage_type TEXT CHECK (usage_type IN ('import', 'implement', 'extend', 'reference')),
                line_number INTEGER,
                FOREIGN KEY (shared_type_id) REFERENCES shared_types(id) ON DELETE CASCADE,
                FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
            )
        """)

        # Create indexes
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_endpoints_module ON api_endpoints(module_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_endpoints_path ON api_endpoints(path)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_calls_module ON api_calls(from_module_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_calls_url ON api_calls(url_pattern)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_shared_types_name ON shared_types(name)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_type_usage_type ON type_usage(shared_type_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_type_usage_module ON type_usage(module_id)")

        self.structure_db.commit()

    def analyze(self) -> Dict[str, int]:
        """
        Perform cross-language dependency analysis.

        Returns:
            Dictionary with analysis statistics
        """
        stats = {
            "api_endpoints_found": 0,
            "api_calls_found": 0,
            "shared_types_found": 0,
            "type_usages_found": 0,
            "proto_files": 0,
            "graphql_files": 0,
            "openapi_files": 0
        }

        # Analyze Python API endpoints
        stats["api_endpoints_found"] += self._analyze_python_apis()

        # Analyze TypeScript/JavaScript API calls
        stats["api_calls_found"] += self._analyze_js_api_calls()

        # Analyze shared type definitions
        proto_stats = self._analyze_protocol_buffers()
        stats["shared_types_found"] += proto_stats["types"]
        stats["proto_files"] += proto_stats["files"]

        graphql_stats = self._analyze_graphql_schemas()
        stats["shared_types_found"] += graphql_stats["types"]
        stats["graphql_files"] += graphql_stats["files"]

        openapi_stats = self._analyze_openapi_specs()
        stats["shared_types_found"] += openapi_stats["types"]
        stats["openapi_files"] += openapi_stats["files"]

        self.structure_db.commit()
        return stats

    def _analyze_python_apis(self) -> int:
        """Analyze Python Flask/FastAPI/Django route definitions."""
        count = 0

        # Get all Python modules
        modules = self.cursor.execute("""
            SELECT m.id, m.path
            FROM modules m
            JOIN languages l ON m.language_id = l.id
            WHERE l.name = 'python'
        """).fetchall()

        for module_id, module_path in modules:
            file_path = self.repo_path / module_path
            if not file_path.exists():
                continue

            try:
                content = file_path.read_text(encoding='utf-8')
            except:
                continue

            # Flask routes: @app.route('/path', methods=['GET'])
            flask_pattern = r"@(?:app|bp|blueprint)\.route\(['\"]([^'\"]+)['\"](?:,\s*methods\s*=\s*\[([^\]]+)\])?\)"

            # FastAPI routes: @app.get('/path')
            fastapi_pattern = r"@app\.(get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]\)"

            # Django URL patterns: path('endpoint/', view)
            django_pattern = r"path\(['\"]([^'\"]+)['\"]\s*,\s*(\w+)"

            for match in re.finditer(flask_pattern, content):
                path = match.group(1)
                methods = match.group(2) or 'GET'
                line_number = content[:match.start()].count('\n') + 1

                for method in methods.replace("'", "").replace('"', "").split(','):
                    self.cursor.execute("""
                        INSERT INTO api_endpoints
                        (module_id, endpoint_type, method, path, line_number)
                        VALUES (?, 'rest', ?, ?, ?)
                    """, (module_id, method.strip(), path, line_number))
                    count += 1

            for match in re.finditer(fastapi_pattern, content):
                method = match.group(1).upper()
                path = match.group(2)
                line_number = content[:match.start()].count('\n') + 1

                self.cursor.execute("""
                    INSERT INTO api_endpoints
                    (module_id, endpoint_type, method, path, line_number)
                    VALUES (?, 'rest', ?, ?, ?)
                """, (module_id, method, path, line_number))
                count += 1

        return count

    def _analyze_js_api_calls(self) -> int:
        """Analyze JavaScript/TypeScript fetch/axios API calls."""
        count = 0

        # Get all JS/TS modules
        modules = self.cursor.execute("""
            SELECT m.id, m.path
            FROM modules m
            JOIN languages l ON m.language_id = l.id
            WHERE l.name IN ('typescript', 'javascript')
        """).fetchall()

        for module_id, module_path in modules:
            file_path = self.repo_path / module_path
            if not file_path.exists():
                continue

            try:
                content = file_path.read_text(encoding='utf-8')
            except:
                continue

            # fetch API: fetch('/api/endpoint', { method: 'POST' })
            fetch_pattern = r"fetch\s*\(\s*['\"]([^'\"]+)['\"](?:\s*,\s*\{[^}]*method\s*:\s*['\"](\w+)['\"])?";

            # axios: axios.get('/api/endpoint')
            axios_pattern = r"axios\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]"

            for match in re.finditer(fetch_pattern, content):
                url = match.group(1)
                method = match.group(2) or 'GET'
                line_number = content[:match.start()].count('\n') + 1

                self.cursor.execute("""
                    INSERT INTO api_calls
                    (from_module_id, call_type, method, url_pattern, line_number)
                    VALUES (?, 'fetch', ?, ?, ?)
                """, (module_id, method.upper(), url, line_number))
                count += 1

            for match in re.finditer(axios_pattern, content):
                method = match.group(1).upper()
                url = match.group(2)
                line_number = content[:match.start()].count('\n') + 1

                self.cursor.execute("""
                    INSERT INTO api_calls
                    (from_module_id, call_type, method, url_pattern, line_number)
                    VALUES (?, 'axios', ?, ?, ?)
                """, (module_id, method, url, line_number))
                count += 1

        return count

    def _analyze_protocol_buffers(self) -> Dict[str, int]:
        """Analyze Protocol Buffer definitions."""
        stats = {"files": 0, "types": 0}

        for proto_file in self.repo_path.rglob("*.proto"):
            if any(skip in proto_file.parts for skip in ['.git', 'node_modules', 'venv']):
                continue

            try:
                content = proto_file.read_text(encoding='utf-8')
            except:
                continue

            stats["files"] += 1
            rel_path = str(proto_file.relative_to(self.repo_path))

            # Extract message definitions: message MessageName { ... }
            message_pattern = r"message\s+(\w+)\s*\{"

            for match in re.finditer(message_pattern, content):
                message_name = match.group(1)
                line_number = content[:match.start()].count('\n') + 1

                # Find full definition
                start_pos = match.end()
                brace_count = 1
                pos = start_pos
                while pos < len(content) and brace_count > 0:
                    if content[pos] == '{':
                        brace_count += 1
                    elif content[pos] == '}':
                        brace_count -= 1
                    pos += 1

                definition = content[match.start():pos]

                self.cursor.execute("""
                    INSERT INTO shared_types
                    (type_system, name, file_path, definition)
                    VALUES ('protobuf', ?, ?, ?)
                """, (message_name, rel_path, definition))
                stats["types"] += 1

        return stats

    def _analyze_graphql_schemas(self) -> Dict[str, int]:
        """Analyze GraphQL schema definitions."""
        stats = {"files": 0, "types": 0}

        for gql_file in self.repo_path.rglob("*.graphql"):
            if any(skip in gql_file.parts for skip in ['.git', 'node_modules', 'venv']):
                continue

            try:
                content = gql_file.read_text(encoding='utf-8')
            except:
                continue

            stats["files"] += 1
            rel_path = str(gql_file.relative_to(self.repo_path))

            # Extract type definitions: type TypeName { ... }
            type_pattern = r"type\s+(\w+)\s*\{"

            for match in re.finditer(type_pattern, content):
                type_name = match.group(1)

                # Find full definition
                start_pos = match.end()
                brace_count = 1
                pos = start_pos
                while pos < len(content) and brace_count > 0:
                    if content[pos] == '{':
                        brace_count += 1
                    elif content[pos] == '}':
                        brace_count -= 1
                    pos += 1

                definition = content[match.start():pos]

                self.cursor.execute("""
                    INSERT INTO shared_types
                    (type_system, name, file_path, definition)
                    VALUES ('graphql', ?, ?, ?)
                """, (type_name, rel_path, definition))
                stats["types"] += 1

        return stats

    def _analyze_openapi_specs(self) -> Dict[str, int]:
        """Analyze OpenAPI/Swagger specifications."""
        stats = {"files": 0, "types": 0}

        openapi_patterns = ["*openapi*.yaml", "*openapi*.json", "*swagger*.yaml", "*swagger*.json"]

        for pattern in openapi_patterns:
            for spec_file in self.repo_path.rglob(pattern):
                if any(skip in spec_file.parts for skip in ['.git', 'node_modules', 'venv']):
                    continue

                try:
                    content = spec_file.read_text(encoding='utf-8')
                    if spec_file.suffix == '.json':
                        spec = json.loads(content)
                    else:
                        # Simple YAML parsing fallback - would need pyyaml for full support
                        continue
                except:
                    continue

                stats["files"] += 1
                rel_path = str(spec_file.relative_to(self.repo_path))

                # Extract schema definitions
                if 'components' in spec and 'schemas' in spec['components']:
                    for schema_name, schema_def in spec['components']['schemas'].items():
                        self.cursor.execute("""
                            INSERT INTO shared_types
                            (type_system, name, file_path, definition)
                            VALUES ('openapi', ?, ?, ?)
                        """, (schema_name, rel_path, json.dumps(schema_def)))
                        stats["types"] += 1

        return stats

    def get_api_boundary_coupling(self) -> List[Dict]:
        """
        Analyze coupling across API boundaries.

        Returns:
            List of API call patterns matched to endpoints
        """
        results = self.cursor.execute("""
            SELECT
                calls.url_pattern,
                calls.method,
                calls.call_type,
                m1.path as caller_module,
                l1.name as caller_language,
                endpoints.path as endpoint_path,
                endpoints.method as endpoint_method,
                m2.path as endpoint_module,
                l2.name as endpoint_language
            FROM api_calls calls
            JOIN modules m1 ON calls.from_module_id = m1.id
            JOIN languages l1 ON m1.language_id = l1.id
            LEFT JOIN api_endpoints endpoints ON
                calls.url_pattern LIKE '%' || endpoints.path || '%'
                AND calls.method = endpoints.method
            LEFT JOIN modules m2 ON endpoints.module_id = m2.id
            LEFT JOIN languages l2 ON m2.language_id = l2.id
        """).fetchall()

        return [
            {
                "url_pattern": row[0],
                "method": row[1],
                "call_type": row[2],
                "caller_module": row[3],
                "caller_language": row[4],
                "endpoint_path": row[5],
                "endpoint_method": row[6],
                "endpoint_module": row[7],
                "endpoint_language": row[8]
            }
            for row in results
        ]
