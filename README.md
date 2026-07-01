# ＡＵＲＯＲＡ GFP Design 2026

## 项目简介

从竞赛提供的 3 个非 sfGFP 参考 GFP 蛋白（amacGFP、cgreGFP、ppluGFP）出发，运用 ProteinMPNN 反向折叠 + ESMFold 结构预测，设计兼具高亮度和热稳定性的新型 GFP 变体。当前本地迭代已达到 **sort_score = 0.9291**，且与第一支队 SnowFold 的序列路线完全独立。

## 设计思路

- **种子选择**: 选取与 sfGFP 序列相似度最低的 3 个参考 GFP（amacGFP ~70%, cgreGFP ~30%, ppluGFP ~25%），最大化序列多样性
- **设计管线**: 参考序列 → ESMFold 预测结构 → ProteinMPNN 反向折叠生成新序列 → ESMFold r=8 筛选 → Top 6 提交
- **固定残基**: [1, 65, 66, 67, 96, 222]（起始甲硫氨酸 + 5 个生色团关键残基）
- **温度策略**: [0.1, 0.2, 0.5] 三档采样温度，平衡探索与利用

## 实验条件

| 参数 | 值 |
|:-----|:--|
| 种子序列 | amacGFP (7LG4), cgreGFP (2HPW), ppluGFP (2G6X) |
| 序列生成 | ProteinMPNN v_48_020 |
| 结构预测 | ESMFold (facebook/esmfold_v1) |
| 采样温度 | [0.1, 0.2, 0.5] |
| 候选/温度 | 100 |
| 总候选 | 900 |
| Fixed positions | [1, 65, 66, 67, 96, 222] |
| ESMFold recycles | 8 |
| 评分公式 | sort_score = pTM×0.40 + pLDDT×0.30 + chromo_pLDDT×0.30 |

## 当前结果

| 阶段 | 起点/父代 | 样本量 | Top1 sort_score | 备注 |
|:-----|:----------|:------:|:---------------:|:-----|
| Initial | amacGFP/cgreGFP/ppluGFP | 900 | 0.8008 | 从零起步，amacGFP 路线有效 |
| Local R1 | Initial Top2 | ~100 | 0.9046 | 中低温微调 |
| **Local R2** | Local R1 Top3 | ~135 | **0.9291** | 当前推荐提交 |
| Local R3 | Local R2 Top3 | ~135 | 0.9272 | 低温精修，未超越 R2 |
| Remote AutoLoop | Local/Initial Top6 | 1800/轮 | 运行中 | 自动持续迭代 |

当前推荐提交文件：`submission/submission_team2.csv`，对应 Local R2 Top6。

合规性验证：6 条序列均为 238aa、M 开头、标准 20AA、不在 Exclusion_List，且与第一支队 SnowFold Top6 的最大 identity 仅 8.8%。

分析图表：`docs/analysis_figures.html` 与 `docs/figures/`。

## 评分公式

```
sort_score = (pTM × 0.40) + (全局pLDDT / 100 × 0.30) + (生色团pLDDT / 100 × 0.30)
```

## 技术栈

- Python 3.10+, PyTorch >= 2.0, CUDA 12+
- ProteinMPNN (v_48_020)
- ESMFold (facebook/esmfold_v1) via HuggingFace Transformers

## 环境配置

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
git clone https://github.com/dauparas/ProteinMPNN.git
```

## 运行方式

```bash
cd pipeline
python team2_server.py
```

## 目录结构

```
ＡＵＲＯＲＡ-GFP-2026/
├── README.md
├── requirements.txt
├── .gitignore
├── submission/
│   └── submission_team2.csv
├── pipeline/
│   ├── team2_server.py
│   ├── team2_local_r2.py
│   └── team2_local_r3.py
├── data/
│   └── reference_sequences.txt
├── results/
│   ├── local_r1/
│   └── local_r2/
└── docs/
    └── design_report.md
```

## 自主开发工具：gssh CLI

本项目使用了我们自主开发的 **gssh** 命令行工具——一个专为远程 GPU 服务器协作而设计的轻量 CLI。

| 命令 | 功能 |
|:-----|:-----|
| `gssh run <session> "<cmd>"` | 远程执行任务（自动后台化） |
| `gssh cp <src> <dst>` | 双向文件传输 |
| `gssh logs <task-id> -f` | 实时查看任务日志 |
| `gssh task stop <task-id>` | 停止远程任务 |
| `gssh --json exec <session> "<cmd>"` | 一次性命令执行（JSON 输出） |

本项目通过 gssh 在远程 A800 80GB 服务器上执行 ProteinMPNN + ESMFold 管线，实现脚本上传、任务启动、进度监控、结果下载的全流程自动化。

## Agent 逻辑树

本项目使用 **Trae AI Agent** 辅助设计与迭代，核心逻辑如下：

```
[Trae AI Agent]
├── 1. 规则解析
│   ├── 读取竞赛规则（序列长度 220-250aa, M 开头, 20 种标准氨基酸）
│   ├── 解析评分指标（pTM, pLDDT, 生色团 pLDDT）
│   └── 加载 5 个参考 GFP 序列 + Exclusion_List
│
├── 2. 种子选择决策
│   ├── 分析 5 个参考序列与 sfGFP 的相似度
│   ├── 决策：选取相似度最低的 3 个（amacGFP/cgreGFP/ppluGFP）
│   └── 理由：最大化序列多样性 + 规避排除列表
│
├── 3. 设计管线执行
│   ├── 3a. ESMFold 预测 3 个种子序列的 3D 结构 → PDB
│   ├── 3b. ProteinMPNN 反向折叠
│   │   ├── 固定残基 [1, 65, 66, 67, 96, 222]
│   │   ├── 3 档温度 [0.1, 0.2, 0.5] × 100 候选
│   │   └── 3 父代 × 300 候选 = 900 总候选
│   ├── 3c. ESMFold r=8 结构预测 + 评分
│   └── 3d. 筛选 Top 6
│
├── 4. 合规检查
│   ├── 序列长度 220-250aa
│   ├── M 开头 + 标准氨基酸
│   └── Exclusion_List 比对
│
└── 5. 提交
    ├── 生成 submission CSV
    └── 整理仓库 + 文档
```

### Agent 关键执行日志

- **种子选择**: Agent 分析 5 个参考序列的 pairwise identity，发现 sfGFP/avGFP 相似度 >95%，决定弃用；选取 amacGFP(70%)/cgreGFP(30%)/ppluGFP(25%) 三个差异最大的种子
- **Fixed positions**: Agent 从第一支队的经验中得知 position 1 (M) 必须固定，直接采用 [1, 65, 66, 67, 96, 222]
- **温度策略**: Agent 选择 [0.1, 0.2, 0.5] 中等温度，因为从零开始需要一定探索空间，但不需要极低温（无精细微调需求）
- **远程执行**: Agent 通过 gssh 将脚本上传至 A800 服务器，启动后台任务并实时监控进度

## License

MIT
