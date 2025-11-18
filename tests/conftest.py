"""Pytest fixtures and test utilities."""
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import shutil

import pytest
import git

from depanalysis.db_manager import DatabaseManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def schema_dir():
    """Get the schema directory path."""
    return Path(__file__).parent.parent / "schema"


@pytest.fixture
def db_manager(temp_dir, schema_dir):
    """Create a DatabaseManager instance with test directories."""
    return DatabaseManager(data_dir=temp_dir / "data", schema_dir=schema_dir)


@pytest.fixture
def history_db(db_manager):
    """Create an initialized history database."""
    db_path = db_manager.get_repo_db_path("test_repo", "history")
    schema_file = db_manager.schema_dir / "history.sql"
    db_manager.initialize_database(db_path, schema_file)

    conn = sqlite3.connect(db_path)
    yield conn
    conn.close()


@pytest.fixture
def structure_db(db_manager):
    """Create an initialized structure database."""
    db_path = db_manager.get_repo_db_path("test_repo", "structure")
    schema_file = db_manager.schema_dir / "structure.sql"
    db_manager.initialize_database(db_path, schema_file)

    conn = sqlite3.connect(db_path)
    yield conn
    conn.close()


@pytest.fixture
def sample_git_repo(temp_dir):
    """
    Create a sample Git repository with known history for testing.

    Creates a repository with:
    - 3 files: file_a.py, file_b.py, file_c.py
    - Multiple commits showing different coupling patterns
    """
    repo_path = temp_dir / "sample_repo"
    repo_path.mkdir()

    # Initialize git repo
    repo = git.Repo.init(repo_path)

    # Configure git user (required for commits)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@example.com")

    # Commit 1: Add file_a.py and file_b.py together
    (repo_path / "file_a.py").write_text("# File A\nprint('a')\n")
    (repo_path / "file_b.py").write_text("# File B\nprint('b')\n")
    repo.index.add(["file_a.py", "file_b.py"])
    repo.index.commit("Initial commit: add files A and B")

    # Commit 2: Add file_c.py alone
    (repo_path / "file_c.py").write_text("# File C\nprint('c')\n")
    repo.index.add(["file_c.py"])
    repo.index.commit("Add file C")

    # Commit 3: Modify file_a.py and file_b.py together again
    (repo_path / "file_a.py").write_text("# File A\nprint('a')\nprint('modified')\n")
    (repo_path / "file_b.py").write_text("# File B\nprint('b')\nprint('modified')\n")
    repo.index.add(["file_a.py", "file_b.py"])
    repo.index.commit("Modify files A and B together")

    # Commit 4: Modify file_a.py alone
    (repo_path / "file_a.py").write_text("# File A\nprint('a')\nprint('modified')\nprint('again')\n")
    repo.index.add(["file_a.py"])
    repo.index.commit("Modify file A alone")

    # Commit 5: Modify file_b.py and file_c.py together
    (repo_path / "file_b.py").write_text("# File B\nprint('b')\nprint('modified')\nprint('with c')\n")
    (repo_path / "file_c.py").write_text("# File C\nprint('c')\nprint('modified')\n")
    repo.index.add(["file_b.py", "file_c.py"])
    repo.index.commit("Modify files B and C together")

    yield repo_path

    # Cleanup is automatic with temp_dir


@pytest.fixture
def sample_structure_data(structure_db):
    """
    Populate structure database with sample data for testing structural coupling.

    Creates a structure with:
    - 3 modules with import relationships
    - 3 classes with inheritance relationships
    - Multiple functions with call relationships
    """
    cursor = structure_db.cursor()

    # Insert modules
    cursor.execute("""
        INSERT INTO modules (id, language_id, path, name, file_hash)
        VALUES
            (1, 1, 'module_a.py', 'module_a', 'hash_a'),
            (2, 1, 'module_b.py', 'module_b', 'hash_b'),
            (3, 1, 'module_c.py', 'module_c', 'hash_c')
    """)

    # Insert imports (file-to-file coupling)
    # module_a imports module_b
    # module_b imports module_c
    # module_c imports module_a (circular)
    cursor.execute("""
        INSERT INTO imports (from_module_id, to_module, import_name, import_kind, line_number)
        VALUES
            (1, 'module_b', 'module_b', 'import', 1),
            (2, 'module_c', 'module_c', 'import', 1),
            (3, 'module_a', 'module_a', 'import', 1)
    """)

    # Insert classes
    cursor.execute("""
        INSERT INTO classes (id, module_id, name, qualified_name, kind, line_start, line_end)
        VALUES
            (1, 1, 'ClassA', 'module_a.ClassA', 'class', 1, 10),
            (2, 2, 'ClassB', 'module_b.ClassB', 'class', 1, 10),
            (3, 3, 'ClassC', 'module_c.ClassC', 'class', 1, 10)
    """)

    # Insert inheritance (class-to-class coupling)
    # ClassB inherits from ClassA
    # ClassC inherits from ClassB
    cursor.execute("""
        INSERT INTO inheritance (class_id, base_class_id, base_class_name, relationship_kind, position)
        VALUES
            (2, 1, 'ClassA', 'inherits', 0),
            (3, 2, 'ClassB', 'inherits', 0)
    """)

    # Insert functions
    cursor.execute("""
        INSERT INTO functions (id, module_id, class_id, name, qualified_name, kind, line_start, line_end)
        VALUES
            (1, 1, 1, 'method_a', 'module_a.ClassA.method_a', 'method', 2, 5),
            (2, 2, 2, 'method_b', 'module_b.ClassB.method_b', 'method', 2, 5),
            (3, 3, 3, 'method_c', 'module_c.ClassC.method_c', 'method', 2, 5)
    """)

    # Insert function calls (method-to-method coupling)
    # method_b calls method_a
    # method_c calls method_b
    cursor.execute("""
        INSERT INTO calls (from_function_id, to_function_id, to_name, call_kind, line_number)
        VALUES
            (2, 1, 'method_a', 'call', 3),
            (3, 2, 'method_b', 'call', 3)
    """)

    structure_db.commit()
    yield structure_db
