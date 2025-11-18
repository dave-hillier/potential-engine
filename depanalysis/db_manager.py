"""
Database management for depanalysis.

Handles initialization of structure.db and history.db from schema files,
repository discovery, and multi-database operations.
"""
import sqlite3
from pathlib import Path
from typing import Optional


class DatabaseManager:
    """
    Manages SQLite databases for depanalysis.

    Each repository gets its own structure.db and history.db files,
    stored in data/<repo_name>/ directory.
    """

    def __init__(self, data_dir: Path = None, schema_dir: Path = None):
        """
        Initialize database manager.

        Args:
            data_dir: Directory where repo databases are stored (default: ./data)
            schema_dir: Directory containing SQL schema files (default: ./schema)
        """
        self.data_dir = data_dir or Path("data")
        self.schema_dir = schema_dir or Path("schema")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_repo_db_path(self, repo_name: str, db_type: str) -> Path:
        """
        Get path to a repository's database file.

        Args:
            repo_name: Name of the repository
            db_type: Type of database ('structure' or 'history')

        Returns:
            Path to the database file
        """
        repo_dir = self.data_dir / repo_name
        repo_dir.mkdir(parents=True, exist_ok=True)
        return repo_dir / f"{db_type}.db"

    def initialize_database(self, db_path: Path, schema_file: Path) -> None:
        """
        Initialize a database from a schema file.

        Args:
            db_path: Path where database should be created
            schema_file: Path to SQL schema file
        """
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_file}")

        with sqlite3.connect(db_path) as conn:
            schema_sql = schema_file.read_text()
            conn.executescript(schema_sql)
            conn.commit()

    def initialize_repo_databases(self, repo_name: str) -> tuple[Path, Path]:
        """
        Initialize both structure.db and history.db for a repository.

        Args:
            repo_name: Name of the repository

        Returns:
            Tuple of (structure_db_path, history_db_path)
        """
        structure_db = self.get_repo_db_path(repo_name, "structure")
        history_db = self.get_repo_db_path(repo_name, "history")

        structure_schema = self.schema_dir / "structure.sql"
        history_schema = self.schema_dir / "history.sql"

        if not structure_db.exists():
            self.initialize_database(structure_db, structure_schema)

        if not history_db.exists():
            self.initialize_database(history_db, history_schema)

        return structure_db, history_db

    def list_analyzed_repos(self) -> list[str]:
        """
        List all repositories that have been analyzed.

        Returns:
            List of repository names
        """
        if not self.data_dir.exists():
            return []

        repos = []
        for repo_dir in self.data_dir.iterdir():
            if repo_dir.is_dir():
                # Check if it has at least one database file
                if (repo_dir / "structure.db").exists() or (repo_dir / "history.db").exists():
                    repos.append(repo_dir.name)

        return sorted(repos)

    def get_connection(self, repo_name: str, db_type: str) -> sqlite3.Connection:
        """
        Get a connection to a repository's database.

        Args:
            repo_name: Name of the repository
            db_type: Type of database ('structure' or 'history')

        Returns:
            SQLite connection
        """
        db_path = self.get_repo_db_path(repo_name, db_type)
        if not db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        return conn

    def repo_exists(self, repo_name: str) -> bool:
        """
        Check if a repository has been analyzed.

        Args:
            repo_name: Name of the repository

        Returns:
            True if repository databases exist
        """
        return (self.get_repo_db_path(repo_name, "history").exists() or
                self.get_repo_db_path(repo_name, "structure").exists())

    def delete_repo_databases(self, repo_name: str) -> None:
        """
        Delete all databases for a repository.

        Args:
            repo_name: Name of the repository
        """
        repo_dir = self.data_dir / repo_name
        if repo_dir.exists():
            for db_file in repo_dir.glob("*.db"):
                db_file.unlink()
            repo_dir.rmdir()


def get_repo_name_from_path(repo_path: Path) -> str:
    """
    Extract a clean repository name from a path.

    Args:
        repo_path: Path to the repository

    Returns:
        Repository name suitable for use as directory name
    """
    return repo_path.resolve().name
