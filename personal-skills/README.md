# 个人技能备份与调用目录

保存本人使用、创建或维护的自定义技能，供恢复、跨设备使用和后续改进。本目录按用户 2026-10-22 的决定公开备份，位于 `joint3256/study-lib` 的 `personal-skills/`，不是另建的独立仓库。

整理日期：2026-10-22。本次完整备份 **5 个现用技能包、28 个技能文件**；另外归档从历史记录中找回的 3 个旧版主文件，旧版不计入现用完整技能包。

## 技能名称、作用和调用方法

| 技能 ID | 中文名称 | 作用与适用场景 | 调用示例 |
|---|---|---|---|
| [study-lib-audit](skills/study-lib-audit/SKILL.md) | 资料库可靠性核验 | 排查资料库的路径、误删、题目提取、证据与统计问题；复现、修复、回归验证，并按授权提交。它负责维护资料库，不代替普通讲题。 | 用 study-lib-audit 检查 study-lib，先复现问题，再修复并验证。 |
| [cz-combine](skills/cz-combine/SKILL.md) | 初中六科综合讲题 | 数学、物理、化学、历史、道法、语文；答案速查、逐题八板块、师生对白和总结，生成彩色 Word。不含英语。 | 用 cz-combine 讲解这份初中数学试卷，生成彩色 Word。 |
| [gaoshu1](skills/gaoshu1/SKILL.md) | 家教式循序渐进讲解 | 先补先修知识，再逐步解释依据与原理；适合基础薄弱、需要慢讲的学生，不设小测。项目主要用于高中数学，正文允许小学至本科。 | 用 gaoshu1 讲这几道高中数学题，先补基础，再一步步讲。 |
| [gaoshu2](skills/gaoshu2/SKILL.md) | 考前冲刺轻量七步讲解 | 时间紧时讲重点题；每批最多 8 页，说明易错点、原理和快解，生成 Word，并按需记录学习进度及错题。 | 用 gaoshu2 做考前冲刺，按轻量七步讲解这批题。 |
| [tiqu-extractor](skills/tiqu-extractor/SKILL.md) | 试卷原题清洁提取 | 从照片还原印刷题和图形、去掉手写；逐字逐图核对，交付 Word、PDF 和逐页 PNG，不提供答案或讲解。 | 用 tiqu-extractor 提取这些照片中的原题，去手写，交付 Word、PDF 和逐页 PNG。 |

需要先还原再讲解时，顺序为 `tiqu-extractor` → `cz-combine` / `gaoshu1` / `gaoshu2`。资料库本身有问题时使用 `study-lib-audit`。

## 以后怎样调用

对能够读取 GitHub 仓库的助手，可以直接说：

> 请读取 joint3256/study-lib 中 personal-skills/README.md，按我的任务选择技能，读取对应 SKILL.md 及所需附件后执行。开始前核对实际文件、依赖和已有授权。

也可以直接指定上表中的技能 ID。**GitHub 备份不会自动让所有聊天平台安装或启用技能**：新环境需要读取技能或按该环境支持的方式安装。不能访问时应报告限制，不能假装已经读取。

手动恢复时，把 `skills/<技能ID>/` **整个文件夹**复制到目标环境支持的自定义技能目录；保留 `references/`、`scripts/`、`assets/`、`agents/` 的相对结构。具体安装目录依目标产品而定，不能把某台机器的路径当成通用路径。`archive/` 中的旧文件不作为默认安装内容。

## 必要依赖与恢复检查

### study-lib-audit 与 cz-combine

两者需要实际资料库。备份源版本为 [joint3256/study-lib](https://github.com/joint3256/study-lib)，固定提交：

```text
c9d20dfd8d942e0268a19c60f507fac02660ff0b
```

`study-lib-audit` 复用资料库中的检查器和测试脚本。`cz-combine` 还需要其中的 `知识清单/`、`方法套路/`、`同步清单/`、`课标/`、`教材/` 说明。最稳妥的恢复方式是检出这一固定版本的完整资料库，随后核对更新；仅复制 Skill 不等于取得了知识库。

`cz-combine` 的路径检查只需要 Python 3.8+ 标准库。进入恢复后的 `skills/cz-combine` 目录，按本机实际位置运行：

```text
python -B scripts/check_library.py --lib-root "本机 study-lib 根目录"
```

也可按其 [知识库检索说明](skills/cz-combine/references/知识库检索.md) 设置 `CZ_COMBINE_LIB_ROOT`。教材位于独立本机目录时，用 `CZ_COMBINE_TEXTBOOK_ROOT` 或 `--textbook-root` 指定。必须保证配置对实际运行技能的进程可见。检查成功只能证明其覆盖的目录、字段或链接符合要求，不代表已读教材或事实全部正确。

### tiqu-extractor

需要 Python 3、`python-docx`、`Pillow`；重画图形还需要 `numpy`、`matplotlib`；Word/PDF/PNG 转换需要 LibreOffice 的 `soffice`、Poppler 的 `pdftoppm` 和中文字体。请保留全部 6 个脚本，包含供其他脚本导入的 `extract_schema.py`、`console_output.py`。

配图相对路径以 `extract.json` 所在目录为准。按 [技能主规范](skills/tiqu-extractor/SKILL.md) 检查依赖，在临时目录用合成素材验证，不能拿已有用户输出测试删除或覆盖。

### 讲解类技能的宿主能力

讲解类技能需要 Word 生成、渲染、审阅和交付能力。旧规范中的 Word `audit`、`present_files` 是原宿主工作流，本备份未附带这些平台功能；迁移到其他环境时，需要提供等效能力。它们不是下载后即可独立启动的应用。

## 备份范围、来源与历史版本

- `skills/`：5 个当前完整文件夹，备份时与来源逐字节核对。文件清单、大小、SHA-256 和来源提交见 [manifest.json](manifest.json)。
- `study-lib-audit` 是本次系列任务中创建并改进的个人维护技能；另外 4 个是资料库中已有、持续维护的项目技能。本目录不把所有原始内容都标成 Codex 首创。
- `archive/`：从用户历史记录找回的旧版技能主文件。见 [历史归档说明](archive/README.md)，其中列明附件缺失与未验证状态。
- `xhs631` 只找到历史名称和用途登记，没有找到技能正文，**未计作已备份技能**。
- 系统内置和第三方插件提供的 Skill 不属于本人创建的技能，不整套复制到此库。
- 当前备份是一个明确日期的快照；没有设置定时同步。以后新增或改进技能时，更新对应备份目录、目录说明和文件指纹，并提交新版本。4 个项目技能继续以仓库原有 `技能/` 目录为维护源；本目录保留固定日期的完整快照，调用前先核对维护源是否已有更新。

## 资料与许可边界

教材全本、整页原卷素材、完整聊天记录、凭据和个人学习记录不属于本次技能备份。教材全本仅保留在本人设备，**不得上传任何 GitHub 仓库，包括私有仓库**。历史技能中与此冲突的旧要求不再适用。

保留技能原有的署名和来源说明。`study-lib-audit/references/upstream.md` 包含适配来源及两份完整 MIT 许可；`cz-combine/references/` 保留各学科来源和许可限制。`gaoshu1`、`gaoshu2` 的原文只标注改编来源，未附完整许可证据；本次保留原文作公开备份，不擅自给所有技能统一添加开源许可证。公开可见不改变上游许可；进一步分发时仍须保留适用的署名与许可，并核对这些未补齐的出处信息。

## 本次验证的含义

本次检查技能文件是否齐全、复制是否一致、内部引用是否可定位，以及是否命中常见凭据模式；复用已有技能，不改写技能行为。`cz-combine` 已用实际资料库运行路径检查，结果通过，外置教材目录缺失有明确警告。没有把全部讲解、Word/PDF 生成流程重新运行一遍，也没有把历史主文件标成已经适配或安装。
