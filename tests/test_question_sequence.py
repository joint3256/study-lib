"""题号检查的行为回归；仅使用临时合成试卷。"""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "技能/tiqu-extractor/scripts"
sys.path.insert(0, str(SCRIPTS))
import verify_extract


class QuestionSequenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "试卷.json"

    def save(self, numbers):
        data = {"title": "合成试卷", "blocks": [
            {"type": "q", "no": number, "text": "计算。"} for number in numbers]}
        self.source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def check(self, numbers):
        self.save(numbers)
        before = self.source.read_bytes()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = verify_extract.main(str(self.source))
        self.assertEqual(self.source.read_bytes(), before)
        return code, output.getvalue()

    def test_ordered_complete_questions_need_no_sequence_warning(self):
        code, report = self.check([1, "2.", 3])
        self.assertEqual(code, 0)
        self.assertIn("【CHECK 疑似（必须调出原照片逐处确认并记录）】共 0 处", report)

    def test_descending_order_is_a_check_and_preserves_input(self):
        code, report = self.check([2, 1])
        self.assertEqual(code, 0)  # CHECK 仍由人工对照原卷，不能改成 ERR。
        self.assertIn("题号顺序异常", report)
        self.assertIn("2→1", report)
        self.assertIn("【CHECK 疑似（必须调出原照片逐处确认并记录）】共 1 处", report)
        self.assertIn("【ERR 确定错误（必须修改）】共 0 处", report)
        self.assertEqual([b["no"] for b in json.loads(self.source.read_text(encoding="utf-8"))["blocks"]], [2, 1])

    def test_gaps_are_reported_as_intervals_with_exact_count(self):
        code, report = self.check([1, 3, 6])
        self.assertEqual(code, 0)
        self.assertIn("题号序列缺少 2、4–5，共 3 个", report)
        self.assertNotIn("题号顺序异常", report)

    def test_many_gaps_have_bounded_preview_and_full_count(self):
        code, report = self.check(list(range(2, 202, 2)))
        self.assertEqual(code, 0)
        self.assertIn("仅展示前8段", report)
        self.assertIn("共 100 个", report)
        self.assertLess(len(report), 1500)

    def test_gap_and_order_checks_are_independent(self):
        code, report = self.check([3, 1])
        self.assertEqual(code, 0)
        self.assertIn("题号序列缺少 2，共 1 个", report)
        self.assertIn("题号顺序异常", report)
        self.assertIn("【CHECK 疑似（必须调出原照片逐处确认并记录）】共 2 处", report)

    def test_large_question_number_uses_bounded_resources(self):
        self.save([20261022])
        before = self.source.read_bytes()
        # Linux/macOS 用独立进程内存上限复现旧版 MemoryError；不支持
        # RLIMIT_AS 的系统限制旧版的大范围枚举，避免 Windows CI 耗尽内存。
        worker = r'''
import builtins
import runpy
import sys

limited = False
try:
    import resource
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    limit = 256 * 1024 * 1024
    if hard != resource.RLIM_INFINITY:
        limit = min(limit, hard)
    resource.setrlimit(resource.RLIMIT_AS, (limit, hard))
    limited = True
except (ImportError, AttributeError, OSError, ValueError):
    pass

def bounded_range(*args):
    result = builtins.range(*args)
    if len(result) > 100000:
        raise MemoryError("题号检查不得枚举巨大的缺号区间")
    return result

script, source = sys.argv[1:]
sys.path.insert(0, str(__import__('pathlib').Path(script).parent))
sys.argv = [script, source]
runpy.run_path(script, run_name="__main__",
               init_globals={} if limited else {"range": bounded_range})
'''
        result = subprocess.run(
            [sys.executable, "-B", "-c", worker,
             str(SCRIPTS / "verify_extract.py"), str(self.source)],
            capture_output=True, encoding="utf-8", timeout=15,
            env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("题号序列缺少 1–20261021，共 20261021 个", result.stdout)
        self.assertLess(len(result.stdout), 1500)
        self.assertEqual(self.source.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
