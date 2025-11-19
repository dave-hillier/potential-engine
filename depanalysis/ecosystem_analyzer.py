"""
Manifest Parser - Language ecosystem package dependency parser.

PARSE PHASE component that extracts dependencies from package manifest files:
- Python (requirements.txt, pyproject.toml, setup.py, Pipfile)
- TypeScript/JavaScript (package.json, yarn.lock, package-lock.json)
- Rust (Cargo.toml, Cargo.lock)
- Java (pom.xml, build.gradle)
- C# (.csproj, packages.config)
- Go (go.mod, go.sum)
- C++ (conanfile.txt, CMakeLists.txt)

This is a PARSER, not an analyzer - it writes to structure.db during parse phase.
For analysis/queries, use MetricsAnalyzer.
"""
import json
import re
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class ManifestParser:
    """
    Parses package manager manifest files and extracts external dependencies.

    PARSE PHASE: Extracts and writes to structure.db:
    - External package dependencies → external_dependencies table
    - Version conflicts → dependency_conflicts table
    - Package manager metadata → package_managers table

    For ANALYSIS/QUERIES: Use MetricsAnalyzer methods
    """

    def __init__(self, repo_path: Path, structure_db: sqlite3.Connection):
        """
        Initialize ecosystem analyzer.

        Args:
            repo_path: Path to the repository root
            structure_db: SQLite connection to structure.db
        """
        self.repo_path = Path(repo_path)
        self.structure_db = structure_db
        self.cursor = structure_db.cursor()

        # Initialize ecosystem tables
        self._initialize_tables()

    def _initialize_tables(self) -> None:
        """Create tables for external dependencies."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS package_managers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                ecosystem TEXT NOT NULL,
                CONSTRAINT valid_manager CHECK (name IN (
                    'pip', 'poetry', 'pipenv', 'npm', 'yarn', 'pnpm',
                    'cargo', 'maven', 'gradle', 'nuget', 'go_modules',
                    'conan', 'vcpkg'
                ))
            )
        """)

        # Pre-populate package managers
        managers = [
            ('pip', 'python'),
            ('poetry', 'python'),
            ('pipenv', 'python'),
            ('npm', 'javascript'),
            ('yarn', 'javascript'),
            ('pnpm', 'javascript'),
            ('cargo', 'rust'),
            ('maven', 'java'),
            ('gradle', 'java'),
            ('nuget', 'csharp'),
            ('go_modules', 'go'),
            ('conan', 'cpp'),
            ('vcpkg', 'cpp')
        ]

        for name, ecosystem in managers:
            self.cursor.execute("""
                INSERT OR IGNORE INTO package_managers (name, ecosystem)
                VALUES (?, ?)
            """, (name, ecosystem))

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS external_dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_manager_id INTEGER NOT NULL,
                manifest_file TEXT NOT NULL,
                package_name TEXT NOT NULL,
                version_spec TEXT,
                is_dev_dependency BOOLEAN DEFAULT 0,
                is_transitive BOOLEAN DEFAULT 0,
                FOREIGN KEY (package_manager_id) REFERENCES package_managers(id) ON DELETE CASCADE
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS dependency_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_name TEXT NOT NULL,
                version1 TEXT NOT NULL,
                version2 TEXT NOT NULL,
                manifest1 TEXT NOT NULL,
                manifest2 TEXT NOT NULL,
                conflict_type TEXT CHECK (conflict_type IN ('version_mismatch', 'major_version_diff', 'incompatible'))
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS module_package_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id INTEGER NOT NULL,
                external_dependency_id INTEGER NOT NULL,
                import_name TEXT NOT NULL,
                FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE,
                FOREIGN KEY (external_dependency_id) REFERENCES external_dependencies(id) ON DELETE CASCADE
            )
        """)

        # Create indexes
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_external_deps_package ON external_dependencies(package_name)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_external_deps_manager ON external_dependencies(package_manager_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_external_deps_manifest ON external_dependencies(manifest_file)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_conflicts_package ON dependency_conflicts(package_name)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_module_pkg_usage_module ON module_package_usage(module_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_module_pkg_usage_dep ON module_package_usage(external_dependency_id)")

        self.structure_db.commit()

    def parse(self) -> Dict[str, int]:
        """
        Parse package manifest files and write to structure.db.

        PARSE PHASE method - extracts dependency data and persists to database.

        Returns:
            Dictionary with parsing statistics
        """
        stats = {
            "manifest_files": 0,
            "dependencies_found": 0,
            "conflicts_found": 0,
            "python_deps": 0,
            "javascript_deps": 0,
            "rust_deps": 0,
            "java_deps": 0,
            "csharp_deps": 0,
            "go_deps": 0,
            "cpp_deps": 0
        }

        # Analyze Python dependencies
        stats["python_deps"] += self._analyze_python_dependencies(stats)

        # Analyze JavaScript/TypeScript dependencies
        stats["javascript_deps"] += self._analyze_javascript_dependencies(stats)

        # Analyze Rust dependencies
        stats["rust_deps"] += self._analyze_rust_dependencies(stats)

        # Analyze Java dependencies
        stats["java_deps"] += self._analyze_java_dependencies(stats)

        # Analyze Go dependencies
        stats["go_deps"] += self._analyze_go_dependencies(stats)

        # Detect version conflicts
        stats["conflicts_found"] = self._detect_version_conflicts()

        self.structure_db.commit()
        return stats

    def analyze(self) -> Dict[str, int]:
        """
        DEPRECATED: Use parse() instead.

        This method is kept for backward compatibility but will be removed.
        analyze() implies querying/analysis, but this class does parsing.
        """
        return self.parse()

    def _get_package_manager_id(self, name: str) -> Optional[int]:
        """Get package manager ID by name."""
        result = self.cursor.execute(
            "SELECT id FROM package_managers WHERE name = ?",
            (name,)
        ).fetchone()
        return result[0] if result else None

    def _analyze_python_dependencies(self, stats: Dict) -> int:
        """Analyze Python package dependencies."""
        count = 0

        # requirements.txt
        for req_file in self.repo_path.rglob("requirements*.txt"):
            if any(skip in req_file.parts for skip in ['.git', 'venv', '__pycache__']):
                continue

            stats["manifest_files"] += 1
            count += self._parse_requirements_txt(req_file)

        # pyproject.toml
        for toml_file in self.repo_path.rglob("pyproject.toml"):
            if '.git' in toml_file.parts:
                continue

            stats["manifest_files"] += 1
            count += self._parse_pyproject_toml(toml_file)

        # Pipfile
        for pipfile in self.repo_path.rglob("Pipfile"):
            if '.git' in pipfile.parts:
                continue

            stats["manifest_files"] += 1
            count += self._parse_pipfile(pipfile)

        stats["dependencies_found"] += count
        return count

    def _parse_requirements_txt(self, file_path: Path) -> int:
        """Parse requirements.txt file."""
        count = 0
        pm_id = self._get_package_manager_id('pip')
        rel_path = str(file_path.relative_to(self.repo_path))

        try:
            content = file_path.read_text(encoding='utf-8')
        except:
            return 0

        # Parse lines like: package==1.2.3 or package>=1.0.0
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Extract package name and version spec
            match = re.match(r'([a-zA-Z0-9_-]+)([><=!]+.*)?', line)
            if match:
                package_name = match.group(1)
                version_spec = match.group(2) or ''

                self.cursor.execute("""
                    INSERT INTO external_dependencies
                    (package_manager_id, manifest_file, package_name, version_spec)
                    VALUES (?, ?, ?, ?)
                """, (pm_id, rel_path, package_name, version_spec))
                count += 1

        return count

    def _parse_pyproject_toml(self, file_path: Path) -> int:
        """Parse pyproject.toml file (simple regex-based parsing)."""
        count = 0
        pm_id = self._get_package_manager_id('poetry')
        rel_path = str(file_path.relative_to(self.repo_path))

        try:
            content = file_path.read_text(encoding='utf-8')
        except:
            return 0

        # Look for dependencies section
        in_dependencies = False
        in_dev_dependencies = False

        for line in content.splitlines():
            line = line.strip()

            if line == '[project.dependencies]' or line == '[tool.poetry.dependencies]':
                in_dependencies = True
                in_dev_dependencies = False
                continue
            elif line == '[tool.poetry.dev-dependencies]' or line == '[project.optional-dependencies]':
                in_dependencies = False
                in_dev_dependencies = True
                continue
            elif line.startswith('['):
                in_dependencies = False
                in_dev_dependencies = False
                continue

            if in_dependencies or in_dev_dependencies:
                # Parse lines like: package = "^1.2.3"
                match = re.match(r'(["\']?)([a-zA-Z0-9_-]+)\1\s*=\s*["\']([^"\']+)["\']', line)
                if match:
                    package_name = match.group(2)
                    version_spec = match.group(3)

                    self.cursor.execute("""
                        INSERT INTO external_dependencies
                        (package_manager_id, manifest_file, package_name, version_spec, is_dev_dependency)
                        VALUES (?, ?, ?, ?, ?)
                    """, (pm_id, rel_path, package_name, version_spec, in_dev_dependencies))
                    count += 1

        return count

    def _parse_pipfile(self, file_path: Path) -> int:
        """Parse Pipfile."""
        count = 0
        pm_id = self._get_package_manager_id('pipenv')
        rel_path = str(file_path.relative_to(self.repo_path))

        try:
            content = file_path.read_text(encoding='utf-8')
        except:
            return 0

        in_packages = False
        in_dev_packages = False

        for line in content.splitlines():
            line = line.strip()

            if line == '[packages]':
                in_packages = True
                in_dev_packages = False
                continue
            elif line == '[dev-packages]':
                in_packages = False
                in_dev_packages = True
                continue
            elif line.startswith('['):
                in_packages = False
                in_dev_packages = False
                continue

            if in_packages or in_dev_packages:
                match = re.match(r'([a-zA-Z0-9_-]+)\s*=\s*["\']([^"\']+)["\']', line)
                if match:
                    package_name = match.group(1)
                    version_spec = match.group(2)

                    self.cursor.execute("""
                        INSERT INTO external_dependencies
                        (package_manager_id, manifest_file, package_name, version_spec, is_dev_dependency)
                        VALUES (?, ?, ?, ?, ?)
                    """, (pm_id, rel_path, package_name, version_spec, in_dev_packages))
                    count += 1

        return count

    def _analyze_javascript_dependencies(self, stats: Dict) -> int:
        """Analyze JavaScript/TypeScript package dependencies."""
        count = 0

        for pkg_file in self.repo_path.rglob("package.json"):
            if any(skip in pkg_file.parts for skip in ['.git', 'node_modules']):
                continue

            stats["manifest_files"] += 1
            count += self._parse_package_json(pkg_file)

        stats["dependencies_found"] += count
        return count

    def _parse_package_json(self, file_path: Path) -> int:
        """Parse package.json file."""
        count = 0
        pm_id = self._get_package_manager_id('npm')
        rel_path = str(file_path.relative_to(self.repo_path))

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            return 0

        # Parse dependencies
        for dep_type, is_dev in [('dependencies', False), ('devDependencies', True)]:
            if dep_type in data and isinstance(data[dep_type], dict):
                for package_name, version_spec in data[dep_type].items():
                    self.cursor.execute("""
                        INSERT INTO external_dependencies
                        (package_manager_id, manifest_file, package_name, version_spec, is_dev_dependency)
                        VALUES (?, ?, ?, ?, ?)
                    """, (pm_id, rel_path, package_name, version_spec, is_dev))
                    count += 1

        return count

    def _analyze_rust_dependencies(self, stats: Dict) -> int:
        """Analyze Rust Cargo dependencies."""
        count = 0

        for cargo_file in self.repo_path.rglob("Cargo.toml"):
            if '.git' in cargo_file.parts:
                continue

            stats["manifest_files"] += 1
            count += self._parse_cargo_toml(cargo_file)

        stats["dependencies_found"] += count
        return count

    def _parse_cargo_toml(self, file_path: Path) -> int:
        """Parse Cargo.toml file."""
        count = 0
        pm_id = self._get_package_manager_id('cargo')
        rel_path = str(file_path.relative_to(self.repo_path))

        try:
            content = file_path.read_text(encoding='utf-8')
        except:
            return 0

        in_dependencies = False
        in_dev_dependencies = False

        for line in content.splitlines():
            line = line.strip()

            if line == '[dependencies]':
                in_dependencies = True
                in_dev_dependencies = False
                continue
            elif line == '[dev-dependencies]':
                in_dependencies = False
                in_dev_dependencies = True
                continue
            elif line.startswith('['):
                in_dependencies = False
                in_dev_dependencies = False
                continue

            if in_dependencies or in_dev_dependencies:
                match = re.match(r'([a-zA-Z0-9_-]+)\s*=\s*["\']([^"\']+)["\']', line)
                if match:
                    package_name = match.group(1)
                    version_spec = match.group(2)

                    self.cursor.execute("""
                        INSERT INTO external_dependencies
                        (package_manager_id, manifest_file, package_name, version_spec, is_dev_dependency)
                        VALUES (?, ?, ?, ?, ?)
                    """, (pm_id, rel_path, package_name, version_spec, in_dev_dependencies))
                    count += 1

        return count

    def _analyze_java_dependencies(self, stats: Dict) -> int:
        """Analyze Java Maven/Gradle dependencies."""
        count = 0

        # Maven pom.xml
        for pom_file in self.repo_path.rglob("pom.xml"):
            if '.git' in pom_file.parts:
                continue

            stats["manifest_files"] += 1
            count += self._parse_pom_xml(pom_file)

        # TODO: Gradle build.gradle parsing (requires more complex parsing)

        stats["dependencies_found"] += count
        return count

    def _parse_pom_xml(self, file_path: Path) -> int:
        """Parse Maven pom.xml file."""
        count = 0
        pm_id = self._get_package_manager_id('maven')
        rel_path = str(file_path.relative_to(self.repo_path))

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except:
            return 0

        # Maven uses XML namespaces
        ns = {'maven': 'http://maven.apache.org/POM/4.0.0'}

        # Find all dependencies
        for dep in root.findall('.//maven:dependency', ns) or root.findall('.//dependency'):
            group_id = dep.find('maven:groupId', ns) or dep.find('groupId')
            artifact_id = dep.find('maven:artifactId', ns) or dep.find('artifactId')
            version = dep.find('maven:version', ns) or dep.find('version')
            scope = dep.find('maven:scope', ns) or dep.find('scope')

            if group_id is not None and artifact_id is not None:
                package_name = f"{group_id.text}:{artifact_id.text}"
                version_spec = version.text if version is not None else ''
                is_dev = scope is not None and scope.text in ['test', 'provided']

                self.cursor.execute("""
                    INSERT INTO external_dependencies
                    (package_manager_id, manifest_file, package_name, version_spec, is_dev_dependency)
                    VALUES (?, ?, ?, ?, ?)
                """, (pm_id, rel_path, package_name, version_spec, is_dev))
                count += 1

        return count

    def _analyze_go_dependencies(self, stats: Dict) -> int:
        """Analyze Go module dependencies."""
        count = 0

        for go_mod in self.repo_path.rglob("go.mod"):
            if '.git' in go_mod.parts:
                continue

            stats["manifest_files"] += 1
            count += self._parse_go_mod(go_mod)

        stats["dependencies_found"] += count
        return count

    def _parse_go_mod(self, file_path: Path) -> int:
        """Parse go.mod file."""
        count = 0
        pm_id = self._get_package_manager_id('go_modules')
        rel_path = str(file_path.relative_to(self.repo_path))

        try:
            content = file_path.read_text(encoding='utf-8')
        except:
            return 0

        in_require = False

        for line in content.splitlines():
            line = line.strip()

            if line.startswith('require'):
                in_require = True
                # Single line require
                if not line.endswith('('):
                    match = re.match(r'require\s+([^\s]+)\s+([^\s]+)', line)
                    if match:
                        package_name = match.group(1)
                        version_spec = match.group(2)

                        self.cursor.execute("""
                            INSERT INTO external_dependencies
                            (package_manager_id, manifest_file, package_name, version_spec)
                            VALUES (?, ?, ?, ?)
                        """, (pm_id, rel_path, package_name, version_spec))
                        count += 1
                continue

            if in_require:
                if line == ')':
                    in_require = False
                    continue

                match = re.match(r'([^\s]+)\s+([^\s]+)', line)
                if match:
                    package_name = match.group(1)
                    version_spec = match.group(2)

                    self.cursor.execute("""
                        INSERT INTO external_dependencies
                        (package_manager_id, manifest_file, package_name, version_spec)
                        VALUES (?, ?, ?, ?)
                    """, (pm_id, rel_path, package_name, version_spec))
                    count += 1

        return count

    def _detect_version_conflicts(self) -> int:
        """Detect version conflicts across different manifest files."""
        count = 0

        # Find packages with multiple version specifications
        conflicts = self.cursor.execute("""
            SELECT
                d1.package_name,
                d1.version_spec as version1,
                d2.version_spec as version2,
                d1.manifest_file as manifest1,
                d2.manifest_file as manifest2
            FROM external_dependencies d1
            JOIN external_dependencies d2 ON d1.package_name = d2.package_name
            WHERE d1.id < d2.id
              AND d1.version_spec != d2.version_spec
              AND d1.version_spec != ''
              AND d2.version_spec != ''
        """).fetchall()

        for package_name, version1, version2, manifest1, manifest2 in conflicts:
            # Determine conflict type
            conflict_type = 'version_mismatch'
            if self._is_major_version_diff(version1, version2):
                conflict_type = 'major_version_diff'

            self.cursor.execute("""
                INSERT INTO dependency_conflicts
                (package_name, version1, version2, manifest1, manifest2, conflict_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (package_name, version1, version2, manifest1, manifest2, conflict_type))
            count += 1

        return count

    def _is_major_version_diff(self, version1: str, version2: str) -> bool:
        """Check if two versions have different major version numbers."""
        def extract_major(version: str) -> Optional[int]:
            # Extract first number from version string
            match = re.search(r'(\d+)', version)
            return int(match.group(1)) if match else None

        major1 = extract_major(version1)
        major2 = extract_major(version2)

        return major1 is not None and major2 is not None and major1 != major2

    def get_dependency_summary(self) -> Dict:
        """Get summary of external dependencies."""
        result = self.cursor.execute("""
            SELECT
                pm.ecosystem,
                pm.name as package_manager,
                COUNT(DISTINCT ed.package_name) as unique_packages,
                COUNT(DISTINCT ed.manifest_file) as manifest_files,
                SUM(CASE WHEN ed.is_dev_dependency THEN 1 ELSE 0 END) as dev_dependencies,
                SUM(CASE WHEN ed.is_dev_dependency THEN 0 ELSE 1 END) as prod_dependencies
            FROM package_managers pm
            LEFT JOIN external_dependencies ed ON pm.id = ed.package_manager_id
            GROUP BY pm.ecosystem, pm.name
            HAVING unique_packages > 0
        """).fetchall()

        return [
            {
                "ecosystem": row[0],
                "package_manager": row[1],
                "unique_packages": row[2],
                "manifest_files": row[3],
                "dev_dependencies": row[4],
                "prod_dependencies": row[5]
            }
            for row in result
        ]

    def get_version_conflicts(self) -> List[Dict]:
        """Get all detected version conflicts."""
        results = self.cursor.execute("""
            SELECT
                package_name,
                version1,
                version2,
                manifest1,
                manifest2,
                conflict_type
            FROM dependency_conflicts
            ORDER BY conflict_type DESC, package_name
        """).fetchall()

        return [
            {
                "package": row[0],
                "version1": row[1],
                "version2": row[2],
                "manifest1": row[3],
                "manifest2": row[4],
                "conflict_type": row[5]
            }
            for row in results
        ]


# Backward compatibility alias - DEPRECATED
EcosystemAnalyzer = ManifestParser
