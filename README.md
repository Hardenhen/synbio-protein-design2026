# ＡＵＲＯＲＡ GFP Design 2026

> **队伍名称**：ＡＵＲＯＲＡ
> **推荐提交**：`submission/submission_team2.csv`（Local R2 Top-6）
> **最佳 sort_score**：**0.9291**（pTM 0.918 / pLDDT 0.920 / chromo_pLDDT 0.953）
> **设计路线**：基于 amacGFP / cgreGFP / ppluGFP 三个低相似度 GFP 家族成员的全新探索

---

## 一、项目简介

本仓库是 ＡＵＲＯＲＡ 队伍参加 **2026 Protein Design in SynBio Challenges** 的完整方案。

竞赛要求设计兼具**高初始亮度**与**优良热稳定性（72°C）**的绿色荧光蛋白（GFP），每队提交 6 条长度 220–250 aa 的序列。

与绝大多数以 sfGFP / avGFP 为起点的方案不同，ＡＵＲＯＲＡ 刻意选择 3 个与 sfGFP 相似度较低的天然 GFP 作为种子，通过 **ProteinMPNN 反向折叠 + ESMFold 结构预测**的迭代管线，在完全独立的序列空间中探索高分候选。当前迭代已达到 **sort_score = 0.9291**。

## 二、设计思路

- **种子选择**：选取与 sfGFP 相似度最低的 3 个参考 GFP（amacGFP ~70%、cgreGFP ~30%、ppluGFP ~25%），在相似度梯度上主动覆盖 25–70% 区间，最大化候选序列空间多样性，降低单一路线整体失败风险
- **设计管线**：参考序列 → ESMFold 预测结构（PDB）→ ProteinMPNN 反向折叠生成新序列 → ESMFold（recycles=8）结构预测与打分 → 筛选 Top 6
- **固定残基**：`[1, 65, 66, 67, 96, 222]`（起始甲硫氨酸 M + 5 个生色团关键残基），保证生色团微环境与起始密码子
- **迭代爬山**：以每轮 Top 候选作为下一轮父代，采样温度逐轮收窄（中低温 → 低温），实现稳定的分数爬升

## 三、评分公式

```
sort_score = pTM × 0.40 + (全局 pLDDT / 100) × 0.30 + (生色团 pLDDT / 100) × 0.30
存活门槛   = pTM > 0.60 且 全局 pLDDT > 0.60 且 生色团 pLDDT > 0.55
```

其中生色团 pLDDT 取残基 58–72 区段的平均 pLDDT。

## 四、实验条件

| 参数 | 值 |
|:-----|:--|
| 种子序列 | amacGFP (PDB 7LG4)、cgreGFP (PDB 2HPW)、ppluGFP (PDB 2G6X) |
| 序列生成 | ProteinMPNN `v_48_020` |
| 结构预测 | ESMFold (`facebook/esmfold_v1`) |
| 采样温度（首轮） | [0.1, 0.2, 0.5] |
| Fixed positions | [1, 65, 66, 67, 96, 222] |
| ESMFold recycles | 8 |
| 首轮总候选 | 900（3 种子 × 3 温度 × 100） |

## 五、迭代结果

| 阶段 | 起点/父代 | 样本量 | Top1 sort_score | 备注 |
|:-----|:----------|:------:|:---------------:|:-----|
| Initial | amacGFP / cgreGFP / ppluGFP | 900 | 0.8008 | 从零起步，amacGFP 路线最有效 |
| Local R1 | Initial Top2 | ~100 | 0.9046 | 中低温微调 |
| **Local R2** | Local R1 Top3 | ~135 | **0.9291** | **当前推荐提交** |
| Local R3 | Local R2 Top3 | ~135 | 0.9272 | 低温精修，未超越 R2 |

**推荐提交**：`submission/submission_team2.csv`，对应 Local R2 Top6。

### Local R2 Top6

| Rank | sort_score | pTM | pLDDT | chromo | 父代 |
|---:|---:|---:|---:|---:|:--|
| 1 | 0.9291 | 0.9180 | 0.9199 | 0.9530 | r2_p1 |
| 2 | 0.9196 | 0.9076 | 0.9117 | 0.9436 | r2_p1 |
| 3 | 0.9135 | 0.9007 | 0.9026 | 0.9416 | r2_p1 |
| 4 | 0.9130 | 0.9002 | 0.9027 | 0.9404 | r2_p1 |
| 5 | 0.9126 | 0.9027 | 0.9058 | 0.9326 | r2_p3 |
| 6 | 0.9125 | 0.9022 | 0.8992 | 0.9397 | r2_p3 |

## 六、合规性验证

运行 `python check_compliance.py` 可复现下列检查（全部 PASS）：

| 检查项 | 结果 |
|:-----|:--:|
| 序列数量 = 6 | ✅ |
| 长度 220–250 aa | ✅ 全部 238 aa |
| 以 M 开头 | ✅ |
| 仅含 20 种标准氨基酸 | ✅ |
| 不在 Exclusion_List（135,412 条） | ✅ |
| 队内 6 条互不重复 | ✅ |
| 与另一路线 Top6 最大 identity | 8.8%（充分独立） |

## 七、技术栈

- Python 3.10+，PyTorch ≥ 2.0，CUDA 12+
- ProteinMPNN（`v_48_020` vanilla 权重）
- ESMFold（`facebook/esmfold_v1`）via HuggingFace Transformers
- 分析与绘图：NumPy / R + ggplot2

## 八、环境配置

```bash
# 1. Python 环境
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. ProteinMPNN（单独克隆并放置权重）
git clone https://github.com/dauparas/ProteinMPNN.git

# 3. ESMFold 权重首次运行自动从 HuggingFace 下载（约 2.5GB）
```

| 项目 | 要求 |
|:-----|:-----|
| GPU 显存 | ≥ 16GB（ESMFold 推理，chunk_size 可调） |
| 磁盘 | ≥ 10GB（模型权重 + 中间结果） |
| 操作系统 | Linux（推荐）/ Windows |

## 九、复现方式

```bash
# 初始设计（3 种子 × 3 温度 × 100 候选）
python pipeline/team2_server.py

# 本地迭代 R2（以上一轮 Top3 为父代，中低温精修）
python pipeline/team2_local_r2.py

# 本地迭代 R3（低温精修）
python pipeline/team2_local_r3.py

# 合规性检查
python check_compliance.py
```

每一轮的 Top6 与提交文件均归档在 `results/` 下对应目录，便于逐轮追溯与复现。

## 十、目录结构

```
synbio-protein-design2026/
├── README.md
├── requirements.txt
├── .gitignore
├── check_compliance.py               # 合规性 + 相似度验证脚本
├── submission/
│   └── submission_team2.csv          # 推荐提交（Local R2 Top6）
├── pipeline/
│   ├── team2_server.py               # 初始设计管线
│   ├── team2_local_r2.py             # 本地迭代 R2
│   └── team2_local_r3.py             # 本地迭代 R3
├── data/
│   └── reference_sequences.txt       # 3 个种子 GFP 序列
├── results/
│   ├── local_r1/                     # 各轮 Top6 + submission
│   ├── local_r2/
│   └── local_r3/
└── docs/
    ├── design_report.md              # 设计思路文档
    ├── analysis_figures.html         # 图表汇总页
    ├── figures/                      # ggplot2 分析图
    └── build_pdf/                    # 参赛 PDF 报告及配图
```

## 十一、设计流程逻辑

```
[设计流程]
├── 1. 规则解析
│   ├── 序列长度 220–250 aa，以 M 开头，仅 20 种标准氨基酸
│   ├── 评分指标：pTM / pLDDT / 生色团 pLDDT
│   └── 加载 5 个参考 GFP 序列 + Exclusion_List
│
├── 2. 种子选择
│   ├── 计算 5 个参考序列与 sfGFP 的相似度
│   ├── 弃用 sfGFP / avGFP（相似度 >95%）
│   └── 选取 amacGFP / cgreGFP / ppluGFP（25–70% 相似度梯度）
│
├── 3. 设计管线
│   ├── ESMFold 预测种子结构 → PDB
│   ├── ProteinMPNN 反向折叠（固定 [1,65,66,67,96,222]）
│   ├── ESMFold recycles=8 打分
│   └── 筛选 Top 6 作为下一轮父代
│
├── 4. 迭代爬山
│   ├── R1：中低温 [0.05, 0.1] → 0.9046
│   ├── R2：中低温 [0.05, 0.1, 0.2] → 0.9291
│   └── R3：低温 [0.02, 0.05, 0.1] → 0.9272
│
└── 5. 合规检查与提交
    ├── 长度 / M 开头 / 标准氨基酸 / Exclusion_List
    └── 生成 submission CSV + 归档结果
```

## License

MIT
