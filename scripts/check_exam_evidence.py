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

SUBJECTS = ('数学', '物理', '化学')
STATUSES = ('已核实', '待核实', '推断待核实')


def read_records(directory):
    records = []
    for subject in SUBJECTS:
        path = Path(directory) / (subject + '.md')
        text = path.read_text(encoding='utf-8')
        match = re.search(r'^## 四、逐题对照明细\s*\n(.*?)^## 五、', text, re.M | re.S)
        if not match:
            raise ValueError('%s 缺少逐题对照明细' % path)
        year = None
        count = 0
        for line in match[1].splitlines():
            heading = re.match(r'### (202[2-6]) 年$', line)
            if heading:
                year = int(heading[1])
            if re.match(r'^\| \d+ \|', line):
                fields = [x.strip() for x in re.split(r'(?<!\\)\|', line.strip().strip('|'))]
                if len(fields) != 7 or year is None:
                    raise ValueError('%s 逐题行缺少年份或核验字段：%s' % (path, line))
                records.append(dict(subject=subject, year=year, question=int(fields[0]),
                                    topic=fields[1], status=fields[5], evidence=fields[6]))
                count += 1
        if not count:
            raise ValueError('%s 没有逐题记录' % path)
    return records


def summarize(records):
    counts = Counter()
    seen = set()
    verified_years = defaultdict(set)
    verified_questions = Counter()
    for record in records:
        key = (record['subject'], record['year'], record['question'])
        if key in seen:
            raise ValueError('重复记录：%s' % (key,))
        seen.add(key)
        status = record['status']
        if status not in STATUSES:
            raise ValueError('未知核验状态：%s %s' % (key, status))
        counts[status] += 1
        if status != '已核实':
            continue
        topic = record['topic']
        evidence = record['evidence']
        if not topic or any(word in topic for word in ('待核实', '反推', '推断')):
            raise ValueError('推断或空考点不能标为已核实：%s' % (key,))
        if not re.search(r'https?://\S+', evidence) or not re.search(r'(第?\d+页|p\.\s*\d+|图\s*\d+)', evidence):
            raise ValueError('已核实记录缺少来源 URL 或页码/图号：%s' % (key,))
        if '题面' not in evidence or '答案' not in evidence:
            raise ValueError('已核实记录须分别给出题面与答案的定位：%s' % (key,))
        dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', evidence)
        if not dates:
            raise ValueError('已核实记录缺少核验日期：%s' % (key,))
        for value in dates:
            date.fromisoformat(value)
        topic_key = (record['subject'], topic)
        verified_years[topic_key].add(record['year'])
        verified_questions[topic_key] += 1
    return {
        '候选记录总数': len(records),
        '已核实记录': counts['已核实'],
        '待核实记录': counts['待核实'] + counts['推断待核实'],
        '其中原推断记录': counts['推断待核实'],
        '已核实记录内计数': [
            {'学科': subject, '考点': topic, '出现年份数': len(years),
             '题目次数': verified_questions[(subject, topic)]}
            for (subject, topic), years in sorted(verified_years.items())],
        '说明': '计数仅覆盖已核实记录；待核实不是未出现。不得据部分证据发布五年频率、必考排序或年均分值。'
    }


def main():
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / '真题考点/天津'
    try:
        # JSON 转义可在 Windows 非 UTF-8 控制台中无损传输中文字段与内容。
        print(json.dumps(summarize(read_records(directory)), ensure_ascii=True, indent=2))
    except (OSError, ValueError, KeyError) as exc:
        sys.exit('证据检查失败：%s' % exc)


if __name__ == '__main__':
    main()
