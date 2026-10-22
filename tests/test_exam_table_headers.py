"""表头错位不能被当作有效考点统计；临时副本保留真实记录结构。"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_exam_evidence.py"
SUBJECTS = ("数学", "物理", "化学")


class ExamTableHeaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.originals = {
            subject: (ROOT / "真题考点/天津" / (subject + ".md")).read_text(encoding="utf-8")
            for subject in SUBJECTS}

    def write_sources(self, subject=None, year=2022, transform=None):
        for name, text in self.originals.items():
            if name == subject:
                heading = "### %d 年" % year
                before, section = text.split(heading, 1)
                end = re.search(r"^##(?:#)? ", section, re.M)
                text = before + heading + transform(section[:end.start()]) + section[end.start():]
            (self.directory / (name + ".md")).write_text(text, encoding="utf-8")

    def run_checker(self):
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), str(self.directory)],
            capture_output=True, encoding="utf-8", timeout=15,
            env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"))

    def assert_header_rejected(self):
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout[:500])
        self.assertEqual(result.stdout, "")
        self.assertIn("表头", json.loads(result.stderr)["错误"])

    def test_existing_tables_and_header_spacing_are_accepted(self):
        self.write_sources()
        baseline = self.run_checker()
        self.assertEqual(baseline.returncode, 0, baseline.stderr)
        self.write_sources("数学", transform=lambda section: re.sub(
            r"^\| 题号 .*$", lambda match: match[0].replace(" | ", "|"), section, flags=re.M))
        spaced = self.run_checker()
        self.assertEqual(spaced.returncode, 0, spaced.stderr)
        self.assertEqual(json.loads(spaced.stdout), json.loads(baseline.stdout))

    def test_swapped_topic_and_score_columns_cannot_produce_statistics(self):
        def swap_columns(section):
            def swap(match):
                fields = [part.strip() for part in re.split(r"(?<!\\)\|", match[0][1:-1])]
                fields[1], fields[3] = fields[3], fields[1]
                return "| " + " | ".join(fields) + " |"
            return re.sub(r"^\|.*\|$", swap, section, flags=re.M)
        self.write_sources("数学", transform=swap_columns)
        self.assert_header_rejected()

    def test_wrong_header_name_is_rejected_for_every_subject(self):
        for subject in SUBJECTS:
            with self.subTest(subject=subject):
                self.write_sources(subject, transform=lambda section: section.replace(
                    "候选分值", "错误分值标题", 1))
                self.assert_header_rejected()

    def test_each_year_requires_its_own_correct_header(self):
        self.write_sources("数学", year=2025, transform=lambda section: section.replace(
            "候选题型 | 候选分值", "候选分值 | 候选题型", 1))
        self.assert_header_rejected()

    def test_missing_header_is_rejected(self):
        self.write_sources("数学", transform=lambda section: re.sub(
            r"^\| 题号 .*\n", "", section, count=1, flags=re.M))
        self.assert_header_rejected()


if __name__ == "__main__":
    unittest.main()
