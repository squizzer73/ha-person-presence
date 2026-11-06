"""Build an allowlisted install ZIP and standalone repository export."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]


def export_files(root):
    root = Path(root).resolve()
    names = json.loads((root / "release-files.json").read_text())
    if (
        not isinstance(names, list)
        or any(not isinstance(n, str) for n in names)
        or len(set(names)) != len(names)
    ):
        raise ValueError("Release file manifest must contain unique relative paths")
    paths = []
    for name in names:
        relative = Path(name)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or any(part == ".venv" or ".local" in part for part in relative.parts)
        ):
            raise ValueError("Unsafe path in release manifest")
        path = root / relative
        if (
            not path.is_file()
            or not path.resolve().is_relative_to(root)
            or any(
                parent.is_symlink()
                for parent in [path, *path.parents]
                if parent != root and root in parent.parents
            )
        ):
            raise ValueError("Missing file or symlink in release manifest: " + name)
        paths.append(path)
    return sorted(paths)


def build(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    version = json.loads(
        (ROOT / "custom_components/person_presence/manifest.json").read_text()
    )["version"]
    package = output / f"person-presence-{version}.zip"
    files = export_files(ROOT)
    with ZipFile(package, "w", ZIP_DEFLATED) as archive:
        for path in files:
            name = str(path.relative_to(ROOT))
            if not name.startswith("custom_components/"):
                continue
            item = ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            item.compress_type = ZIP_DEFLATED
            item.external_attr = 0o644 << 16
            archive.writestr(item, path.read_bytes())
    export = output / "repository"
    if export.exists():
        shutil.rmtree(export)
    for path in files:
        dest = export / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(path.read_bytes())
    checksum = hashlib.sha256(package.read_bytes()).hexdigest()
    (output / "SHA256SUMS").write_text(f"{checksum}  {package.name}\n")
    return {
        "package": str(package),
        "sha256": checksum,
        "export": str(export),
        "files": len(files),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    print(json.dumps(build(parser.parse_args().output)))
