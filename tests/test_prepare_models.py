"""Exercise downloads and file preservation without GPU or large model downloads."""

import argparse
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare_models", ROOT / "tools/prepare_models.py")
models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class ModelPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = b"example model data\x00\xff"
        self.entry = {"path": "model.pth", "group": "character", "size": len(self.payload),
                      "sha256": hashlib.sha256(self.payload).hexdigest()}

    def serve(self):
        source = self.root / "source"
        source.mkdir()
        (source / "model.pth").write_bytes(self.payload)
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(source)))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return "http://127.0.0.1:%s/model.pth" % server.server_port

    def fixture(self):
        (self.root / "docs").mkdir()
        (self.root / "docs/models.json").write_text(json.dumps({"files": [self.entry]}))
        config_dir = self.root / "GPT_SoVITS/configs"
        config_dir.mkdir(parents=True)
        (config_dir / "tts_infer.example.yaml").write_text("custom: {}\n")
        model_path = self.root / "GPT_SoVITS/pretrained_models/model.pth"
        model_path.parent.mkdir()
        model_path.write_bytes(self.payload)
        return model_path, config_dir / "tts_infer.yaml"

    def args(self, check=False):
        return argparse.Namespace(root=self.root, check=check, with_base=False)

    def test_download_verifies_and_installs_file(self):
        url = self.serve()
        target = self.root / "destination/model.pth"
        models.download(url, target, self.entry)
        self.assertEqual(target.read_bytes(), self.payload)
        self.assertEqual(list(target.parent.glob("*.part")), [])

    def test_corrupt_download_preserves_existing_file_and_removes_partial(self):
        url = self.serve()
        target = self.root / "destination/model.pth"
        target.parent.mkdir()
        target.write_bytes(b"original")
        wrong = dict(self.entry, sha256="0" * 64)
        with patch.object(models.time, "sleep"), self.assertRaises(ValueError):
            models.download(url, target, wrong)
        self.assertEqual(target.read_bytes(), b"original")
        self.assertEqual(list(target.parent.glob("*.part")), [])

    def test_existing_config_is_preserved_and_missing_config_is_created(self):
        _, config = self.fixture()
        with patch.object(models, "ROOT", self.root):
            self.assertEqual(models.prepare(self.args()), 0)
            self.assertEqual(config.read_text(), "custom: {}\n")
            config.write_text("custom: {device: cpu}\n")
            self.assertEqual(models.prepare(self.args()), 0)
        self.assertEqual(config.read_text(), "custom: {device: cpu}\n")

    def test_check_does_not_create_config(self):
        _, config = self.fixture()
        with patch.object(models, "ROOT", self.root):
            self.assertEqual(models.prepare(self.args(check=True)), 1)
        self.assertFalse(config.exists())

    def test_mismatched_existing_model_is_not_overwritten(self):
        model, config = self.fixture()
        model.write_bytes(b"different local model")
        with patch.object(models, "ROOT", self.root), self.assertRaises(ValueError):
            models.prepare(self.args())
        self.assertEqual(model.read_bytes(), b"different local model")
        self.assertFalse(config.exists())


if __name__ == "__main__":
    unittest.main()
