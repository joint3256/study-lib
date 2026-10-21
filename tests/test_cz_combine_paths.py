"""Portable path contract tests. Fixtures contain synthetic text, never textbooks."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "技能/cz-combine/scripts/check_library.py"
spec = importlib.util.spec_from_file_location("check_library", SCRIPT)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def put(path, content="synthetic fixture\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def library(root):
    put(root / "知识清单/_编写规范与模板.md")
    for subject in check.SUBJECTS:
        books = (("八年级上册", "八年级下册", "九年级全一册") if subject == "物理"
                 else ("九年级上册", "九年级下册") if subject == "化学"
                 else tuple(g + t for g in ("七年级", "八年级", "九年级")
                            for t in ("上册", "下册")))
        for book in books:
            put(root / "知识清单/初中" / subject / (book + ".md"))
        methods = root / "方法套路" / ("初中数学" if subject == "数学" else subject + "/初中")
        put(methods / "01_测试方法.md")
        if subject not in ("数学", "物理", "化学"):
            put(methods / ("讲法话术_" + subject + ".md"))
    put(root / "方法套路/讲法话术.md")
    put(root / "方法套路/讲法话术_化学英语.md")
    return root


class PathContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = library(self.base / "设备 中文 空格 (副本)" / "任意库名")
        self.skill = self.base / "独立技能/cz-combine"
        self.skill.mkdir(parents=True)
        self.cwd = self.base / "工作目录"
        self.cwd.mkdir()

    def run_check(self, *args, env=None, skill=None, cwd=None):
        return check.run_checks(check.parser().parse_args(args),
                                skill or self.skill, cwd or self.cwd, env or {})

    def configured(self, *args):
        return self.run_check("--lib-root", str(self.root), *args)

    def test_explicit_unicode_space_root_and_missing_optional_textbooks(self):
        report = self.configured()
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["lib_root"], str(self.root))
        self.assertIn(str(self.root.parent / "教材库"), report["warnings"][0])
        self.assertIsNone(report["textbook_root"])
        self.assertIn("未检索", report["citation_status"])

    def test_env_supports_copied_skill(self):
        report = self.run_check(env={"CZ_COMBINE_LIB_ROOT": str(self.root)})
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["lib_source"], "CZ_COMBINE_LIB_ROOT")

    def test_cli_overrides_env(self):
        report = self.run_check("--lib-root", str(self.root),
                                env={"CZ_COMBINE_LIB_ROOT": str(self.base / "missing")})
        self.assertTrue(report["ok"], report)

    def test_bad_explicit_root_never_falls_back(self):
        for value in (str(self.base / "missing"), "", "relative", "C:relative"):
            with self.subTest(value=value):
                report = self.run_check(env={"CZ_COMBINE_LIB_ROOT": value}, cwd=self.root)
                self.assertFalse(report["ok"])
                self.assertIsNone(report["lib_root"])
                self.assertTrue(report["errors"])

    def test_skill_in_repo_detected_independent_of_cwd(self):
        report = self.run_check(skill=self.root / "技能/cz-combine")
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["lib_root"], str(self.root))

    def test_nested_workdir_detected(self):
        report = self.run_check(cwd=self.root / "知识清单/初中/物理")
        self.assertTrue(report["ok"], report)

    def test_named_neighbor_discovery(self):
        for name in ("study-lib", "学习资料库"):
            with self.subTest(name=name):
                parent = self.base / name
                target = library(parent / name)
                report = self.run_check(cwd=parent / "work/deep")
                self.assertTrue(report["ok"], report)
                self.assertEqual(report["lib_root"], str(target))

    def test_two_clones_require_selection(self):
        other = library(self.base / "another")
        report = self.run_check(skill=self.root / "技能/cz-combine", cwd=other)
        self.assertFalse(report["ok"])
        self.assertIn(str(self.root), report["errors"][0])
        self.assertIn(str(other), report["errors"][0])

    def test_same_clone_from_both_anchors_not_ambiguous(self):
        report = self.run_check(skill=self.root / "技能/cz-combine", cwd=self.root)
        self.assertTrue(report["ok"], report)

    def test_no_discovery_reports_checked_locations(self):
        report = self.run_check()
        self.assertFalse(report["ok"])
        self.assertIn(str(self.skill), report["errors"][0])
        self.assertIn(str(self.cwd / "study-lib"), report["errors"][0])

    def test_directory_name_alone_is_not_a_library(self):
        fake = self.cwd / "study-lib"
        fake.mkdir()
        report = self.run_check()
        self.assertFalse(report["ok"])
        self.assertIn(str(fake), report["errors"][0])

    def test_marker_required_and_empty_marker_rejected(self):
        marker = self.root / "知识清单/_编写规范与模板.md"
        for exists in (True, False):
            with self.subTest(exists=exists):
                marker.write_text("") if exists else marker.unlink()
                report = self.configured()
                self.assertFalse(report["ok"])
                self.assertIn(str(marker), report["errors"][0])

    def test_missing_book_reports_exact_path(self):
        missing = self.root / "知识清单/初中/化学/九年级下册.md"
        missing.unlink()
        report = self.configured()
        self.assertFalse(report["ok"])
        self.assertIn(str(missing), "\n".join(report["errors"]))
        self.assertTrue(self.configured("--subject", "数学")["ok"])

    def test_empty_method_directory_fails(self):
        (self.root / "方法套路/初中数学/01_测试方法.md").unlink()
        report = self.configured("--subject", "数学")
        self.assertFalse(report["ok"])
        self.assertIn("初中数学", "\n".join(report["errors"]))

    def test_exact_required_file_and_empty_file(self):
        rel = "方法套路/初中数学/不存在.md"
        report = self.configured("--require", rel)
        self.assertFalse(report["ok"])
        self.assertIn(str(self.root / rel), "\n".join(report["errors"]))
        put(self.root / rel, "")
        self.assertFalse(self.configured("--require", rel)["ok"])
        put(self.root / rel)
        self.assertTrue(self.configured("--require", rel)["ok"])

    def test_relative_resource_both_separators(self):
        report = self.configured("--require", "知识清单\\初中\\数学\\七年级上册.md")
        self.assertTrue(report["ok"], report)

    def test_absolute_and_escaping_resources_rejected(self):
        for rel in ("../outside.md", "/tmp/a", "C:\\a.md", "C:a", "\\\\host\\share\\a"):
            with self.subTest(rel=rel):
                self.assertFalse(self.configured("--require", rel)["ok"])

    def test_sibling_textbooks_and_required_file(self):
        books = self.root.parent / "教材库"
        rel = "初中数学/人教版/人教版数学七年级上册.docx"
        self.assertFalse(self.configured("--textbook", rel)["ok"])
        put(books / rel)  # Path/readability fixture, not a real DOCX.
        report = self.configured("--textbook", rel)
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["textbook_root"], str(books))
        self.assertIn("未检索", report["citation_status"])

    def test_configured_textbooks_override_sibling_and_bad_config_fails(self):
        (self.root.parent / "教材库").mkdir()
        books = self.base / "本地教 材"
        books.mkdir()
        report = self.run_check("--lib-root", str(self.root),
                                env={"CZ_COMBINE_TEXTBOOK_ROOT": str(books)})
        self.assertEqual(report["textbook_root"], str(books))
        report = self.configured("--textbook-root", str(self.base / "missing"))
        self.assertFalse(report["ok"])
        self.assertIsNone(report["textbook_root"])
        report = self.run_check("--lib-root", str(self.root), "--textbook-root", str(books),
                                env={"CZ_COMBINE_TEXTBOOK_ROOT": "invalid"})
        self.assertTrue(report["ok"], report)

    def test_unreadable_file_reports_path(self):
        target = self.root / "知识清单/初中/数学/七年级上册.md"
        original = Path.open

        def deny(path, *args, **kwargs):
            if path == target:
                raise PermissionError("simulated unreadable file")
            return original(path, *args, **kwargs)

        with patch.object(Path, "open", deny):
            report = self.configured()
        self.assertFalse(report["ok"])
        self.assertIn(str(target), "\n".join(report["errors"]))

    def test_special_file_is_not_read(self):
        target = self.base / "not-a-file"
        target.mkdir()
        with patch.object(Path, "open", side_effect=AssertionError("must not open non-files")):
            self.assertIn(str(target), check.readable_file(target))
        if hasattr(os, "mkfifo"):
            fifo = self.base / "pipe"
            os.mkfifo(fifo)
            with patch.object(Path, "open", side_effect=AssertionError("must not open FIFO")):
                self.assertIn(str(fifo), check.readable_file(fifo))

    def test_no_writes_or_network_needed(self):
        def snapshot():
            return {str(p): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                    for p in self.base.rglob("*") if p.is_file()}
        before = snapshot()
        with patch("socket.socket", side_effect=AssertionError("network forbidden")):
            self.assertTrue(self.configured()["ok"])
        self.assertEqual(before, snapshot())

    def test_copied_cli_exit_codes_and_json(self):
        copied = self.skill / "scripts/check_library.py"
        copied.parent.mkdir()
        shutil.copyfile(SCRIPT, copied)
        env = {k: v for k, v in os.environ.items() if not k.startswith("CZ_COMBINE_")}
        for root, code in ((self.root, 0), (self.base / "missing", 1)):
            result = subprocess.run([sys.executable, "-B", str(copied), "--lib-root", str(root)],
                                    cwd=self.cwd, env=env, capture_output=True, check=False)
            self.assertEqual(result.returncode, code, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["ok"], code == 0)
            self.assertIn("未检索", report["citation_status"])

    def test_native_absolute_paths_and_foreign_paths(self):
        self.assertEqual(check.configured_path(str(self.root)), self.root)
        if os.name != "nt":
            for value in ("D:\\学习资料\\study-lib", "\\\\server\\share\\study-lib"):
                with self.assertRaises(ValueError):
                    check.configured_path(value)
        else:
            with self.assertRaises(ValueError):
                check.configured_path("/home/user/study-lib")

    def test_symlink_deduplication(self):
        alias = self.base / "linked"
        try:
            alias.symlink_to(self.root, target_is_directory=True)
        except OSError as exc:
            self.skipTest("OS does not permit symlink creation: " + str(exc))
        report = self.run_check(skill=alias / "技能/cz-combine", cwd=self.root)
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["lib_root"], str(self.root))


class RepositoryRegressionTests(unittest.TestCase):
    def test_checkout_all_six_subjects(self):
        args = check.parser().parse_args(["--lib-root", str(REPO)])
        report = check.run_checks(args, environ={})
        self.assertTrue(report["ok"], report)

    def test_skill_has_no_old_workspace_dependency(self):
        for path in (REPO / "技能/cz-combine").rglob("*.md"):
            with self.subTest(path=path):
                self.assertNotRegex(path.read_text(encoding="utf-8"), r"/home/[^\s`]*Doubao/chats/")


if __name__ == "__main__":
    unittest.main()
