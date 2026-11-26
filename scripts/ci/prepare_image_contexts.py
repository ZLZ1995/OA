"""Prepare allowlisted, non-production Docker contexts; never copy live data."""

import argparse
import shutil
from pathlib import Path


def ignored(directory, names):
    """Defense in depth for files nested inside allowed source directories."""
    return [name for name in names if (
        name in {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "uploads", "backups"}
        or name.startswith(".env")
        or name.lower().endswith((".pem", ".key", ".p12", ".pfx", ".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3", ".pyc"))
    )]


def copy(source, target):
    if source.is_symlink():
        raise ValueError(f"Symlink is not allowed: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        for entry in source.rglob("*"):
            if entry.is_symlink():
                raise ValueError(f"Symlink is not allowed: {entry}")
        shutil.copytree(source, target, ignore=ignored)
    else:
        shutil.copy2(source, target)


def prepare(repo, output):
    repo, output = Path(repo).resolve(), Path(output).resolve()
    if output == repo or repo in output.parents:
        raise ValueError("Build contexts must be outside the repository")
    # Refuse to overwrite any existing directory.
    output.mkdir(parents=True, exist_ok=False)
    backend, frontend = output / "backend", output / "frontend"
    for item in ("Dockerfile", "start", "backend/app", "backend/migrations", "backend/alembic.ini", "backend/requirements.txt"):
        copy(repo / item, backend / item)
    # Knowledge service resolves the manual relative to the repository root.
    copy(repo / "docs/agent-support-manual.md", backend / "docs/agent-support-manual.md")
    for item in ("Dockerfile", "package.json", "package-lock.json", "index.html", "tsconfig.json", "vite.config.ts", "src", "public"):
        copy(repo / "frontend" / item, frontend / item)
    # Do not inherit the tracked Zeabur URL. This context is for the new host.
    (frontend / ".env.production").write_text("VITE_API_BASE_URL=/api/v1\n", encoding="utf-8")
    return backend, frontend


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(Path(__file__).resolve().parents[2], args.output)
