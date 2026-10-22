#!/usr/bin/env python3
"""只读检查天津图谱逐题证据；待核实记录永不进入已核实计数。

用法：python scripts/check_exam_evidence.py [图谱目录]
字段校验无法代替实际阅读原卷；全部通过也不证明题面与归类正确。
"""
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

SUBJECTS = ('数学', '物理', '化学')
YEARS = tuple(range(2022, 2027))
STATUSES = ('已核实', '待核实', '推断待核实')
SOURCE_TYPES = ('官方原卷', '第三方原卷转载', '第三方解析版')
RECORD_HEADERS = ('题号', '候选考点或原记录', '候选题型', '候选分值',
                  '难度估计', '核验状态', '题面及答案证据')


def read_records(directory):
    records = []
    for subject in SUBJECTS:
        path = Path(directory) / (subject + '.md')
        text = path.read_text(encoding='utf-8')
        match = re.search(r'^## 四、逐题对照明细\s*\n(.*?)^## 五、', text, re.M | re.S)
        if not match:
            raise ValueError('%s 缺少逐题对照明细' % path)
        year = None
        year_counts = Counter()
        has_header = False
        for number, raw_line in enumerate(match[1].splitlines(), 1):
            line = raw_line.strip()
            if not line or line == '---':
                continue
            if line.startswith('#'):
                heading = re.fullmatch(r'###\s+(\d{4})\s*年', line)
                if not heading or int(heading[1]) not in YEARS:
                    raise ValueError('%s 未识别的年份标题：%s' % (path, line))
                year = int(heading[1])
                if year in year_counts:
                    raise ValueError('%s 重复年份：%s' % (path, year))
                year_counts[year] = 0
                has_header = False
                continue
            if year is None and not line.startswith('|'):
                continue  # 明细前的说明文字，不包含数据表。
            if not (line.startswith('|') and line.endswith('|')):
                raise ValueError('%s 明细第%d行不是完整表格行：%s' % (path, number, line))
            fields = [x.strip() for x in re.split(r'(?<!\\)\|', line[1:-1])]
            if len(fields) != 7 or year is None:
                raise ValueError('%s 逐题行缺少年份或核验字段：%s' % (path, line))
            if fields[0] == '题号':
                if has_header or year_counts[year]:
                    raise ValueError('%s 重复表头：%s' % (path, year))
                if tuple(fields) != RECORD_HEADERS:
                    raise ValueError('%s %s 年表头名称或顺序错误：应为 %s，实际为 %s'
                                     % (path, year, RECORD_HEADERS, tuple(fields)))
                has_header = True
                continue
            if all(re.fullmatch(r':?-{3,}:?', field) for field in fields):
                if not has_header:
                    raise ValueError('%s 表格分隔线前缺少表头' % path)
                continue
            if not has_header or not re.fullmatch(r'[1-9]\d*', fields[0]):
                raise ValueError('%s 非法题号或缺少表头：%s' % (path, line))
            if any(not field for field in fields):
                raise ValueError('%s 明细存在空字段：%s' % (path, line))
            records.append(dict(subject=subject, year=year, question=int(fields[0]),
                                topic=fields[1], question_type=fields[2], score=fields[3],
                                status=fields[5], evidence=fields[6]))
            year_counts[year] += 1
        missing = [year for year in YEARS if not year_counts[year]]
        if missing:
            raise ValueError('%s 缺少候选记录年份：%s' % (path, missing))
    return records


def validate_evidence(record):
    """要求题面、答案各有 URL、页/图号及本题题号；不尝试联网判真。"""
    key = (record['subject'], record['year'], record['question'])
    parts = [part.strip() for part in record['evidence'].split('；')]
    fields = {}
    for part in parts:
        match = re.fullmatch(r'(题面|答案|来源|核验)\s*[:：]?\s+(.+)', part)
        if not match or match[1] in fields:
            raise ValueError('证据须分别填写题面、答案、来源、核验（用中文分号分隔）：%s' % (key,))
        fields[match[1]] = match[2]
    if set(fields) != {'题面', '答案', '来源', '核验'}:
        raise ValueError('证据缺少题面、答案、来源或核验：%s' % (key,))
    for role in ('题面', '答案'):
        match = re.fullmatch(r'(https?://\S+)\s+第([1-9]\d*)(?:-([1-9]\d*))?(页|图)\s+第([1-9]\d*)题', fields[role])
        if not match:
            raise ValueError('%s缺少独立 URL、正数页码/图号或题号：%s' % (role, key))
        url = urlsplit(match[1])
        if not url.hostname or url.username or url.password:
            raise ValueError('%s URL 无效：%s' % (role, key))
        if match[3] and int(match[3]) < int(match[2]):
            raise ValueError('%s页码/图号范围倒置：%s' % (role, key))
        if int(match[5]) != record['question']:
            raise ValueError('%s定位的题号与记录不符：%s' % (role, key))
    if fields['来源'] not in SOURCE_TYPES:
        raise ValueError('必须区分官方原卷、第三方原卷转载与第三方解析版：%s' % (key,))
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', fields['核验']):
        raise ValueError('核验日期须为 YYYY-MM-DD：%s' % (key,))
    checked = date.fromisoformat(fields['核验'])
    if checked > date.today() or checked.year < record['year']:
        raise ValueError('核验日期在未来或早于考试年份：%s' % (key,))
    return fields['来源']


def summarize(records):
    if not records:
        raise ValueError('没有候选记录')
    counts = Counter()
    seen = set()
    verified_years = defaultdict(set)
    verified_questions = Counter()
    source_counts = Counter()
    coverage = defaultdict(Counter)
    for record in records:
        key = (record['subject'], record['year'], record['question'])
        if (record['subject'] not in SUBJECTS or type(record['year']) is not int
                or record['year'] not in YEARS or type(record['question']) is not int
                or record['question'] < 1):
            raise ValueError('非法学科、年份或题号：%s' % (key,))
        if key in seen:
            raise ValueError('重复记录：%s' % (key,))
        seen.add(key)
        status = record['status']
        if status not in STATUSES:
            raise ValueError('未知核验状态：%s %s' % (key, status))
        counts[status] += 1
        coverage[key[:2]][status] += 1
        if status != '已核实':
            continue
        topic = record['topic']
        if not topic.strip() or any(word in topic for word in ('待核实', '反推', '推断')):
            raise ValueError('推断或空考点不能标为已核实：%s' % (key,))
        source_counts[validate_evidence(record)] += 1
        topic_key = (record['subject'], topic)
        verified_years[topic_key].add(record['year'])
        verified_questions[topic_key] += 1
    return {
        '候选记录总数': len(records),
        '已核实记录': counts['已核实'],
        '待核实记录': counts['待核实'] + counts['推断待核实'],
        '其中原推断记录': counts['推断待核实'],
        '已核实来源类型': dict(sorted(source_counts.items())),
        '候选记录核验进度': [
            {'学科': subject, '年份': year, '候选记录': sum(c.values()),
             '已核实': c['已核实'], '待核实': c['待核实'] + c['推断待核实']}
            for (subject, year), c in sorted(coverage.items())],
        '已核实记录内计数': [
            {'学科': subject, '考点': topic, '出现年份数': len(years),
             '题目次数': verified_questions[(subject, topic)]}
            for (subject, topic), years in sorted(verified_years.items())],
        '说明': '字段检查不核验网页内容或来源真实性。计数按考点原文分组，尚非统一考点频率；'
                '进度分母仅为现有候选记录，不证明原卷完整。待核实不是未出现。'
                '不得据部分证据发布五年频率、必考排序或年均分值。'
    }


def main():
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / '真题考点/天津'
    try:
        # JSON 转义可在 Windows 非 UTF-8 控制台中无损传输中文字段与内容。
        print(json.dumps(summarize(read_records(directory)), ensure_ascii=True, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'错误': '证据检查失败：%s' % exc}, ensure_ascii=True), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
