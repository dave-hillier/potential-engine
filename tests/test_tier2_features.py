"""
Comprehensive tests for Tier 2 features: Polyglot Repository Support.

Tests:
- TypeScript/JavaScript parser (Feature 4)
- Cross-language dependency tracking (Feature 5)
- Language ecosystem analysis (Feature 6)
"""
import pytest
import sqlite3
import tempfile
from pathlib import Path

from depanalysis.typescript_analyzer import TypeScriptAnalyzer
from depanalysis.cross_language_analyzer import CrossLanguageAnalyzer
from depanalysis.ecosystem_analyzer import EcosystemAnalyzer
from depanalysis.db_manager import DatabaseManager


class TestTypeScriptJavaScriptParser:
    """Test suite for TypeScript/JavaScript parser."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a temporary repository with TypeScript/JavaScript files."""
        repo = tmp_path / "test_repo"
        repo.mkdir()

        # Create TypeScript file with class and imports
        ts_file = repo / "example.ts"
        ts_file.write_text("""
import { Component } from 'react';
import * as utils from './utils';

export class MyComponent extends Component {
    async fetchData() {
        const response = await fetch('/api/data');
        return response.json();
    }
}

export function helperFunction() {
    return 42;
}
""")

        # Create JavaScript file with imports
        js_file = repo / "app.js"
        js_file.write_text("""
const express = require('express');
const { getData } = require('./data');

function main() {
    const app = express();
    app.get('/api/data', (req, res) => {
        res.json({ data: getData() });
    });
}
""")

        # Create React TSX file
        tsx_file = repo / "Button.tsx"
        tsx_file.write_text("""
import React from 'react';

interface ButtonProps {
    label: string;
    onClick: () => void;
}

export const Button: React.FC<ButtonProps> = ({ label, onClick }) => {
    return <button onClick={onClick}>{label}</button>;
};
""")

        return repo

    @pytest.fixture
    def structure_db(self, tmp_path):
        """Create a structure database for testing."""
        db_manager = DatabaseManager(data_dir=tmp_path / "data", schema_dir=Path("schema"))
        structure_db_path, _ = db_manager.initialize_repo_databases("test_repo")
        conn = sqlite3.connect(structure_db_path)
        return conn

    def test_typescript_file_parsing(self, temp_repo, structure_db):
        """Test that TypeScript files are parsed correctly."""
        analyzer = TypeScriptAnalyzer(temp_repo, structure_db)
        stats = analyzer.analyze()

        assert stats['files_parsed'] > 0, "Should parse TypeScript files"
        assert stats['typescript_files'] > 0, "Should count TypeScript files"
        assert stats['imports_found'] > 0, "Should extract imports"
        assert stats['classes_found'] > 0, "Should extract classes"
        assert stats['functions_found'] > 0, "Should extract functions"

    def test_javascript_file_parsing(self, temp_repo, structure_db):
        """Test that JavaScript files are parsed correctly."""
        analyzer = TypeScriptAnalyzer(temp_repo, structure_db)
        stats = analyzer.analyze()

        assert stats['javascript_files'] > 0, "Should count JavaScript files"

    def test_es6_imports(self, temp_repo, structure_db):
        """Test ES6 import statement extraction."""
        analyzer = TypeScriptAnalyzer(temp_repo, structure_db)
        analyzer.analyze()

        cursor = structure_db.cursor()
        imports = cursor.execute("""
            SELECT import_name, to_module, import_kind
            FROM imports
            WHERE import_kind = 'import'
        """).fetchall()

        assert len(imports) > 0, "Should find ES6 imports"
        import_names = [imp[0] for imp in imports]
        assert 'Component' in import_names or 'React' in import_names

    def test_commonjs_requires(self, temp_repo, structure_db):
        """Test CommonJS require statement extraction."""
        analyzer = TypeScriptAnalyzer(temp_repo, structure_db)
        analyzer.analyze()

        cursor = structure_db.cursor()
        requires = cursor.execute("""
            SELECT import_name, to_module, import_kind
            FROM imports
            WHERE import_kind = 'require'
        """).fetchall()

        assert len(requires) > 0, "Should find CommonJS requires"
        modules = [req[1] for req in requires]
        assert 'express' in modules

    def test_async_function_detection(self, temp_repo, structure_db):
        """Test async function detection."""
        analyzer = TypeScriptAnalyzer(temp_repo, structure_db)
        analyzer.analyze()

        cursor = structure_db.cursor()
        async_funcs = cursor.execute("""
            SELECT name, is_async
            FROM functions
            WHERE is_async = 1
        """).fetchall()

        assert len(async_funcs) > 0, "Should detect async functions"

    def test_class_inheritance(self, temp_repo, structure_db):
        """Test class inheritance extraction."""
        analyzer = TypeScriptAnalyzer(temp_repo, structure_db)
        analyzer.analyze()

        cursor = structure_db.cursor()
        inheritance = cursor.execute("""
            SELECT base_class_name, relationship_kind
            FROM inheritance
            WHERE relationship_kind = 'extends'
        """).fetchall()

        assert len(inheritance) > 0, "Should extract class inheritance"
        base_classes = [inh[0] for inh in inheritance]
        assert 'Component' in base_classes


class TestCrossLanguageDependencyTracking:
    """Test suite for cross-language dependency tracking."""

    @pytest.fixture
    def polyglot_repo(self, tmp_path):
        """Create a temporary polyglot repository."""
        repo = tmp_path / "polyglot_repo"
        repo.mkdir()

        # Python Flask API
        python_api = repo / "api.py"
        python_api.write_text("""
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/users', methods=['GET'])
def get_users():
    return jsonify(users=[])

@app.route('/api/products/<int:id>', methods=['GET'])
def get_product(id):
    return jsonify(product={'id': id})
""")

        # TypeScript frontend calling API
        ts_frontend = repo / "frontend.ts"
        ts_frontend.write_text("""
import axios from 'axios';

async function fetchUsers() {
    const response = await fetch('/api/users');
    return response.json();
}

async function getProduct(id: number) {
    return axios.get(`/api/products/${id}`);
}
""")

        # Protocol Buffer definition
        proto_file = repo / "user.proto"
        proto_file.write_text("""
syntax = "proto3";

message User {
    int32 id = 1;
    string name = 2;
    string email = 3;
}

message UserList {
    repeated User users = 1;
}
""")

        # GraphQL schema
        graphql_file = repo / "schema.graphql"
        graphql_file.write_text("""
type User {
    id: ID!
    name: String!
    email: String!
}

type Query {
    users: [User!]!
    user(id: ID!): User
}
""")

        return repo

    @pytest.fixture
    def polyglot_db(self, tmp_path, polyglot_repo):
        """Create databases for polyglot testing."""
        db_manager = DatabaseManager(data_dir=tmp_path / "data", schema_dir=Path("schema"))
        structure_db_path, history_db_path = db_manager.initialize_repo_databases("polyglot_repo")
        structure_conn = sqlite3.connect(structure_db_path)
        history_conn = sqlite3.connect(history_db_path)

        # Pre-parse the files with Python and TypeScript analyzers
        from depanalysis.structure_analyzer import StructureAnalyzer
        py_analyzer = StructureAnalyzer(polyglot_repo, structure_conn)
        py_analyzer.analyze()

        ts_analyzer = TypeScriptAnalyzer(polyglot_repo, structure_conn)
        ts_analyzer.analyze()

        return structure_conn, history_conn

    def test_api_endpoint_detection(self, polyglot_repo, polyglot_db):
        """Test Python Flask API endpoint detection."""
        structure_conn, history_conn = polyglot_db
        analyzer = CrossLanguageAnalyzer(polyglot_repo, structure_conn, history_conn)
        stats = analyzer.analyze()

        assert stats['api_endpoints_found'] > 0, "Should find Flask API endpoints"

        cursor = structure_conn.cursor()
        endpoints = cursor.execute("""
            SELECT path, method, endpoint_type
            FROM api_endpoints
        """).fetchall()

        paths = [ep[0] for ep in endpoints]
        assert '/api/users' in paths
        assert any('/api/products' in p for p in paths)

    def test_api_call_detection(self, polyglot_repo, polyglot_db):
        """Test TypeScript API call detection."""
        structure_conn, history_conn = polyglot_db
        analyzer = CrossLanguageAnalyzer(polyglot_repo, structure_conn, history_conn)
        stats = analyzer.analyze()

        assert stats['api_calls_found'] > 0, "Should find API calls"

        cursor = structure_conn.cursor()
        calls = cursor.execute("""
            SELECT url_pattern, method, call_type
            FROM api_calls
        """).fetchall()

        assert len(calls) > 0, "Should detect fetch and axios calls"
        call_types = [call[2] for call in calls]
        assert 'fetch' in call_types or 'axios' in call_types

    def test_protocol_buffer_detection(self, polyglot_repo, polyglot_db):
        """Test Protocol Buffer shared type detection."""
        structure_conn, history_conn = polyglot_db
        analyzer = CrossLanguageAnalyzer(polyglot_repo, structure_conn, history_conn)
        stats = analyzer.analyze()

        assert stats['proto_files'] > 0, "Should find Protocol Buffer files"
        assert stats['shared_types_found'] > 0, "Should find shared types"

        cursor = structure_conn.cursor()
        types = cursor.execute("""
            SELECT name, type_system
            FROM shared_types
            WHERE type_system = 'protobuf'
        """).fetchall()

        type_names = [t[0] for t in types]
        assert 'User' in type_names
        assert 'UserList' in type_names

    def test_graphql_schema_detection(self, polyglot_repo, polyglot_db):
        """Test GraphQL schema shared type detection."""
        structure_conn, history_conn = polyglot_db
        analyzer = CrossLanguageAnalyzer(polyglot_repo, structure_conn, history_conn)
        stats = analyzer.analyze()

        assert stats['graphql_files'] > 0, "Should find GraphQL schema files"

        cursor = structure_conn.cursor()
        types = cursor.execute("""
            SELECT name, type_system
            FROM shared_types
            WHERE type_system = 'graphql'
        """).fetchall()

        type_names = [t[0] for t in types]
        assert 'User' in type_names
        assert 'Query' in type_names

    def test_api_boundary_coupling(self, polyglot_repo, polyglot_db):
        """Test API boundary coupling detection."""
        structure_conn, history_conn = polyglot_db
        analyzer = CrossLanguageAnalyzer(polyglot_repo, structure_conn, history_conn)
        analyzer.analyze()

        coupling = analyzer.get_api_boundary_coupling()
        assert len(coupling) > 0, "Should find API boundary couplings"


class TestLanguageEcosystemAnalysis:
    """Test suite for language ecosystem analysis."""

    @pytest.fixture
    def ecosystem_repo(self, tmp_path):
        """Create a repository with various package manager files."""
        repo = tmp_path / "ecosystem_repo"
        repo.mkdir()

        # Python requirements.txt
        requirements = repo / "requirements.txt"
        requirements.write_text("""
flask==2.3.0
requests>=2.28.0
pytest>=7.0.0  # dev dependency
pandas==2.0.0
""")

        # Python pyproject.toml
        pyproject = repo / "pyproject.toml"
        pyproject.write_text("""
[tool.poetry.dependencies]
python = "^3.9"
fastapi = "^0.100.0"
sqlalchemy = "^2.0.0"

[tool.poetry.dev-dependencies]
black = "^23.0.0"
mypy = "^1.0.0"
""")

        # JavaScript package.json
        package_json = repo / "package.json"
        package_json.write_text("""
{
  "name": "test-project",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.2.0",
    "axios": "^1.4.0",
    "lodash": "^4.17.21"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "jest": "^29.0.0"
  }
}
""")

        # Rust Cargo.toml
        cargo_toml = repo / "Cargo.toml"
        cargo_toml.write_text("""
[package]
name = "test-project"
version = "0.1.0"

[dependencies]
serde = "1.0"
tokio = { version = "1.28", features = ["full"] }

[dev-dependencies]
criterion = "0.5"
""")

        # Go go.mod
        go_mod = repo / "go.mod"
        go_mod.write_text("""
module example.com/myproject

go 1.20

require (
    github.com/gin-gonic/gin v1.9.0
    github.com/stretchr/testify v1.8.4
)
""")

        # Create a conflict scenario - different versions
        requirements2 = repo / "requirements-prod.txt"
        requirements2.write_text("""
flask==2.2.0
requests>=2.30.0
pandas==1.5.0
""")

        return repo

    @pytest.fixture
    def ecosystem_db(self, tmp_path):
        """Create structure database for ecosystem testing."""
        db_manager = DatabaseManager(data_dir=tmp_path / "data", schema_dir=Path("schema"))
        structure_db_path, _ = db_manager.initialize_repo_databases("ecosystem_repo")
        conn = sqlite3.connect(structure_db_path)
        return conn

    def test_python_requirements_parsing(self, ecosystem_repo, ecosystem_db):
        """Test Python requirements.txt parsing."""
        analyzer = EcosystemAnalyzer(ecosystem_repo, ecosystem_db)
        stats = analyzer.analyze()

        assert stats['python_deps'] > 0, "Should find Python dependencies"
        assert stats['manifest_files'] > 0, "Should find manifest files"

        cursor = ecosystem_db.cursor()
        deps = cursor.execute("""
            SELECT package_name, version_spec
            FROM external_dependencies ed
            JOIN package_managers pm ON ed.package_manager_id = pm.id
            WHERE pm.name = 'pip'
        """).fetchall()

        package_names = [dep[0] for dep in deps]
        assert 'flask' in package_names
        assert 'requests' in package_names

    def test_python_pyproject_toml_parsing(self, ecosystem_repo, ecosystem_db):
        """Test pyproject.toml parsing."""
        analyzer = EcosystemAnalyzer(ecosystem_repo, ecosystem_db)
        stats = analyzer.analyze()

        cursor = ecosystem_db.cursor()
        deps = cursor.execute("""
            SELECT package_name, version_spec, is_dev_dependency
            FROM external_dependencies ed
            JOIN package_managers pm ON ed.package_manager_id = pm.id
            WHERE pm.name = 'poetry'
        """).fetchall()

        package_names = [dep[0] for dep in deps]
        assert 'fastapi' in package_names or 'sqlalchemy' in package_names

    def test_javascript_package_json_parsing(self, ecosystem_repo, ecosystem_db):
        """Test package.json parsing."""
        analyzer = EcosystemAnalyzer(ecosystem_repo, ecosystem_db)
        stats = analyzer.analyze()

        assert stats['javascript_deps'] > 0, "Should find JavaScript dependencies"

        cursor = ecosystem_db.cursor()
        deps = cursor.execute("""
            SELECT package_name, version_spec, is_dev_dependency
            FROM external_dependencies ed
            JOIN package_managers pm ON ed.package_manager_id = pm.id
            WHERE pm.name = 'npm'
        """).fetchall()

        package_names = [dep[0] for dep in deps]
        assert 'react' in package_names
        assert 'axios' in package_names

        # Check dev dependencies
        dev_deps = [dep[0] for dep in deps if dep[2]]
        assert 'typescript' in dev_deps or 'jest' in dev_deps

    def test_rust_cargo_toml_parsing(self, ecosystem_repo, ecosystem_db):
        """Test Cargo.toml parsing."""
        analyzer = EcosystemAnalyzer(ecosystem_repo, ecosystem_db)
        stats = analyzer.analyze()

        assert stats['rust_deps'] > 0, "Should find Rust dependencies"

        cursor = ecosystem_db.cursor()
        deps = cursor.execute("""
            SELECT package_name, version_spec
            FROM external_dependencies ed
            JOIN package_managers pm ON ed.package_manager_id = pm.id
            WHERE pm.name = 'cargo'
        """).fetchall()

        package_names = [dep[0] for dep in deps]
        assert 'serde' in package_names
        assert 'tokio' in package_names

    def test_go_mod_parsing(self, ecosystem_repo, ecosystem_db):
        """Test go.mod parsing."""
        analyzer = EcosystemAnalyzer(ecosystem_repo, ecosystem_db)
        stats = analyzer.analyze()

        assert stats['go_deps'] > 0, "Should find Go dependencies"

        cursor = ecosystem_db.cursor()
        deps = cursor.execute("""
            SELECT package_name, version_spec
            FROM external_dependencies ed
            JOIN package_managers pm ON ed.package_manager_id = pm.id
            WHERE pm.name = 'go_modules'
        """).fetchall()

        package_names = [dep[0] for dep in deps]
        assert any('gin' in name for name in package_names)

    def test_version_conflict_detection(self, ecosystem_repo, ecosystem_db):
        """Test version conflict detection across manifest files."""
        analyzer = EcosystemAnalyzer(ecosystem_repo, ecosystem_db)
        stats = analyzer.analyze()

        assert stats['conflicts_found'] > 0, "Should detect version conflicts"

        cursor = ecosystem_db.cursor()
        conflicts = cursor.execute("""
            SELECT package_name, version1, version2, conflict_type
            FROM dependency_conflicts
        """).fetchall()

        conflict_packages = [c[0] for c in conflicts]
        # flask has different versions in requirements.txt (2.3.0) and requirements-prod.txt (2.2.0)
        assert 'flask' in conflict_packages or 'pandas' in conflict_packages

    def test_dependency_summary(self, ecosystem_repo, ecosystem_db):
        """Test dependency summary generation."""
        analyzer = EcosystemAnalyzer(ecosystem_repo, ecosystem_db)
        analyzer.analyze()

        summary = analyzer.get_dependency_summary()
        assert len(summary) > 0, "Should generate dependency summary"

        ecosystems = [item['ecosystem'] for item in summary]
        assert 'python' in ecosystems
        assert 'javascript' in ecosystems

    def test_version_conflicts_report(self, ecosystem_repo, ecosystem_db):
        """Test version conflicts report."""
        analyzer = EcosystemAnalyzer(ecosystem_repo, ecosystem_db)
        analyzer.analyze()

        conflicts = analyzer.get_version_conflicts()
        assert len(conflicts) > 0, "Should generate conflicts report"

        # Verify conflict structure
        for conflict in conflicts:
            assert 'package' in conflict
            assert 'version1' in conflict
            assert 'version2' in conflict
            assert 'conflict_type' in conflict


class TestPolyglotIntegration:
    """Integration tests for polyglot repository analysis."""

    @pytest.fixture
    def full_polyglot_repo(self, tmp_path):
        """Create a complete polyglot repository."""
        repo = tmp_path / "full_polyglot"
        repo.mkdir()

        # Python backend
        (repo / "backend").mkdir()
        (repo / "backend" / "api.py").write_text("""
from flask import Flask
app = Flask(__name__)

@app.route('/api/data')
def get_data():
    return {'data': []}
""")

        # TypeScript frontend
        (repo / "frontend").mkdir()
        (repo / "frontend" / "App.tsx").write_text("""
import React from 'react';

function App() {
    const fetchData = async () => {
        const res = await fetch('/api/data');
        return res.json();
    };
    return <div>App</div>;
}
""")

        # Package manifests
        (repo / "requirements.txt").write_text("flask==2.3.0\n")
        (repo / "package.json").write_text('{"dependencies": {"react": "^18.0.0"}}')

        return repo

    def test_full_polyglot_analysis(self, full_polyglot_repo, tmp_path):
        """Test complete analysis of polyglot repository."""
        db_manager = DatabaseManager(data_dir=tmp_path / "data", schema_dir=Path("schema"))
        structure_db_path, history_db_path = db_manager.initialize_repo_databases("full_polyglot")

        structure_conn = sqlite3.connect(structure_db_path)
        history_conn = sqlite3.connect(history_db_path)

        # Run all analyzers
        from depanalysis.structure_analyzer import StructureAnalyzer
        py_analyzer = StructureAnalyzer(full_polyglot_repo, structure_conn)
        py_stats = py_analyzer.analyze()

        ts_analyzer = TypeScriptAnalyzer(full_polyglot_repo, structure_conn)
        ts_stats = ts_analyzer.analyze()

        cross_analyzer = CrossLanguageAnalyzer(full_polyglot_repo, structure_conn, history_conn)
        cross_stats = cross_analyzer.analyze()

        eco_analyzer = EcosystemAnalyzer(full_polyglot_repo, structure_conn)
        eco_stats = eco_analyzer.analyze()

        # Verify all analyzers ran successfully
        assert py_stats['files_parsed'] > 0, "Python analyzer should work"
        assert ts_stats['files_parsed'] > 0, "TypeScript analyzer should work"
        assert cross_stats['api_endpoints_found'] > 0, "Cross-language analyzer should find APIs"
        assert eco_stats['dependencies_found'] > 0, "Ecosystem analyzer should find dependencies"

        # Verify polyglot language detection
        cursor = structure_conn.cursor()
        languages = cursor.execute("""
            SELECT DISTINCT l.name
            FROM modules m
            JOIN languages l ON m.language_id = l.id
        """).fetchall()

        language_names = [lang[0] for lang in languages]
        assert 'python' in language_names
        assert 'typescript' in language_names or 'javascript' in language_names

        structure_conn.close()
        history_conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
