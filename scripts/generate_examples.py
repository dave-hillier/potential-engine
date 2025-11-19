#!/usr/bin/env python3
"""
Generate example repositories for testing and documentation.

Creates three example repositories:
- simple-linear: Single author, linear history
- multi-author: Multiple authors, moderate complexity
- high-churn: High change frequency, temporal coupling patterns
"""

import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone
import git


def create_simple_linear_repo(base_path: Path):
    """
    Create a simple repository with linear history.

    Single author, clear dependency chain, minimal churn.
    """
    repo_path = base_path / "simple-linear"
    if repo_path.exists():
        shutil.rmtree(repo_path)
    repo_path.mkdir(parents=True)

    repo = git.Repo.init(repo_path)

    # Configure git user
    with repo.config_writer() as config:
        config.set_value("user", "name", "Alice Developer")
        config.set_value("user", "email", "alice@example.com")

    # Commit 1: Initial project structure
    (repo_path / "main.py").write_text("""#!/usr/bin/env python3
\"\"\"Main entry point.\"\"\"

def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
""")
    repo.index.add(["main.py"])
    repo.index.commit("Initial commit: Add main.py", author_date=datetime.now(timezone.utc) - timedelta(days=30))

    # Commit 2: Add utils module
    (repo_path / "utils.py").write_text("""\"\"\"Utility functions.\"\"\"

def helper():
    return "Helper function"

def format_output(text):
    return f"Output: {text}"
""")
    repo.index.add(["utils.py"])
    repo.index.commit("Add utils module", author_date=datetime.now(timezone.utc) - timedelta(days=25))

    # Commit 3: Use utils in main
    (repo_path / "main.py").write_text("""#!/usr/bin/env python3
\"\"\"Main entry point.\"\"\"

from utils import format_output

def main():
    message = format_output("Hello, World!")
    print(message)

if __name__ == "__main__":
    main()
""")
    repo.index.add(["main.py"])
    repo.index.commit("Use utils in main", author_date=datetime.now(timezone.utc) - timedelta(days=20))

    # Commit 4: Add config module
    (repo_path / "config.py").write_text("""\"\"\"Configuration settings.\"\"\"

DEBUG = True
VERSION = "1.0.0"
""")
    repo.index.add(["config.py"])
    repo.index.commit("Add config module", author_date=datetime.now(timezone.utc) - timedelta(days=15))

    # Commit 5: Update main to use config
    (repo_path / "main.py").write_text("""#!/usr/bin/env python3
\"\"\"Main entry point.\"\"\"

from utils import format_output
from config import VERSION

def main():
    message = format_output(f"Hello, World! v{VERSION}")
    print(message)

if __name__ == "__main__":
    main()
""")
    repo.index.add(["main.py"])
    repo.index.commit("Add version to main", author_date=datetime.now(timezone.utc) - timedelta(days=10))

    print(f"✓ Created simple-linear repository with 5 commits")


def create_multi_author_repo(base_path: Path):
    """
    Create a repository with multiple authors and overlapping changes.

    Multiple contributors, some temporal coupling, moderate complexity.
    """
    repo_path = base_path / "multi-author"
    if repo_path.exists():
        shutil.rmtree(repo_path)
    repo_path.mkdir(parents=True)

    repo = git.Repo.init(repo_path)

    authors = [
        ("Alice Developer", "alice@example.com"),
        ("Bob Engineer", "bob@example.com"),
        ("Charlie Coder", "charlie@example.com")
    ]

    # Set default author
    with repo.config_writer() as config:
        config.set_value("user", "name", authors[0][0])
        config.set_value("user", "email", authors[0][1])

    # Commit 1: Alice - Initial structure
    (repo_path / "server.py").write_text("""\"\"\"Server implementation.\"\"\"

class Server:
    def __init__(self):
        self.port = 8000

    def start(self):
        print(f"Starting server on port {self.port}")
""")
    repo.index.add(["server.py"])
    commit_date = datetime.now(timezone.utc) - timedelta(days=30)
    repo.index.commit("Initial server implementation",
                     author=git.Actor(authors[0][0], authors[0][1]),
                     author_date=commit_date)

    # Commit 2: Bob - Add client
    (repo_path / "client.py").write_text("""\"\"\"Client implementation.\"\"\"

class Client:
    def __init__(self, host="localhost"):
        self.host = host

    def connect(self):
        print(f"Connecting to {self.host}")
""")
    repo.index.add(["client.py"])
    commit_date = datetime.now(timezone.utc) - timedelta(days=28)
    repo.index.commit("Add client implementation",
                     author=git.Actor(authors[1][0], authors[1][1]),
                     author_date=commit_date)

    # Commit 3: Charlie - Add shared protocol
    (repo_path / "protocol.py").write_text("""\"\"\"Shared protocol definitions.\"\"\"

class Message:
    def __init__(self, content):
        self.content = content

    def serialize(self):
        return self.content.encode()
""")
    repo.index.add(["protocol.py"])
    commit_date = datetime.now(timezone.utc) - timedelta(days=25)
    repo.index.commit("Add protocol module",
                     author=git.Actor(authors[2][0], authors[2][1]),
                     author_date=commit_date)

    # Commit 4: Alice - Update server to use protocol
    (repo_path / "server.py").write_text("""\"\"\"Server implementation.\"\"\"

from protocol import Message

class Server:
    def __init__(self):
        self.port = 8000

    def start(self):
        print(f"Starting server on port {self.port}")

    def send(self, content):
        msg = Message(content)
        return msg.serialize()
""")
    repo.index.add(["server.py"])
    commit_date = datetime.now(timezone.utc) - timedelta(days=20)
    repo.index.commit("Server uses protocol",
                     author=git.Actor(authors[0][0], authors[0][1]),
                     author_date=commit_date)

    # Commit 5: Bob - Update client to use protocol
    (repo_path / "client.py").write_text("""\"\"\"Client implementation.\"\"\"

from protocol import Message

class Client:
    def __init__(self, host="localhost"):
        self.host = host

    def connect(self):
        print(f"Connecting to {self.host}")

    def receive(self, data):
        msg = Message(data.decode())
        return msg.content
""")
    repo.index.add(["client.py"])
    commit_date = datetime.now(timezone.utc) - timedelta(days=18)
    repo.index.commit("Client uses protocol",
                     author=git.Actor(authors[1][0], authors[1][1]),
                     author_date=commit_date)

    # Commit 6: Charlie - Update protocol (temporal coupling!)
    (repo_path / "protocol.py").write_text("""\"\"\"Shared protocol definitions.\"\"\"

class Message:
    def __init__(self, content, priority=0):
        self.content = content
        self.priority = priority

    def serialize(self):
        return f"{self.priority}:{self.content}".encode()
""")
    (repo_path / "server.py").write_text("""\"\"\"Server implementation.\"\"\"

from protocol import Message

class Server:
    def __init__(self):
        self.port = 8000

    def start(self):
        print(f"Starting server on port {self.port}")

    def send(self, content, priority=0):
        msg = Message(content, priority)
        return msg.serialize()
""")
    repo.index.add(["protocol.py", "server.py"])
    commit_date = datetime.now(timezone.utc) - timedelta(days=15)
    repo.index.commit("Add priority to protocol",
                     author=git.Actor(authors[2][0], authors[2][1]),
                     author_date=commit_date)

    # Commit 7: Alice - Update client for priority
    (repo_path / "client.py").write_text("""\"\"\"Client implementation.\"\"\"

from protocol import Message

class Client:
    def __init__(self, host="localhost"):
        self.host = host

    def connect(self):
        print(f"Connecting to {self.host}")

    def receive(self, data):
        priority, content = data.decode().split(":", 1)
        msg = Message(content, int(priority))
        return msg.content, msg.priority
""")
    repo.index.add(["client.py"])
    commit_date = datetime.now(timezone.utc) - timedelta(days=12)
    repo.index.commit("Client handles priority",
                     author=git.Actor(authors[0][0], authors[0][1]),
                     author_date=commit_date)

    print(f"✓ Created multi-author repository with 7 commits from 3 authors")


def create_high_churn_repo(base_path: Path):
    """
    Create a repository with high churn and temporal coupling.

    Frequent changes, strong temporal coupling, hotspot patterns.
    """
    repo_path = base_path / "high-churn"
    if repo_path.exists():
        shutil.rmtree(repo_path)
    repo_path.mkdir(parents=True)

    repo = git.Repo.init(repo_path)

    # Configure git user
    with repo.config_writer() as config:
        config.set_value("user", "name", "Rapid Developer")
        config.set_value("user", "email", "rapid@example.com")

    # Initial files
    (repo_path / "models.py").write_text("""\"\"\"Data models.\"\"\"

class User:
    def __init__(self, name):
        self.name = name
""")

    (repo_path / "views.py").write_text("""\"\"\"View functions.\"\"\"

def show_user(user):
    return f"User: {user.name}"
""")

    (repo_path / "tests.py").write_text("""\"\"\"Test suite.\"\"\"

def test_user():
    pass
""")

    repo.index.add(["models.py", "views.py", "tests.py"])
    repo.index.commit("Initial implementation",
                     author_date=datetime.now(timezone.utc) - timedelta(days=30))

    # Generate many iterations with strong coupling
    for i in range(1, 11):
        days_ago = 28 - (i * 2)

        # Iteration: models and views always change together (strong coupling)
        (repo_path / "models.py").write_text(f"""\"\"\"Data models.\"\"\"

class User:
    def __init__(self, name, version={i}):
        self.name = name
        self.version = {i}

    def to_dict(self):
        return {{"name": self.name, "version": self.version}}
""")

        (repo_path / "views.py").write_text(f"""\"\"\"View functions.\"\"\"

def show_user(user):
    data = user.to_dict()
    return f"User: {{data['name']}} (v{{data['version']}})"
""")

        repo.index.add(["models.py", "views.py"])
        repo.index.commit(f"Iteration {i}: Update models and views",
                         author_date=datetime.now(timezone.utc) - timedelta(days=days_ago))

        # Sometimes update tests too
        if i % 3 == 0:
            (repo_path / "tests.py").write_text(f"""\"\"\"Test suite.\"\"\"

def test_user():
    from models import User
    user = User("test")
    assert user.version == {i}
""")
            repo.index.add(["tests.py"])
            repo.index.commit(f"Update tests for iteration {i}",
                             author_date=datetime.now(timezone.utc) - timedelta(days=days_ago - 0.5))

    print(f"✓ Created high-churn repository with 14 commits showing temporal coupling")


def main():
    """Generate all example repositories."""
    base_path = Path(__file__).parent.parent / "examples" / "repos"
    base_path.mkdir(parents=True, exist_ok=True)

    print("Generating example repositories...")
    print("=" * 70)

    create_simple_linear_repo(base_path)
    create_multi_author_repo(base_path)
    create_high_churn_repo(base_path)

    print("=" * 70)
    print("✓ All example repositories created successfully!")
    print(f"\nLocation: {base_path.absolute()}")
    print("\nNext steps:")
    print("  1. Run: depanalysis regenerate-examples")
    print("  2. Run tests: pytest tests/test_examples.py")


if __name__ == "__main__":
    main()
