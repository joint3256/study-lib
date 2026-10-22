# 公开来源与适配范围

核对日期：2026-10-21；2026-10-22 补充两项评估。以下只列实际审阅的公开实现；没有据此声称遍历了所有仓库或找到全局最优。截图中的排名、Star 和下载量不作为采用依据。

| 来源（固定版本） | 适合之处 | 本任务的限制与取舍 |
|---|---|---|
| [obra/superpowers: verification-before-completion](https://github.com/obra/superpowers/blob/b739a8af570e10a95898f2bdf6cec97467fa6c12/skills/verification-before-completion/SKILL.md) | 声称完成前先明确检验、执行、读取结果；区分测试通过与需求满足 | 采用并改写为“结论与证据对应”流程。原文要求在同一条消息里运行命令，可能导致无关重复运行；“局部检查什么也不能证明”过于绝对；没有给出题目来源分级、版本冲突或安全隔离复现的领域规则。 |
| [openai/skills: gh-fix-ci](https://github.com/openai/skills/blob/49f948faa9258a0c61caceaf225e179651397431/skills/.curated/gh-fix-ci/SKILL.md) | 聚焦 GitHub Actions 日志与失败检查 | 未复制或安装。它依赖 gh CLI 认证，不覆盖教材与真题证据；此环境已有可用 GitHub 连接器，不能把 CLI 无凭据误判成连接器未授权。 |
| [anthropics/skills: skill-creator](https://github.com/anthropics/skills/blob/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/skill-creator/SKILL.md) | 提供真实任务试用、对照及迭代方法 | 未复制或安装。面向 Claude 的部分评估路径、CLI 和交互不能直接搬到此环境；本次使用已有系统 skill-creator 并做独立只读试用，不声称有速度或准确率提升的对照实验结论。 |
| [mattpocock/skills: diagnosing-bugs](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/diagnosing-bugs/SKILL.md) 与 [tdd](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/tdd/SKILL.md) | 修好最小用例后复跑原始场景；测试预期值来自独立依据 | 仅适配这两条验证原则，无新增运行依赖。不照搬每次测试前必须确认、固定假设数量或高次数压力测试。其 scripts/link-skills.sh 是维护者脚本且会删除同名非链接目录，不执行。 |
| [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design/blob/7a12007b5a4246894f342a2e52e78facbc62eca3/skills/diagram-design/SKILL.md) | 提供 HTML/SVG 技术示意图的布局与导入检查 | 未复制或安装；当前核验无需新增绘图依赖。PNG 导出另需 Playwright/Chromium。不能将舍弃原坐标的重绘规则套用到原卷电路、几何或实验装置图，空间关系可能就是题意。 |

这是对本资料库任务的适配判断，不是对上述项目整体质量的评级。未安装其 hooks、运行外部脚本或更改他人的仓库；本 Skill 只复用经过审阅的验证原则，继续调用目标资料库既有脚本。

## 适配后的关键差异

- 把验证结果绑定到提交 SHA 或文件指纹、运行环境和具体结论；相关输入未变化时可引用已读日志，变化后重跑受影响项。
- 区分代码行为、证据字段、题目事实和远端写入；每一层只支持自身范围的结论。
- 在隔离副本或临时输入上确认检查器会拒绝已知错误；不在有用户改动的工作区回滚补丁来做红绿测试。
- 保留跳过项、来源限制、分母口径和版本冲突，不把“流程通过”写成“知识全对”。

## 上游许可声明

上面的验证流程参考并改写自 obra/superpowers 的 MIT 授权文档，保留其完整许可：

MIT License

Copyright (c) 2025 Jesse Vincent

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

本次回归检查的两条增补原则参考并改写自 mattpocock/skills，保留其完整许可：

MIT License

Copyright (c) 2026 Matt Pocock

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
