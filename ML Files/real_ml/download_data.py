"""Download the immutable NRC dataset snapshot; never import simulated data."""
import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import time
from urllib.parse import quote
from urllib.request import Request, urlopen

REPOSITORY = "nrc-cnrc/CUAS-sensing-dataset"
REVISION = "df3cebae895f4f12d23cd50480dd4c47b09d422e"
DEFAULT_RAW = Path(__file__).resolve().parent / "data" / "raw"


def git_blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def safe_path(root, name):
    if PureWindowsPath(name).anchor:
        raise ValueError(f"Unsafe upstream path: {name}")
    target = (root / name).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"Unsafe upstream path: {name}")
    return target


def fetch(url):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": "RTX-Ignite-data-validation"}), timeout=120) as response:
                return response.read()
        except OSError:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def download(raw_dir=DEFAULT_RAW):
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = raw_dir / "download_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["revision"] != REVISION or manifest["repository"] != REPOSITORY:
            raise ValueError("Download manifest belongs to another dataset revision")
        entries = manifest["files"]
    else:
        tree = json.loads(fetch(f"https://api.github.com/repos/{REPOSITORY}/git/trees/{REVISION}?recursive=1"))
        if tree.get("truncated"):
            raise ValueError("Incomplete upstream file tree")
        entries = [{"path": e["path"], "sha": e["sha"], "size": e["size"]}
                   for e in tree["tree"] if e["type"] == "blob" and
                   (e["path"].startswith(("data/", "metadata/", "docs/")) or
                    e["path"] in {"README.md", "LICENSE", "CITATION.cff"})]
    for entry in entries:
        target = safe_path(raw_dir, entry["path"])
        if target.exists() and git_blob_sha(target.read_bytes()) == entry["sha"]:
            continue
        url = f"https://raw.githubusercontent.com/{REPOSITORY}/{REVISION}/{quote(entry['path'])}"
        data = fetch(url)
        if len(data) != entry["size"] or git_blob_sha(data) != entry["sha"]:
            raise ValueError(f"Integrity mismatch: {entry['path']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".part")
        temporary.write_bytes(data)
        temporary.replace(target)
        print(f"Downloaded {entry['path']}", flush=True)
    manifest = {"repository": REPOSITORY, "revision": REVISION, "license": "CC-BY-4.0",
                "attribution": "Mehta, Bolic, Mantegh and Vidal; National Research Council Canada / University of Ottawa",
                "files": entries}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(entries)} files at {REVISION}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    download(parser.parse_args().raw_dir)
