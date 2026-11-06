import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).parents[1]


class Release(unittest.TestCase):
    def test_archive_is_deterministic_and_export_excludes_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            for _ in range(2):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "scripts/build_release.py"),
                        "--output",
                        directory,
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                zip_path = next(Path(directory).glob("person-presence-*.zip"))
                checksum = hashlib.sha256(zip_path.read_bytes()).hexdigest()
                if _ == 0:
                    first = checksum
                else:
                    self.assertEqual(checksum, first)
            with ZipFile(zip_path) as archive:
                names = archive.namelist()
                self.assertIn("custom_components/person_presence/whereabouts.py", names)
                self.assertNotIn("README.md", names)
                self.assertFalse(
                    any(
                        ".local" in n or ".venv" in n or "__pycache__" in n
                        for n in names
                    )
                )
                manifest = json.loads(
                    archive.read("custom_components/person_presence/manifest.json")
                )
                self.assertEqual(manifest["version"], "0.2.0b1")
                for name in names:
                    self.assertEqual(archive.read(name), (ROOT / name).read_bytes())
            export = Path(directory) / "repository"
            self.assertTrue((export / "README.md").exists())
            self.assertTrue((export / "hacs.json").exists())
            self.assertFalse((export / "dist").exists())
            self.assertFalse((export / ".venv").exists())
            expected = set(json.loads((ROOT / "release-files.json").read_text()))
            actual = {
                str(p.relative_to(export)) for p in export.rglob("*") if p.is_file()
            }
            self.assertEqual(actual, expected)
            for name in expected:
                self.assertEqual(
                    (export / name).read_bytes(), (ROOT / name).read_bytes()
                )

    def test_top_level_escaped_symlink_is_rejected(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "release_builder", ROOT / "scripts/build_release.py"
        )
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with (
            tempfile.TemporaryDirectory() as directory,
            tempfile.TemporaryDirectory() as outside,
        ):
            root = Path(directory).resolve()
            secret = Path(outside) / "secret.txt"
            secret.write_text("PRIVATE_CANARY")
            (root / "README.md").symlink_to(secret)
            (root / "release-files.json").write_text(json.dumps(["README.md"]))
            with self.assertRaises(ValueError):
                builder.export_files(root)

    def test_unlisted_file_in_otherwise_allowed_directory_is_excluded(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "release_builder", ROOT / "scripts/build_release.py"
        )
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "tests").mkdir()
            (root / "tests/debug_snapshot.json").write_text(
                '{"private":"PRIVATE_CANARY"}'
            )
            (root / "README.md").write_text("Public")
            (root / "release-files.json").write_text(json.dumps(["README.md"]))
            self.assertEqual(
                [str(p.relative_to(root)) for p in builder.export_files(root)],
                ["README.md"],
            )
