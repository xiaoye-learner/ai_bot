"""Download and verify the published character models (Python 3.9+, stdlib only)."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verified(path, entry):
    return (path.is_file() and path.stat().st_size == entry["size"]
            and sha256(path) == entry["sha256"])


def download(url, target, entry):
    target.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".part", delete=False) as out:
                temporary = Path(out.name)
                with urlopen(url, timeout=60) as response:
                    shutil.copyfileobj(response, out, length=1024 * 1024)
            if not verified(temporary, entry):
                raise ValueError("Downloaded file failed size/SHA-256 verification: " + entry["path"])
            os.replace(temporary, target)
            return
        except (OSError, ValueError, URLError):
            if attempt == 2:
                raise
            time.sleep(2)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def prepare(args):
    manifest = json.loads((ROOT / "docs/models.json").read_text(encoding="utf-8"))
    model_root = args.root / "GPT_SoVITS/pretrained_models"
    missing = []
    for entry in manifest["files"]:
        target = model_root / entry["path"]
        if target.exists():
            if not verified(target, entry):
                raise ValueError("Existing file differs from the published model; left unchanged: " + str(target))
            print("OK " + entry["path"], flush=True)
            continue
        if args.check or (entry["group"] == "base" and not args.with_base):
            missing.append(entry["path"])
            continue
        name = quote(entry["path"], safe="/")
        if entry["group"] == "character":
            url = ("https://github.com/" + manifest["repository"] + "/releases/download/"
                   + manifest["release"] + "/" + name)
        else:
            url = (args.hf_endpoint.rstrip("/") + "/" + manifest["base_repository"]
                   + "/resolve/" + manifest["base_revision"] + "/" + name)
        print("Downloading " + entry["path"], flush=True)
        download(url, target, entry)
        print("OK " + entry["path"], flush=True)

    config = args.root / "GPT_SoVITS/configs/tts_infer.yaml"
    if args.check:
        if not config.is_file():
            missing.append("GPT_SoVITS/configs/tts_infer.yaml")
    elif not config.exists():
        config.parent.mkdir(parents=True, exist_ok=True)
        with config.open("x", encoding="utf-8") as stream:
            stream.write((ROOT / "GPT_SoVITS/configs/tts_infer.example.yaml").read_text(encoding="utf-8"))
        print("Created " + str(config), flush=True)
    else:
        print("Kept existing config: " + str(config), flush=True)
    if missing:
        print("Missing files:\n  " + "\n  ".join(missing), file=sys.stderr)
        print("Run with --with-base to download all required model files.", file=sys.stderr)
        return 1
    print("Required model files are verified. Config: " + str(config), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-base", action="store_true", help="also download the required upstream base models")
    parser.add_argument("--check", action="store_true", help="verify all required models and config without writing files")
    parser.add_argument("--root", type=Path, default=ROOT, help="target project directory (default: this repository)")
    parser.add_argument("--hf-endpoint", default="https://huggingface.co", help="Hugging Face endpoint or compatible mirror")
    args = parser.parse_args()
    try:
        return prepare(args)
    except (OSError, ValueError, URLError) as exc:
        print("Error: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
