# 技能（Skills）

本目录保存自用的豆包技能，随私有库 `study-lib` 跨设备同步。技能均为自制内容，
**不含教材全本**（教材受版权保护，只在各设备本地保存，不上云）。

## 技能清单

| 技能 | 作用 | 何时用 |
|---|---|---|
| **tiqu-extractor** | 把试卷/题目照片里的印刷题目与几何图**干净提取**（剔除一切手写），产出 Word＋PDF＋每页干净 PNG；交付前强制最严格逐字逐图核对 | 只提取、去手写、要干净原题时 |
| **cz-combine** | 初中**全科综合讲题**（数/物/化/历史/道法/语文，一个技能内分科专精），产出彩色讲解 Word：前 7 板块可照念口播，第 8 板块师生互动对白；无 PPT | 讲初中题、要知识点/思路/解答/快解时 |
| **gaoshu1** | 高中数学**家教式**讲法：先补旧知识再讲正题，无小测，适合基础很弱 | 高中数学、循序渐进 |
| **gaoshu2** | 高中数学**轻量七步**讲法：最短最快，适合考前突击 | 高中数学、考前冲刺 |

分工：**tiqu-extractor 只还原，cz-combine/gaoshu 只讲解**；先提取干净题，再讲解。

## 电脑端安装（Windows）

1. 安装并登录豆包电脑版，进入工作任务模式。
2. 把本目录下需要的技能**整个文件夹**复制到电脑端豆包的自定义技能目录
   `.user_skills/`（与手机/云端的 `.doubao/agent_mode/workspace/.user_skills/`
   对应；具体盘符路径可在电脑端让豆包帮你定位）。
   例如：`.user_skills/tiqu-extractor/SKILL.md`。
3. 使用 `cz-combine` 时，完整复制其 `scripts/` 与 `references/`。按 [知识库检索说明](cz-combine/references/知识库检索.md#定位与检查windows--linux-共用) 设置本机 `CZ_COMBINE_LIB_ROOT`；教材位置不同再设置 `CZ_COMBINE_TEXTBOOK_ROOT`。在 `cz-combine` 目录执行 `python scripts/check_library.py`，确认六科检查成功并处理警告。整库原位使用或目录联接可尝试自动发现；仅复制技能不等于安装了知识库。
4. 重新进入对话，直接 @技能名 或在需求里说技能名即可使用。

也可直接 `git clone` 本私有库后，把 `技能/<技能名>` 复制（或建立目录联接）到
`.user_skills/`。

## 更新

- 技能在一端改进并 push 后，另一端在本库目录执行 `git pull`，再把变更的技能
  文件夹同步到 `.user_skills/`。
- `cz-combine` 路径检查只需 Python 3.8+ 标准库。`tiqu-extractor` 生成与机检需 Python、`python-docx`、`Pillow`；重画另需 `numpy`、`matplotlib`；转换需 LibreOffice（`soffice`）、poppler（`pdftoppm`）与中文字体。缺少图片校验依赖时必须报错，不跳过校验。安装后按各技能主规范检查依赖是否在实际运行进程中可用。

## 不在云端的内容

- 教材全本（人教版初中数学/物理/化学）：仅各设备本地 `教材库/`，禁止上云。
- 本地路径在不同设备盘符不同，`cz-combine` 通过本机环境变量或命令行参数配置根目录，无需修改技能内的知识路径；检查与引用规则见上述检索说明。环境变量须对实际运行技能的进程可见。

## cz-combine 路径回归检查

在仓库根目录执行（仅临时目录内创建合成测试素材，不使用教材全本）：
```bash
python -B -m unittest discover -s tests -p "test_cz_combine_paths.py" -v
python -B 技能/cz-combine/scripts/check_library.py
```

## 仓库链接与索引检查

在仓库根目录执行 `python -B scripts/check_repository_links.py`。该检查只读本地内联链接的文件目标、明确的库内路径和方法索引；不联网、不修改内容，不将外部网址或知识事实标为已核实。方法数量按编号专题文件中的二级“方法 / 模型 / 快解·超纲”标题计数，不计讲法话术与附录。
