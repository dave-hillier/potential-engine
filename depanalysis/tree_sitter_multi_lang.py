"""
Tree-sitter parsers for additional languages: Java, Rust, C++, Go.

These are basic implementations that capture core structural elements.
They can be expanded as needed for more detailed analysis.
"""
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

from tree_sitter import Language, Node, Tree
import tree_sitter_java
import tree_sitter_rust
import tree_sitter_cpp
import tree_sitter_go

from .tree_sitter_base import TreeSitterParser


class TreeSitterJavaParser(TreeSitterParser):
    """Analyzes Java code structure using tree-sitter."""

    def __init__(self, repo_path: Path, db_connection: sqlite3.Connection):
        """Initialize Java parser."""
        super().__init__(repo_path, db_connection, "java")

    def _load_language(self) -> Language:
        """Load tree-sitter Java language."""
        return Language(tree_sitter_java.language())

    def _get_file_extensions(self) -> List[str]:
        """Get Java file extensions."""
        return [".java"]

    def _should_skip_directory(self, dir_name: str) -> bool:
        """Check if directory should be skipped."""
        skip_dirs = {".git", "target", "build", ".gradle", ".mvn", "bin",
                    "node_modules", "__pycache__"}
        return dir_name in skip_dirs

    def _analyze_tree(self, tree: Tree, module_id: int, content: str, stats: dict) -> None:
        """Analyze Java parse tree."""
        root_node = tree.root_node
        context = {"class_id": None, "function_id": None, "package": None}

        # Extract package
        for child in root_node.children:
            if child.type == "package_declaration":
                package_node = self.find_child_by_field(child, "name")
                if package_node:
                    context["package"] = self.get_node_text(package_node, content)
                break

        self._analyze_node(root_node, module_id, content, stats, context)

    def _analyze_node(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Recursively analyze tree-sitter nodes."""

        # Handle imports
        if node.type == "import_declaration":
            import_node = self.find_child_by_type(node, "scoped_identifier") or \
                         self.find_child_by_type(node, "identifier")
            if import_node:
                import_name = self.get_node_text(import_node, content)
                self._insert_import(
                    module_id, import_name, import_name.split('.')[-1],
                    "import", self.get_line_number(node)
                )
                stats["imports_found"] += 1

        # Handle class declarations
        elif node.type == "class_declaration":
            name_node = self.find_child_by_field(node, "name")
            if name_node:
                class_name = self.get_node_text(name_node, content)
                full_name = f"{context['package']}.{class_name}" if context["package"] else class_name

                class_id = self._insert_class(
                    module_id, full_name, "class",
                    self.get_line_number(node), self.get_end_line_number(node)
                )
                stats["classes_found"] += 1

                # Extract superclass and interfaces
                superclass = self.find_child_by_field(node, "superclass")
                if superclass:
                    type_node = self.find_child_by_type(superclass, "type_identifier")
                    if type_node:
                        base_name = self.get_node_text(type_node, content)
                        self._insert_inheritance(class_id, base_name, "extends", 0)
                        stats["inheritance_found"] += 1

                interfaces = self.find_child_by_field(node, "interfaces")
                if interfaces:
                    position = 0
                    for child in interfaces.children:
                        if child.type == "type_identifier":
                            interface_name = self.get_node_text(child, content)
                            self._insert_inheritance(class_id, interface_name, "implements", position)
                            stats["inheritance_found"] += 1
                            position += 1

                # Analyze class body
                body_node = self.find_child_by_field(node, "body")
                if body_node:
                    old_class_id = context["class_id"]
                    context["class_id"] = class_id
                    self._analyze_node(body_node, module_id, content, stats, context)
                    context["class_id"] = old_class_id
                return

        # Handle interface declarations
        elif node.type == "interface_declaration":
            name_node = self.find_child_by_field(node, "name")
            if name_node:
                interface_name = self.get_node_text(name_node, content)
                full_name = f"{context['package']}.{interface_name}" if context["package"] else interface_name

                self._insert_class(
                    module_id, full_name, "interface",
                    self.get_line_number(node), self.get_end_line_number(node)
                )
                stats["classes_found"] += 1
                return

        # Handle method declarations
        elif node.type == "method_declaration" and context["class_id"] is not None:
            name_node = self.find_child_by_field(node, "name")
            if name_node:
                method_name = self.get_node_text(name_node, content)
                kind = "method"

                function_id = self._insert_function(
                    module_id, method_name, kind,
                    self.get_line_number(node), self.get_end_line_number(node),
                    class_id=context["class_id"]
                )
                stats["functions_found"] += 1

                # Analyze method body
                body_node = self.find_child_by_field(node, "body")
                if body_node:
                    old_function_id = context["function_id"]
                    context["function_id"] = function_id
                    self._analyze_node(body_node, module_id, content, stats, context)
                    context["function_id"] = old_function_id
                return

        # Recursively analyze children
        for child in node.children:
            self._analyze_node(child, module_id, content, stats, context)


class TreeSitterRustParser(TreeSitterParser):
    """Analyzes Rust code structure using tree-sitter."""

    def __init__(self, repo_path: Path, db_connection: sqlite3.Connection):
        """Initialize Rust parser."""
        super().__init__(repo_path, db_connection, "rust")

    def _load_language(self) -> Language:
        """Load tree-sitter Rust language."""
        return Language(tree_sitter_rust.language())

    def _get_file_extensions(self) -> List[str]:
        """Get Rust file extensions."""
        return [".rs"]

    def _should_skip_directory(self, dir_name: str) -> bool:
        """Check if directory should be skipped."""
        skip_dirs = {".git", "target", "node_modules", "__pycache__"}
        return dir_name in skip_dirs

    def _analyze_tree(self, tree: Tree, module_id: int, content: str, stats: dict) -> None:
        """Analyze Rust parse tree."""
        root_node = tree.root_node
        context = {"class_id": None, "function_id": None}
        self._analyze_node(root_node, module_id, content, stats, context)

    def _analyze_node(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Recursively analyze tree-sitter nodes."""

        # Handle use declarations (imports)
        if node.type == "use_declaration":
            use_tree = self.find_child_by_type(node, "use_tree") or \
                      self.find_child_by_type(node, "scoped_identifier") or \
                      self.find_child_by_type(node, "identifier")
            if use_tree:
                import_name = self.get_node_text(use_tree, content)
                self._insert_import(
                    module_id, import_name, import_name.split('::')[-1],
                    "use", self.get_line_number(node)
                )
                stats["imports_found"] += 1

        # Handle struct declarations
        elif node.type == "struct_item":
            name_node = self.find_child_by_field(node, "name")
            if name_node:
                struct_name = self.get_node_text(name_node, content)
                self._insert_class(
                    module_id, struct_name, "struct",
                    self.get_line_number(node), self.get_end_line_number(node)
                )
                stats["classes_found"] += 1
                return

        # Handle trait declarations
        elif node.type == "trait_item":
            name_node = self.find_child_by_field(node, "name")
            if name_node:
                trait_name = self.get_node_text(name_node, content)
                self._insert_class(
                    module_id, trait_name, "trait",
                    self.get_line_number(node), self.get_end_line_number(node)
                )
                stats["classes_found"] += 1
                return

        # Handle impl blocks
        elif node.type == "impl_item":
            # Skip for now - Rust impl blocks are complex
            pass

        # Handle function declarations
        elif node.type == "function_item":
            name_node = self.find_child_by_field(node, "name")
            if name_node:
                func_name = self.get_node_text(name_node, content)
                kind = "function"

                function_id = self._insert_function(
                    module_id, func_name, kind,
                    self.get_line_number(node), self.get_end_line_number(node),
                    class_id=context["class_id"]
                )
                stats["functions_found"] += 1

                # Analyze function body
                body_node = self.find_child_by_field(node, "body")
                if body_node:
                    old_function_id = context["function_id"]
                    context["function_id"] = function_id
                    self._analyze_node(body_node, module_id, content, stats, context)
                    context["function_id"] = old_function_id
                return

        # Recursively analyze children
        for child in node.children:
            self._analyze_node(child, module_id, content, stats, context)


class TreeSitterCppParser(TreeSitterParser):
    """Analyzes C++ code structure using tree-sitter."""

    def __init__(self, repo_path: Path, db_connection: sqlite3.Connection):
        """Initialize C++ parser."""
        super().__init__(repo_path, db_connection, "cpp")

    def _load_language(self) -> Language:
        """Load tree-sitter C++ language."""
        return Language(tree_sitter_cpp.language())

    def _get_file_extensions(self) -> List[str]:
        """Get C++ file extensions."""
        return [".cpp", ".cc", ".cxx", ".hpp", ".h", ".hxx"]

    def _should_skip_directory(self, dir_name: str) -> bool:
        """Check if directory should be skipped."""
        skip_dirs = {".git", "build", "cmake-build-debug", "cmake-build-release",
                    "node_modules", "__pycache__"}
        return dir_name in skip_dirs

    def _analyze_tree(self, tree: Tree, module_id: int, content: str, stats: dict) -> None:
        """Analyze C++ parse tree."""
        root_node = tree.root_node
        context = {"class_id": None, "function_id": None, "namespace": None}
        self._analyze_node(root_node, module_id, content, stats, context)

    def _analyze_node(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Recursively analyze tree-sitter nodes."""

        # Handle using declarations and includes
        if node.type == "using_declaration":
            # Extract what's being imported
            pass  # Simplified for now

        elif node.type == "preproc_include":
            # #include directives
            path_node = self.find_child_by_type(node, "string_literal") or \
                       self.find_child_by_type(node, "system_lib_string")
            if path_node:
                import_name = self.get_node_text(path_node, content).strip('"<>')
                self._insert_import(
                    module_id, import_name, import_name.split('/')[-1],
                    "include", self.get_line_number(node)
                )
                stats["imports_found"] += 1

        # Handle class declarations
        elif node.type in ("class_specifier", "struct_specifier"):
            name_node = self.find_child_by_field(node, "name")
            if name_node:
                class_name = self.get_node_text(name_node, content)
                kind = "class" if node.type == "class_specifier" else "struct"

                class_id = self._insert_class(
                    module_id, class_name, kind,
                    self.get_line_number(node), self.get_end_line_number(node)
                )
                stats["classes_found"] += 1

                # Analyze class body
                body_node = self.find_child_by_field(node, "body")
                if body_node:
                    old_class_id = context["class_id"]
                    context["class_id"] = class_id
                    self._analyze_node(body_node, module_id, content, stats, context)
                    context["class_id"] = old_class_id
                return

        # Handle function definitions
        elif node.type == "function_definition":
            declarator = self.find_child_by_field(node, "declarator")
            if declarator:
                name_node = self.find_child_by_field(declarator, "declarator")
                if not name_node:
                    name_node = declarator

                # Extract function name (simplified)
                func_name = self.get_node_text(name_node, content).split('(')[0].strip()
                if func_name:
                    function_id = self._insert_function(
                        module_id, func_name, "function",
                        self.get_line_number(node), self.get_end_line_number(node),
                        class_id=context["class_id"]
                    )
                    stats["functions_found"] += 1

                    # Analyze function body
                    body_node = self.find_child_by_field(node, "body")
                    if body_node:
                        old_function_id = context["function_id"]
                        context["function_id"] = function_id
                        self._analyze_node(body_node, module_id, content, stats, context)
                        context["function_id"] = old_function_id
                    return

        # Recursively analyze children
        for child in node.children:
            self._analyze_node(child, module_id, content, stats, context)


class TreeSitterGoParser(TreeSitterParser):
    """Analyzes Go code structure using tree-sitter."""

    def __init__(self, repo_path: Path, db_connection: sqlite3.Connection):
        """Initialize Go parser."""
        super().__init__(repo_path, db_connection, "go")

    def _load_language(self) -> Language:
        """Load tree-sitter Go language."""
        return Language(tree_sitter_go.language())

    def _get_file_extensions(self) -> List[str]:
        """Get Go file extensions."""
        return [".go"]

    def _should_skip_directory(self, dir_name: str) -> bool:
        """Check if directory should be skipped."""
        skip_dirs = {".git", "vendor", "node_modules", "__pycache__"}
        return dir_name in skip_dirs

    def _analyze_tree(self, tree: Tree, module_id: int, content: str, stats: dict) -> None:
        """Analyze Go parse tree."""
        root_node = tree.root_node
        context = {"class_id": None, "function_id": None, "package": None}

        # Extract package name
        for child in root_node.children:
            if child.type == "package_clause":
                package_node = self.find_child_by_type(child, "package_identifier")
                if package_node:
                    context["package"] = self.get_node_text(package_node, content)
                break

        self._analyze_node(root_node, module_id, content, stats, context)

    def _analyze_node(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Recursively analyze tree-sitter nodes."""

        # Handle import declarations
        if node.type == "import_declaration":
            for child in node.children:
                if child.type == "import_spec":
                    path_node = self.find_child_by_field(child, "path")
                    if path_node:
                        import_path = self.get_node_text(path_node, content).strip('"')
                        self._insert_import(
                            module_id, import_path, import_path.split('/')[-1],
                            "import", self.get_line_number(node)
                        )
                        stats["imports_found"] += 1

        # Handle type declarations (struct, interface)
        elif node.type == "type_declaration":
            for child in node.children:
                if child.type == "type_spec":
                    name_node = self.find_child_by_field(child, "name")
                    type_node = self.find_child_by_field(child, "type")
                    if name_node and type_node:
                        type_name = self.get_node_text(name_node, content)

                        if type_node.type == "struct_type":
                            kind = "struct"
                        elif type_node.type == "interface_type":
                            kind = "interface"
                        else:
                            kind = "type"

                        self._insert_class(
                            module_id, type_name, kind,
                            self.get_line_number(child), self.get_end_line_number(child)
                        )
                        stats["classes_found"] += 1

        # Handle function declarations
        elif node.type == "function_declaration":
            name_node = self.find_child_by_field(node, "name")
            if name_node:
                func_name = self.get_node_text(name_node, content)

                function_id = self._insert_function(
                    module_id, func_name, "function",
                    self.get_line_number(node), self.get_end_line_number(node)
                )
                stats["functions_found"] += 1

                # Analyze function body
                body_node = self.find_child_by_field(node, "body")
                if body_node:
                    old_function_id = context["function_id"]
                    context["function_id"] = function_id
                    self._analyze_node(body_node, module_id, content, stats, context)
                    context["function_id"] = old_function_id
                return

        # Handle method declarations
        elif node.type == "method_declaration":
            name_node = self.find_child_by_field(node, "name")
            if name_node:
                method_name = self.get_node_text(name_node, content)

                function_id = self._insert_function(
                    module_id, method_name, "method",
                    self.get_line_number(node), self.get_end_line_number(node),
                    class_id=context["class_id"]
                )
                stats["functions_found"] += 1

                # Analyze method body
                body_node = self.find_child_by_field(node, "body")
                if body_node:
                    old_function_id = context["function_id"]
                    context["function_id"] = function_id
                    self._analyze_node(body_node, module_id, content, stats, context)
                    context["function_id"] = old_function_id
                return

        # Recursively analyze children
        for child in node.children:
            self._analyze_node(child, module_id, content, stats, context)
