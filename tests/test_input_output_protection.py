"""The Word output must never overwrite its JSON or image inputs."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from docx import Document
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / '技能/tiqu-extractor/scripts'
sys.path.insert(0, str(SCRIPTS))
import make_clean_doc


class InputOutputProtectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.source = self.base / '题目.json'
        self.image = self.base / '配图.png'
        Image.new('RGB', (40, 30), 'white').save(self.image)
        self.source.write_text(json.dumps({
            'title': '原稿保护测试',
            'blocks': [
                {'type': 'q', 'no': 1, 'text': '观察图形。'},
                {'type': 'image', 'path': self.image.name, 'width_cm': 5},
            ],
        }, ensure_ascii=False), encoding='utf-8')
        self.originals = {p: p.read_bytes() for p in (self.source, self.image)}

    def assert_inputs_unchanged(self):
        for path, original in self.originals.items():
            self.assertEqual(path.read_bytes(), original, str(path))

    def assert_collision_rejected(self, target=None):
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, '不能覆盖输入'):
                make_clean_doc.main(str(self.source), str(target) if target else None)
        self.assert_inputs_unchanged()

    def test_output_equal_to_json_is_rejected_by_cli(self):
        result = subprocess.run(
            [sys.executable, '-B', str(SCRIPTS / 'make_clean_doc.py'),
             str(self.source), str(self.source)],
            capture_output=True, encoding='utf-8',
            env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('不能覆盖输入', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assert_inputs_unchanged()

    def test_output_equal_to_source_image_is_rejected(self):
        self.assert_collision_rejected(self.image)

    def test_docx_symlink_to_json_is_rejected(self):
        alias = self.base / 'alias.docx'
        try:
            alias.symlink_to(self.source)
        except OSError as exc:
            self.skipTest('Symlinks unavailable: ' + str(exc))
        self.assert_collision_rejected(alias)

    def test_docx_hardlink_to_image_is_rejected(self):
        alias = self.base / 'alias.docx'
        try:
            os.link(self.image, alias)
        except OSError as exc:
            self.skipTest('Hardlinks unavailable: ' + str(exc))
        self.assert_collision_rejected(alias)

    def test_default_output_alias_to_input_is_rejected(self):
        try:
            os.link(self.source, self.source.with_suffix('.docx'))
        except OSError as exc:
            self.skipTest('Hardlinks unavailable: ' + str(exc))
        self.assert_collision_rejected()

    def test_normal_output_can_be_created_and_regenerated(self):
        target = self.source.with_suffix('.docx')
        for _ in range(2):
            with contextlib.redirect_stdout(io.StringIO()):
                make_clean_doc.main(str(self.source))
            document = Document(target)
            self.assertEqual(document.paragraphs[1].text, '1. 观察图形。')
            self.assertEqual(len(document.inline_shapes), 1)
            self.assert_inputs_unchanged()


if __name__ == '__main__':
    unittest.main()
