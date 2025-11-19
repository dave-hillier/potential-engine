"""
C# analyzer for parsing code structure.

Parses C# files using regex patterns to extract namespaces, classes, methods,
properties, and their relationships, populating the structure.db database.
"""
import hashlib
import re
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Tuple


class CSharpAnalyzer:
    """Analyzes C# code structure and populates structure.db."""

    def __init__(self, repo_path: Path, db_connection: sqlite3.Connection):
        """
        Initialize C# analyzer.

        Args:
            repo_path: Path to the repository root
            db_connection: SQLite connection to structure.db
        """
        self.repo_path = Path(repo_path)
        self.conn = db_connection
        self.cursor = self.conn.cursor()

        # Cache language ID
        self.csharp_lang_id = self._get_language_id('csharp')

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
        Perform full structural analysis of C# files.

        Returns:
            Dictionary with analysis statistics
        """
        stats = {
            "files_parsed": 0,
            "classes_found": 0,
            "interfaces_found": 0,
            "structs_found": 0,
            "enums_found": 0,
            "methods_found": 0,
            "properties_found": 0,
            "fields_found": 0,
            "using_statements_found": 0,
            "errors": 0
        }

        # Walk through all C# files
        for file_path in self.repo_path.rglob("*.cs"):
            if self._should_skip_file(file_path):
                continue

            try:
                self._analyze_file(file_path, stats)
                stats["files_parsed"] += 1
            except Exception as e:
                # Silently skip problematic files
                stats["errors"] += 1

        self.conn.commit()
        return stats

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during analysis."""
        skip_dirs = {".git", "bin", "obj", "packages", ".vs", "node_modules",
                    "__pycache__", "TestResults", "Debug", "Release"}
        skip_patterns = {".g.cs", ".designer.cs", ".generated.cs"}

        # Skip if in excluded directory
        if any(skip in file_path.parts for skip in skip_dirs):
            return True

        # Skip generated files
        if any(file_path.name.lower().endswith(pattern) for pattern in skip_patterns):
            return True

        return False

    def _analyze_file(self, file_path: Path, stats: dict) -> None:
        """Analyze a single C# file using regex patterns."""
        # Calculate relative path for storage
        rel_path = str(file_path.relative_to(self.repo_path))

        # Read file content
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return  # Skip binary or weird encoding files

        # Remove comments to avoid false matches
        content_no_comments = self._remove_comments(content)

        # Calculate hash
        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Insert module
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO modules
            (language_id, path, name, file_hash, last_parsed)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (self.csharp_lang_id, rel_path, file_path.stem, file_hash)
        )
        module_id = self.cursor.lastrowid

        # Extract namespace (for context)
        namespace = self._extract_namespace(content_no_comments)

        # Parse using regex patterns
        self._extract_using_statements(content_no_comments, module_id, stats)
        self._extract_classes(content_no_comments, module_id, namespace, stats)
        self._extract_interfaces(content_no_comments, module_id, namespace, stats)
        self._extract_structs(content_no_comments, module_id, namespace, stats)
        self._extract_enums(content_no_comments, module_id, namespace, stats)

    def _remove_comments(self, content: str) -> str:
        """Remove single-line and multi-line comments from C# code."""
        # Remove multi-line comments /* ... */
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # Remove single-line comments //
        content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
        return content

    def _extract_namespace(self, content: str) -> Optional[str]:
        """Extract the namespace from the file."""
        # Modern file-scoped namespace: namespace MyApp.Features;
        match = re.search(r'namespace\s+([\w.]+)\s*;', content)
        if match:
            return match.group(1)

        # Traditional namespace: namespace MyApp.Features { ... }
        match = re.search(r'namespace\s+([\w.]+)\s*{', content)
        if match:
            return match.group(1)

        return None

    def _extract_using_statements(self, content: str, module_id: int, stats: dict) -> None:
        """Extract using statements (imports) using regex."""
        # using System.Collections.Generic;
        # using static System.Math;
        # using Alias = System.Text;
        using_pattern = r'using\s+(?:static\s+)?([\w.]+)(?:\s*=\s*([\w.]+))?\s*;'

        for match in re.finditer(using_pattern, content):
            namespace_or_alias = match.group(1)
            aliased_namespace = match.group(2)
            line_number = content[:match.start()].count('\n') + 1

            # Determine the actual import
            import_name = aliased_namespace if aliased_namespace else namespace_or_alias
            alias = namespace_or_alias if aliased_namespace else None

            is_static = 'static' in match.group(0)

            self._insert_import(
                module_id,
                import_name,
                import_name.split('.')[-1],  # Last part as name
                'using',
                line_number,
                alias=alias
            )
            stats["using_statements_found"] += 1

    def _extract_classes(self, content: str, module_id: int, namespace: Optional[str],
                        stats: dict) -> None:
        """Extract class definitions using regex."""
        # Class pattern with various modifiers and inheritance
        # [attributes] public class ClassName : BaseClass, IInterface1, IInterface2 { ... }
        class_pattern = r'''
            (?:\[[\s\S]*?\]\s*)?                    # Optional attributes
            (?:public|internal|private|protected)?\s*  # Access modifier
            (?:static\s+|sealed\s+|abstract\s+|partial\s+)*  # Class modifiers
            class\s+
            (\w+)                                   # Class name
            (?:<[\w\s,]+>)?                         # Optional generic parameters
            (?:\s*:\s*([\w\s,.<>]+))?               # Optional base class and interfaces
            \s*(?:where\s+[\w\s:,]+)?\s*            # Optional generic constraints
            \{                                      # Opening brace
        '''

        for match in re.finditer(class_pattern, content, re.VERBOSE):
            class_name = match.group(1)
            inheritance = match.group(2)

            line_number = content[:match.start()].count('\n') + 1

            # Find closing brace
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

            # Determine if it's abstract, sealed, or static
            match_text = match.group(0)
            kind = 'class'
            if 'abstract' in match_text:
                kind = 'abstract_class'
            elif 'static' in match_text:
                kind = 'static_class'
            elif 'sealed' in match_text:
                kind = 'sealed_class'

            # Build fully qualified name
            full_name = f"{namespace}.{class_name}" if namespace else class_name

            # Insert class
            self.cursor.execute(
                """
                INSERT INTO classes
                (module_id, name, kind, line_start, line_end)
                VALUES (?, ?, ?, ?, ?)
                """,
                (module_id, full_name, kind, line_number, end_line)
            )
            class_id = self.cursor.lastrowid
            stats["classes_found"] += 1

            # Insert inheritance relationships
            if inheritance:
                self._insert_inheritance(class_id, inheritance)

            # Extract class body (methods, properties, fields)
            class_body = content[match.end():pos]
            self._extract_methods(class_body, module_id, class_id, line_number, stats)
            self._extract_properties(class_body, module_id, class_id, line_number, stats)
            self._extract_fields(class_body, module_id, class_id, line_number, stats)

    def _extract_interfaces(self, content: str, module_id: int, namespace: Optional[str],
                           stats: dict) -> None:
        """Extract interface definitions using regex."""
        interface_pattern = r'''
            (?:\[[\s\S]*?\]\s*)?                    # Optional attributes
            (?:public|internal|private|protected)?\s*
            interface\s+
            (\w+)                                   # Interface name
            (?:<[\w\s,]+>)?                         # Optional generic parameters
            (?:\s*:\s*([\w\s,.<>]+))?               # Optional base interfaces
            \s*\{
        '''

        for match in re.finditer(interface_pattern, content, re.VERBOSE):
            interface_name = match.group(1)
            inheritance = match.group(2)

            line_number = content[:match.start()].count('\n') + 1

            # Find closing brace
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

            # Build fully qualified name
            full_name = f"{namespace}.{interface_name}" if namespace else interface_name

            # Insert interface as a class with kind='interface'
            self.cursor.execute(
                """
                INSERT INTO classes
                (module_id, name, kind, line_start, line_end)
                VALUES (?, ?, 'interface', ?, ?)
                """,
                (module_id, full_name, line_number, end_line)
            )
            class_id = self.cursor.lastrowid
            stats["interfaces_found"] += 1

            # Insert inheritance relationships
            if inheritance:
                self._insert_inheritance(class_id, inheritance)

    def _extract_structs(self, content: str, module_id: int, namespace: Optional[str],
                        stats: dict) -> None:
        """Extract struct definitions using regex."""
        struct_pattern = r'''
            (?:\[[\s\S]*?\]\s*)?                    # Optional attributes
            (?:public|internal|private|protected)?\s*
            (?:readonly\s+)?
            struct\s+
            (\w+)                                   # Struct name
            (?:<[\w\s,]+>)?                         # Optional generic parameters
            (?:\s*:\s*([\w\s,.<>]+))?               # Optional interfaces
            \s*\{
        '''

        for match in re.finditer(struct_pattern, content, re.VERBOSE):
            struct_name = match.group(1)
            inheritance = match.group(2)

            line_number = content[:match.start()].count('\n') + 1

            # Find closing brace
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

            # Build fully qualified name
            full_name = f"{namespace}.{struct_name}" if namespace else struct_name

            # Insert struct as a class with kind='struct'
            self.cursor.execute(
                """
                INSERT INTO classes
                (module_id, name, kind, line_start, line_end)
                VALUES (?, ?, 'struct', ?, ?)
                """,
                (module_id, full_name, line_number, end_line)
            )
            class_id = self.cursor.lastrowid
            stats["structs_found"] += 1

            # Insert inheritance relationships (interfaces for structs)
            if inheritance:
                self._insert_inheritance(class_id, inheritance)

    def _extract_enums(self, content: str, module_id: int, namespace: Optional[str],
                      stats: dict) -> None:
        """Extract enum definitions using regex."""
        enum_pattern = r'''
            (?:\[[\s\S]*?\]\s*)?                    # Optional attributes
            (?:public|internal|private|protected)?\s*
            enum\s+
            (\w+)                                   # Enum name
            (?:\s*:\s*(\w+))?                       # Optional underlying type
            \s*\{
        '''

        for match in re.finditer(enum_pattern, content, re.VERBOSE):
            enum_name = match.group(1)

            line_number = content[:match.start()].count('\n') + 1

            # Find closing brace
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

            # Build fully qualified name
            full_name = f"{namespace}.{enum_name}" if namespace else enum_name

            # Insert enum as a class with kind='enum'
            self.cursor.execute(
                """
                INSERT INTO classes
                (module_id, name, kind, line_start, line_end)
                VALUES (?, ?, 'enum', ?, ?)
                """,
                (module_id, full_name, line_number, end_line)
            )
            stats["enums_found"] += 1

    def _extract_methods(self, class_body: str, module_id: int, class_id: int,
                        class_start_line: int, stats: dict) -> None:
        """Extract method definitions from a class body."""
        # C# keywords that should not be treated as method names
        csharp_keywords = {
            'if', 'else', 'while', 'for', 'foreach', 'do', 'switch', 'case',
            'try', 'catch', 'finally', 'throw', 'return', 'break', 'continue',
            'goto', 'using', 'namespace', 'class', 'struct', 'interface', 'enum',
            'new', 'this', 'base', 'typeof', 'sizeof', 'default', 'delegate',
            'event', 'lock', 'checked', 'unchecked', 'fixed', 'unsafe'
        }

        # Simplified pattern for better matching
        simple_method_pattern = r'''
            (?:public|private|protected|internal)\s+
            (?:static\s+|virtual\s+|override\s+|abstract\s+|async\s+|sealed\s+)*
            ([\w<>[\],\s]+)\s+                      # Return type
            (\w+)                                   # Method name
            \s*\(                                   # Opening parenthesis
            ([^)]*)                                 # Parameters
            \)
        '''

        for match in re.finditer(simple_method_pattern, class_body, re.VERBOSE):
            return_type = match.group(1).strip()
            method_name = match.group(2)
            parameters = match.group(3)

            # Skip C# keywords
            if method_name.lower() in csharp_keywords:
                continue

            # Skip common type names that are not methods
            if method_name in ['Task', 'List', 'Dictionary', 'String', 'Int32',
                              'Boolean', 'DateTime', 'TimeSpan', 'Guid']:
                continue

            # Skip if it looks like a constructor call or type instantiation
            # (these typically appear in method bodies, not as declarations)
            if return_type.lower() in ['new', 'var', 'const']:
                continue

            line_number = class_start_line + class_body[:match.start()].count('\n')

            # Determine kind
            match_text = match.group(0)
            is_async = 'async' in match_text
            is_static = 'static' in match_text
            is_abstract = 'abstract' in match_text
            is_virtual = 'virtual' in match_text
            is_override = 'override' in match_text

            kind = 'method'
            if is_async:
                kind = 'async_method'
            elif is_abstract:
                kind = 'abstract_method'
            elif is_static:
                kind = 'static_method'

            # Insert method
            self.cursor.execute(
                """
                INSERT INTO functions
                (module_id, class_id, name, kind, line_start, is_async)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (module_id, class_id, method_name, kind, line_number, is_async)
            )
            stats["methods_found"] += 1

    def _extract_properties(self, class_body: str, module_id: int, class_id: int,
                           class_start_line: int, stats: dict) -> None:
        """Extract property definitions from a class body."""
        # Property pattern: public string Name { get; set; }
        property_pattern = r'''
            (?:public|private|protected|internal)?\s*
            (?:static\s+|virtual\s+|override\s+|abstract\s+)*
            ([\w<>[\]]+)\s+                         # Property type
            (\w+)                                   # Property name
            \s*\{\s*
            (?:get|set|init)                        # Accessor
        '''

        for match in re.finditer(property_pattern, class_body, re.VERBOSE):
            prop_type = match.group(1)
            prop_name = match.group(2)

            line_number = class_start_line + class_body[:match.start()].count('\n')

            # Insert property as a variable with kind='property'
            self.cursor.execute(
                """
                INSERT INTO variables
                (module_id, class_id, name, kind, line_number)
                VALUES (?, ?, ?, 'property', ?)
                """,
                (module_id, class_id, prop_name, line_number)
            )
            stats["properties_found"] += 1

    def _extract_fields(self, class_body: str, module_id: int, class_id: int,
                       class_start_line: int, stats: dict) -> None:
        """Extract field definitions from a class body."""
        # Field pattern: private readonly string _name;
        field_pattern = r'''
            (?:public|private|protected|internal)?\s*
            (?:static\s+|readonly\s+|const\s+)*
            ([\w<>[\]]+)\s+                         # Field type
            (\w+)                                   # Field name
            \s*(?:=\s*[^;]+)?\s*;                   # Optional initializer and semicolon
        '''

        for match in re.finditer(field_pattern, class_body, re.VERBOSE):
            field_type = match.group(1)
            field_name = match.group(2)

            # Skip common false positives
            if field_name in ['get', 'set', 'value', 'return', 'if', 'for', 'while']:
                continue

            line_number = class_start_line + class_body[:match.start()].count('\n')

            match_text = match.group(0)
            kind = 'field'
            if 'const' in match_text:
                kind = 'constant'
            elif 'readonly' in match_text:
                kind = 'readonly_field'

            # Insert field as a variable
            self.cursor.execute(
                """
                INSERT INTO variables
                (module_id, class_id, name, kind, line_number)
                VALUES (?, ?, ?, ?, ?)
                """,
                (module_id, class_id, field_name, kind, line_number)
            )
            stats["fields_found"] += 1

    def _insert_inheritance(self, class_id: int, inheritance_list: str) -> None:
        """Parse and insert inheritance relationships."""
        # Split by comma and clean up
        items = [item.strip() for item in inheritance_list.split(',')]

        for idx, item in enumerate(items):
            # Remove generic parameters for now (simplified)
            item = re.sub(r'<.*?>', '', item).strip()

            # First item is typically base class, rest are interfaces
            # In C#, if it starts with I and is capitalized, it's likely an interface
            if idx == 0 and not item.startswith('I'):
                relationship_kind = 'inherits'
            else:
                relationship_kind = 'implements'

            self.cursor.execute(
                """
                INSERT INTO inheritance
                (class_id, base_class_name, relationship_kind, position)
                VALUES (?, ?, ?, ?)
                """,
                (class_id, item, relationship_kind, idx)
            )

    def _insert_import(self, module_id: int, to_module: str, import_name: str,
                      kind: str, lineno: int, alias: Optional[str] = None) -> None:
        """Insert import record."""
        # C# using statements are always absolute (not relative)
        is_relative = False

        self.cursor.execute(
            """
            INSERT INTO imports
            (from_module_id, to_module, import_name, alias, import_kind,
             is_relative, is_dynamic, is_wildcard, line_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (module_id, to_module, import_name, alias, kind,
             is_relative, False, False, lineno)
        )
