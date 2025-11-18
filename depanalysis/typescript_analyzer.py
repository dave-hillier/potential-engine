"""
TypeScript/JavaScript analyzer for parsing code structure.

Parses TypeScript and JavaScript files using esprima to extract modules,
classes, functions, and their relationships, populating the structure.db database.
"""
import hashlib
import json
import re
import sqlite3
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Tuple


class TypeScriptAnalyzer:
    """Analyzes TypeScript/JavaScript code structure and populates structure.db."""

    def __init__(self, repo_path: Path, db_connection: sqlite3.Connection):
        """
        Initialize TypeScript analyzer.

        Args:
            repo_path: Path to the repository root
            db_connection: SQLite connection to structure.db
        """
        self.repo_path = Path(repo_path)
        self.conn = db_connection
        self.cursor = self.conn.cursor()

        # Cache language IDs
        self.typescript_lang_id = self._get_language_id('typescript')
        self.javascript_lang_id = self._get_language_id('javascript')

    def _get_language_id(self, language: str) -> int:
        """Get the ID for a language from the database."""
        self.cursor.execute("SELECT id FROM languages WHERE name = ?", (language,))
        result = self.cursor.fetchone()
        if result:
            return result[0]

        # Fallback if not found (should be pre-populated)
        self.cursor.execute("INSERT INTO languages (name) VALUES (?)", (language,))
        return self.cursor.lastrowid

    def analyze(self) -> dict:
        """
        Perform full structural analysis of TypeScript/JavaScript files.

        Returns:
            Dictionary with analysis statistics
        """
        stats = {
            "files_parsed": 0,
            "classes_found": 0,
            "functions_found": 0,
            "imports_found": 0,
            "errors": 0,
            "typescript_files": 0,
            "javascript_files": 0
        }

        # Walk through all TypeScript/JavaScript files
        patterns = ["*.ts", "*.tsx", "*.js", "*.jsx"]
        for pattern in patterns:
            for file_path in self.repo_path.rglob(pattern):
                if self._should_skip_file(file_path):
                    continue

                try:
                    self._analyze_file(file_path, stats)
                    stats["files_parsed"] += 1
                    if pattern.startswith("*.ts"):
                        stats["typescript_files"] += 1
                    else:
                        stats["javascript_files"] += 1
                except Exception as e:
                    # Silently skip problematic files
                    stats["errors"] += 1

        self.conn.commit()
        return stats

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during analysis."""
        skip_dirs = {".git", "node_modules", "dist", "build", "__pycache__",
                    ".next", "coverage", ".cache", "out"}
        skip_patterns = {".min.js", ".bundle.js", ".d.ts"}

        # Skip if in excluded directory
        if any(skip in file_path.parts for skip in skip_dirs):
            return True

        # Skip minified and bundle files
        if any(file_path.name.endswith(pattern) for pattern in skip_patterns):
            return True

        return False

    def _analyze_file(self, file_path: Path, stats: dict) -> None:
        """Analyze a single TypeScript/JavaScript file using regex patterns."""
        # Calculate relative path for storage
        rel_path = str(file_path.relative_to(self.repo_path))

        # Determine language
        is_typescript = file_path.suffix in ['.ts', '.tsx']
        lang_id = self.typescript_lang_id if is_typescript else self.javascript_lang_id

        # Read file content
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return  # Skip binary or weird encoding files

        # Calculate hash
        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Insert module
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO modules
            (language_id, path, name, file_hash, last_parsed)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (lang_id, rel_path, file_path.stem, file_hash)
        )
        module_id = self.cursor.lastrowid

        # Parse using regex patterns (simple fallback approach)
        self._extract_imports(content, module_id, stats)
        self._extract_classes(content, module_id, stats)
        self._extract_functions(content, module_id, stats)

    def _extract_imports(self, content: str, module_id: int, stats: dict) -> None:
        """Extract import statements using regex."""
        # ES6 imports: import { foo } from 'bar'
        es6_import_pattern = r"import\s+(?:{([^}]+)}|(\*\s+as\s+\w+)|\w+)\s+from\s+['\"]([^'\"]+)['\"]"
        # CommonJS require: const foo = require('bar')
        commonjs_pattern = r"(?:const|let|var)\s+(\w+)\s*=\s*require\s*\(['\"]([^'\"]+)['\"]\)"
        # Dynamic imports: import('module')
        dynamic_pattern = r"import\s*\(['\"]([^'\"]+)['\"]\)"

        # Process ES6 imports
        for match in re.finditer(es6_import_pattern, content):
            named_imports = match.group(1)
            namespace_import = match.group(2)
            module_path = match.group(3)

            line_number = content[:match.start()].count('\n') + 1

            if named_imports:
                # Extract individual imports from { a, b, c }
                imports = [imp.strip().split(' as ')[0].strip()
                          for imp in named_imports.split(',')]
                for imp in imports:
                    self._insert_import(module_id, module_path, imp,
                                      'import', line_number, is_dynamic=False)
                    stats["imports_found"] += 1
            elif namespace_import:
                # * as namespace
                alias = namespace_import.split('as')[1].strip() if 'as' in namespace_import else None
                self._insert_import(module_id, module_path, '*',
                                  'import', line_number, is_wildcard=True, alias=alias)
                stats["imports_found"] += 1
            else:
                # Default import
                self._insert_import(module_id, module_path, module_path.split('/')[-1],
                                  'import', line_number)
                stats["imports_found"] += 1

        # Process CommonJS requires
        for match in re.finditer(commonjs_pattern, content):
            alias = match.group(1)
            module_path = match.group(2)
            line_number = content[:match.start()].count('\n') + 1

            self._insert_import(module_id, module_path, module_path.split('/')[-1],
                              'require', line_number, alias=alias)
            stats["imports_found"] += 1

        # Process dynamic imports
        for match in re.finditer(dynamic_pattern, content):
            module_path = match.group(1)
            line_number = content[:match.start()].count('\n') + 1

            self._insert_import(module_id, module_path, module_path.split('/')[-1],
                              'import', line_number, is_dynamic=True)
            stats["imports_found"] += 1

    def _extract_classes(self, content: str, module_id: int, stats: dict) -> None:
        """Extract class definitions using regex."""
        # Class pattern: class ClassName { ... }
        # Also handles: export class ClassName, abstract class, etc.
        class_pattern = r"(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?\s*{"

        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            base_class = match.group(2)
            interfaces = match.group(3)

            line_number = content[:match.start()].count('\n') + 1

            # Find closing brace (simplified - may not work for nested classes)
            start_pos = match.end()
            brace_count = 1
            pos = start_pos
            while pos < len(content) and brace_count > 0:
                if content[pos] == '{':
                    brace_count += 1
                elif content[pos] == '}':
                    brace_count -= 1
                pos += 1

            end_line = content[:pos].count('\n') + 1

            # Insert class
            self.cursor.execute(
                """
                INSERT INTO classes
                (module_id, name, kind, line_start, line_end)
                VALUES (?, ?, 'class', ?, ?)
                """,
                (module_id, class_name, line_number, end_line)
            )
            class_id = self.cursor.lastrowid
            stats["classes_found"] += 1

            # Insert inheritance relationships
            if base_class:
                self.cursor.execute(
                    """
                    INSERT INTO inheritance
                    (class_id, base_class_name, relationship_kind, position)
                    VALUES (?, ?, 'extends', 0)
                    """,
                    (class_id, base_class)
                )

            if interfaces:
                for idx, interface in enumerate(interfaces.split(',')):
                    interface = interface.strip()
                    self.cursor.execute(
                        """
                        INSERT INTO inheritance
                        (class_id, base_class_name, relationship_kind, position)
                        VALUES (?, ?, 'implements', ?)
                        """,
                        (class_id, interface, idx)
                    )

    def _extract_functions(self, content: str, module_id: int, stats: dict) -> None:
        """Extract function definitions using regex."""
        # Function patterns:
        # - function name() {}
        # - const name = () => {}
        # - async function name() {}
        # - name() {} (method shorthand)

        function_patterns = [
            r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\([^)]*\)\s*{",
            r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>\s*{",
            r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\s*\([^)]*\)\s*{",
        ]

        for pattern in function_patterns:
            for match in re.finditer(pattern, content):
                func_name = match.group(1)
                line_number = content[:match.start()].count('\n') + 1
                is_async = 'async' in match.group(0)

                # Find closing brace (simplified)
                start_pos = match.end()
                brace_count = 1
                pos = start_pos
                while pos < len(content) and brace_count > 0:
                    if content[pos] == '{':
                        brace_count += 1
                    elif content[pos] == '}':
                        brace_count -= 1
                    pos += 1

                end_line = content[:pos].count('\n') + 1

                kind = 'async_function' if is_async else 'function'

                # Insert function
                self.cursor.execute(
                    """
                    INSERT INTO functions
                    (module_id, name, kind, line_start, line_end, is_async)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (module_id, func_name, kind, line_number, end_line, is_async)
                )
                stats["functions_found"] += 1

    def _insert_import(self, module_id: int, to_module: str, import_name: str,
                      kind: str, lineno: int, is_dynamic: bool = False,
                      is_wildcard: bool = False, alias: Optional[str] = None) -> None:
        """Insert import record."""
        is_relative = to_module.startswith('./')  or to_module.startswith('../')

        self.cursor.execute(
            """
            INSERT INTO imports
            (from_module_id, to_module, import_name, alias, import_kind,
             is_relative, is_dynamic, is_wildcard, line_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (module_id, to_module, import_name, alias, kind,
             is_relative, is_dynamic, is_wildcard, lineno)
        )
