import tempfile
import unittest
from pathlib import Path

from prepare_image_contexts import prepare


class ImageContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        files = ["Dockerfile", "start", "backend/app/main.py", "backend/migrations/env.py",
                 "backend/alembic.ini", "backend/requirements.txt", "docs/agent-support-manual.md"]
        files += ["frontend/" + name for name in ["Dockerfile", "package.json", "package-lock.json",
                  "index.html", "tsconfig.json", "vite.config.ts", "src/main.ts", "public/logo.png"]]
        for name in files:
            self.write(name, "test")

    def write(self, name, content):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_only_runtime_sources_and_same_origin_configuration(self):
        self.write("frontend/.env.production", "VITE_API_BASE_URL=https://old.invalid")
        self.write("backend/app/.env", "SECRET=secret")
        self.write("backend/app/data/test.db", "private")
        self.write("frontend/public/private.key", "private")
        self.write("frontend/src/node_modules/test.js", "unwanted")
        self.write(".git/config", "private")
        backend, frontend = prepare(self.repo, self.root / "contexts")
        self.assertTrue((backend / "docs/agent-support-manual.md").is_file())
        self.assertTrue((frontend / "public/logo.png").is_file())
        self.assertEqual((frontend / ".env.production").read_text(), "VITE_API_BASE_URL=/api/v1\n")
        for path in [backend / "backend/app/.env", backend / "backend/app/data/test.db",
                     frontend / "public/private.key", frontend / "src/node_modules", backend / ".git"]:
            self.assertFalse(path.exists(), path)
        self.assertIn("old.invalid", (self.repo / "frontend/.env.production").read_text())

    def test_existing_output_is_not_overwritten(self):
        output = self.root / "existing"
        output.mkdir()
        with self.assertRaises(FileExistsError):
            prepare(self.repo, output)

    def test_output_cannot_be_inside_repository(self):
        with self.assertRaises(ValueError):
            prepare(self.repo, self.repo / "generated")

    def test_actual_repository_context(self):
        repo = Path(__file__).resolve().parents[2]
        backend, frontend = prepare(repo, self.root / "actual-context")
        self.assertEqual((backend / "Dockerfile").read_bytes(), (repo / "Dockerfile").read_bytes())
        self.assertEqual((frontend / "Dockerfile").read_bytes(), (repo / "frontend/Dockerfile").read_bytes())
        self.assertTrue((backend / "backend/app/data/help_items.json").is_file())
        self.assertTrue((backend / "docs/agent-support-manual.md").is_file())
        self.assertNotIn("zeabur", (frontend / ".env.production").read_text())
        self.assertFalse((backend / "frontend").exists())


if __name__ == "__main__":
    unittest.main()
