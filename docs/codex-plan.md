# modelagree 开发规划（Codex 执行版）

> 本文件是给 Codex（或其他编码代理）逐个执行的任务书，也是给维护者审阅的路线图。
> 仓库级规则见根目录 `AGENTS.md`，每个任务都必须遵守其中的 Invariants。

## 0. 怎么用这份文档

**一次只做一个任务，一个任务一个分支一个 PR。** 按第 2 节的顺序推进，合并后再派下一个。
标注“可并行”的任务可以同时派发，但它们可能在 `cli.py`、`report.py` 上有小冲突，合并时需要处理。

派发给 Codex 的提示词模板：

```text
Read AGENTS.md and docs/codex-plan.md. Implement task <ID> only, on a new branch
from the latest main. Follow the task's spec and acceptance criteria exactly.
Run every command in AGENTS.md "Commands" and make sure they pass.
In the PR description include: (1) what changed, (2) how each acceptance
criterion was verified, with the pytest summary line, (3) any deviation from
the spec and why. Do not start any other task.
```

每个 PR 合并前请你本人核对第 6 节的审阅清单。

## 1. 目标与定位

**一句话定位：** 给“用 LLM 当标注员”的研究者用的、统计口径诚实的一致性评估工具。

它要回答的问题：

1. 模型标注和人工参考标签的一致性有多高？置信区间多宽？
2. 失败、拒答、格式错误是否在悄悄抬高准确率？（已有：显式分母、failure-as-wrong 下界）
3. 模型之间、模型与多个人工标注员之间的一致性，是否落在人与人之间的一致性范围内？
4. 这次评估能否被别人原样复现和审计？（已有：冻结 manifest、不可变原始响应）

差异化来自统计严谨性和可审计性，不来自功能数量。因此优先级是：
**统计核心（Phase 1）> 人类基线（Phase 2）> 更多 provider（Phase 3）> 发布与传播（Phase 4）。**

## 2. 任务总览与顺序

| ID | 任务 | 依赖 | 规模 | 优先级 | 可并行 |
| --- | --- | --- | --- | --- | --- |
| T0.1 | 兼容性金标测试 + CHANGELOG | — | S | P0 | |
| T0.2 | README 瘦身，文档拆分到 `docs/` | T0.1 | M | P0 | 与 T0.3、T1.1 |
| T0.3 | lint、`--version`、包元数据 | T0.1 | S | P1 | 与 T0.2 |
| T1.1 | scoring 重构为纯函数（输出不变） | T0.1 | S | P0 | 与 T0.2 |
| T1.2 | 有序任务加权 kappa | T1.1 | S | P0 | |
| T1.3 | 逐标签 P/R/F1 与 macro-F1 | T1.2 | S | P0 | |
| T1.4 | Krippendorff's alpha（多评分者信度） | T1.3 | M | P0 | |
| T1.5 | Bootstrap 置信区间 | T1.4 | M | P0 | |
| T1.6 | `scores.json` 结构文档 | T1.5 | S | P1 | |
| T2.1 | `modelagree validate` 预检命令 | T0.1 | S | P1 | 与 Phase 1 |
| T2.2 | `modelagree export` CSV 导出 | T1.1 | S | P1 | 与 Phase 1 |
| T2.3 | 多人工标注员与人类基线 | T1.5 | L | P0 | |
| T2.4 | 多数投票参考标签策略 | T2.3 | M | P2 | |
| T2.5 | 使用配方文档 | T2.3 | S | P2 | |
| T3.1 | Anthropic provider | T0.1 | M | P1 | 与 Phase 1/2 |
| T3.2 | OpenAI 兼容接口 provider（vLLM/Ollama 等） | T3.1 | M | P1 | |
| T3.3 | 并发执行 `--workers` | T3.2 | M | P2 | |
| T3.4 | 真实 API 冒烟脚本（不进 CI） | T3.2 | S | P2 | |
| T4.1 | 打包与 PyPI 发布流程 | 见里程碑 | S | P1 | |
| T4.2 | README 截图与对比说明 | T0.2, T1.5, T2.3 | S | P1 | |
| T4.3 | 社区文件（CONTRIBUTING、CITATION 等） | T0.2 | S | P1 | 与 T4.2 |
| T4.4 | 人类基线教程 | T2.3 | S | P1 | 与 T4.2 |
| T4.5 | JOSS 论文草稿（可选） | v0.3.0 | M | P2 | |

T1.2 到 T1.5 都要改 `metrics.py`，所以按顺序执行，不要并行。

**里程碑：**

- **v0.2.0“统计核心”**：T0.1–T0.3、T1.1–T1.6、T2.1、T2.2、T4.1。
- **v0.3.0“人类基线与更多模型”**：T2.3–T2.5、T3.1–T3.4、T4.2–T4.4。
- **之后**：T4.5，以及第 5 节里明确暂不做的事项（需要时重新评估）。

---

## 3. 任务详情

### Phase 0：护栏与门面

#### T0.1 兼容性金标测试 + CHANGELOG

**目的：** 给后续所有重构和新增指标加一道护栏，保证已有输出不被悄悄改变。

**改动：**

- 在**任何其他改动之前**，用当前代码跑 demo，生成 `tests/golden/demo_scores_v0.1.0.json`。
  生成时去掉不确定的字段：`resources.latency_seconds.total` 和
  `resources.attempt_latency_seconds.total`（保留对应的 `denominator`）。
- 新增 `tests/test_compat.py`：
  - 把 `examples/` 复制到 `tmp_path/examples`，运行 `run` 和 `score`，产物落在 `tmp_path/runs/demo`。
  - 断言金标是当前输出的**子集**：递归比较，金标里的每个键都存在且值相等；列表长度与顺序一致；
    浮点数用 `pytest.approx(rel=1e-12)`；上面两个延迟 `total` 跳过。
  - 断言 `run_fingerprint` 与金标完全相同（守住 AGENTS.md 第 6 条：新配置键在默认值下不能进入 manifest）。
  - 再加一个用例：用 0.1.0 格式的 manifest（即当前 demo 产物）运行 `report`，确认能成功生成报告。
- 新增 `CHANGELOG.md`（Keep a Changelog 格式），包含 `Unreleased` 和 `0.1.0` 两节，`0.1.0` 简述现有功能。

**验收：** `pytest` 通过；故意改动 `metrics.py` 里任意一个现有指标时，`test_compat.py` 会失败（在 PR 描述里说明你验证过）。

#### T0.2 README 瘦身，文档拆分

**目的：** 新用户在前 20 行就知道这个工具是给谁用、回答什么问题；细节移到 `docs/`。

**改动：**

- README 控制在大约 150 行以内，结构如下：
  1. 一句话定位（见第 1 节）和 CI 徽章；
  2. “它回答什么问题”：3–4 条；
  3. 五行快速上手（保留现有命令）；
  4. 报告能看到什么：先放 `docs/images/report.png` 的占位引用和 TODO 注释，截图在 T4.2 补；
  5. 功能列表：短条目；
  6. 与通用评测框架的侧重点区别：只描述本项目的侧重点，**不要断言其他工具做不到什么**；
  7. 文档索引；
  8. `## Known limitations`（**必须保留在 README**，`tests/test_documentation.py` 依赖其中的表格）；
  9. 许可证。
- 把现有 README 的其余内容**原样迁移**（可以微调措辞以适配新标题，但不能删除事实性内容）到：
  - `docs/configuration.md`：配置参考、数据集格式、图片、`--limit`
  - `docs/run-artifacts.md`：输出与断点续跑
  - `docs/metrics.md`：指标与分母
  - `docs/providers.md`：真实 provider、凭据、解码与脱敏规则、重试
  - `docs/crisismmd.md`：CrisisMMD 转换器
- 更新 `DESIGN.md` 里指向 README 锚点的链接。

**验收：** 旧 README 中的每一条事实陈述都能在新 README 或 `docs/*.md` 中找到（在 PR 描述里附上段落迁移对照表）；`pytest` 通过；所有相对链接有效。

#### T0.3 工具链与元数据

**改动：**

- `pyproject.toml` 增加 `dev` extra：`ruff`。CI 增加一个 lint job：`ruff check src tests scripts`，
  只启用 `E9,F63,F7,F82,F401`（语法错误、未定义名、未使用导入），**不要引入格式化**，避免全仓库大面积 diff。
  修掉它报出的问题。
- `modelagree --version` 输出 `modelagree 0.1.0`，取自 `modelagree.__version__`；加一个测试，断言它与 `pyproject.toml` 的版本一致。
- `pyproject.toml` 补充 `keywords`、`classifiers`、`[project.urls]`（Homepage、Issues、Changelog）。
  `authors` 由维护者本人填写，**不要自行编写作者信息**。

**验收：** CI 新 job 通过；`modelagree --version` 有测试覆盖。

---

### Phase 1：统计核心

> 本阶段所有新指标都遵守 AGENTS.md 第 5 条：带分子分母，未定义时值为 `None` 并给出 `undefined_reason`。
> 新指标只**新增**键，不改已有键（金标测试兜底）。每个新指标都要同步更新 `report.py`、`docs/metrics.md`、`DESIGN.md` 和 `CHANGELOG.md`。

#### T1.1 scoring 重构为纯函数

**目的：** 让 bootstrap（T1.5）和人类基线（T2.3）可以在重采样后的行上重复计算同一套指标。

**改动：** 在 `scoring.py` 中拆出：

- `reference_rows(items, records_by_item, field, spec)`：返回每个条目一行
  `(item_id, reference_known, reference, prediction_valid, prediction)`；
- `reference_field_scores(rows, spec)`：返回与现在 `models[mid]["fields"][field]` 完全相同的字典；
- `pairwise_rows(...)` 和 `pairwise_field_scores(rows, spec)`：同理，对应 pairwise。

`score()` 只负责组合这些函数并写文件。

**验收：** 金标测试不改一行即通过；`scores.json` 字节级与重构前相同（在 PR 中附 `diff` 结果，延迟字段除外）。

#### T1.2 有序任务的加权 kappa

**规格：** 对 `ordinal` 字段，在 `metrics` 中新增 `linear_weighted_kappa` 和 `quadratic_weighted_kappa`。

- k 个等级，索引为 i（参考）和 j（预测）。不一致权重：线性 `w = |i-j|/(k-1)`，平方 `w = ((i-j)/(k-1))^2`。
- 观察到的不一致 `Do = Σ w_ij·O_ij / n`；期望不一致 `De = Σ w_ij·r_i·c_j / n²`，其中 r、c 为边际计数。
- 输出：`{**ratio(De - Do, De, sample_size=n), "observed_weighted_disagreement": Do, "expected_weighted_disagreement": De, "weights": "linear"|"quadratic", "undefined_reason": ...}`，因此 `value = 1 - Do/De`。
- n=0 时原因为 `"no comparable items"`；De=0 时原因为 `"expected disagreement is zero"`。
- 不进入 `failure_as_wrong`（与现有 kappa 一致，报告会显示 “Not defined”）。pairwise 的有序字段自动获得该指标。

**测试锚点**（使用 `tests/test_metrics.py` 中已有的 ORD 例子 `[('low','high'),('mid','high'),('high','low'),('mid','mid')]`）：

- 线性：`Do = 5/8`，`De = 7/16`，`value = -3/7`
- 平方：`Do = 9/16`，`De = 5/16`，`value = -4/5`

另加一个完全一致的用例（值为 1），以及一个 De=0 的用例（所有参考和预测都是同一个等级）。

#### T1.3 逐标签 P/R/F1 与 macro-F1

**规格：**

- 所有任务类型在字段结果中新增与 `metrics` 平级的 `per_label`：
  `{label: {"precision": ratio(TP, TP+FP), "recall": ratio(TP, TP+FN), "f1": ratio(2TP, 2TP+FP+FN), "support": TP+FN}}`。
  - categorical/ordinal：一对一分类的 one-vs-rest 计数；
  - multi_label：按每个标签是否出现在集合里计数。
- `metrics` 中新增 `macro_f1`：`numerator` 为已定义 F1 之和，`denominator` 为 F1 已定义的标签数，`sample_size` 为 n，
  另加 `labels_undefined`（F1 分母为 0 的标签列表）。所有标签都未定义时值为 `None`。
- 均为条件指标，不进入 `failure_as_wrong`。pairwise 中以左侧模型为“参考”，在文档里写明方向性。
- 报告：在每个字段的详情里加逐标签表格。

**测试锚点：**

- CAT 例子 `[('a','a'),('a','b'),('b','b'),('b','b')]`：
  a 的 P=1/1、R=1/2、F1=2/3；b 的 P=2/3、R=2/2、F1=4/5；macro-F1 = 11/15（分子 22/15，分母 2）。
- MULTI 例子 `[(['a'],['a','b']),([],[]),(['b'],[])]`：
  a 的 TP=1、FP=0、FN=0、F1=1；b 的 TP=0、FP=1、FN=1、F1=0；macro-F1 = 1/2。

#### T1.4 Krippendorff's alpha（多评分者信度）

**目的：** 在多个模型之间（以及加上参考标签后）给出一个能处理缺失值的统一信度指标；T2.3 的人类基线也复用它。

**改动：** 新模块 `src/modelagree/reliability.py`，只用标准库。

- `krippendorff_alpha(units, metric, levels=None)`：`units` 是“每个条目的一组有效取值”的列表，缺失值直接不放进去。
  使用重合矩阵（coincidence matrix）方法。只有一个取值的条目不可配对，不参与计算。
- 距离度量：`nominal`（categorical）和 `ordinal`（Krippendorff 有序度量，使用边际频数 n_g：
  `δ²(c,k) = (Σ_{g=c..k} n_g − (n_c + n_k)/2)²`）。
- multi_label：每个标签视为“出现/不出现”的二元 nominal 变量，逐标签计算 alpha。**不要**给出跨标签的聚合值。
- 输出：`{**ratio(De - Do, De), "observed_disagreement": Do, "expected_disagreement": De, "metric": ..., "pairable_units": ..., "pairable_values": ..., "coders": [...], "undefined_reason": ...}`。
  未定义情形：可配对取值少于 2、有效评分者少于 2、De=0。
- `scores.json` 新增顶层键 `multi_rater`：

  ```json
  {"<field>": {"task_type": "...",
               "models": {...alpha...},
               "models_and_reference": {...alpha...}}}
  ```

  multi_label 字段改为 `{"per_label": {"<label>": {"models": ..., "models_and_reference": ...}}}`。
  只有一个模型时，`models` 为未定义，原因为 `"fewer than two coders"`。
  无效预测和未知参考都视为缺失值。参考标签作为评分者时，在 `coders` 中记为 `"reference"`，与模型 ID 分开存放，不能和模型 ID 冲突。
- 报告新增 “Multi-rater reliability” 小节。

**测试：**

- Krippendorff (2011) *Computing Krippendorff's Alpha-Reliability* 中 4 个评分者 × 12 个条目、带缺失值的示例数据，
  nominal 和 ordinal 都要对照文中公布的值。在测试注释里注明出处；如果无法确认公布值，就在注释中手算重合矩阵并以手算结果为准，同时在 PR 里说明。
- 小型手算用例：完全一致（值为 1）；两评分者无缺失；只有一个可配对条目时为未定义。

#### T1.5 Bootstrap 置信区间

**规格：**

- `score` 和 `report` 新增参数：`--bootstrap N`（默认 0，即关闭）、`--seed S`（默认 0）、`--confidence C`（默认 0.95，取值在 (0,1) 开区间）。
- N>0 时，`scores.json` 新增顶层键
  `"bootstrap": {"resamples": N, "seed": S, "confidence": C, "method": "percentile", "unit": "item"}`；N=0 时不出现，保持向后兼容。
- **重采样方法：** 以条目为单位有放回抽样。每个计算单元（某模型某字段、某 pair 某字段、某字段的 multi_rater）都新建
  `rng = random.Random(seed)`，并按 `idx = [int(rng.random() * n) for _ in range(n)]` 依次生成 N 组下标。
  这样所有单元使用**同一组**重采样，内存占用低，也便于以后做配对比较。不要使用 `randrange` 或 `choices`，以保证跨 Python 版本的确定性。
- 每组重采样都用 T1.1 的纯函数在重采样后的行上重新计算。区间用定义了的值，按线性插值分位数（Hyndman–Fan type 7）计算，
  上下分位为 `(1-C)/2` 和 `1-(1-C)/2`。
- 在 `metrics` 和 `failure_as_wrong` 的每个标量指标、以及 `multi_rater` 的每个 alpha 上附加：
  `"ci": {"low": ..., "high": ..., "defined_resamples": k}`。k=0 时 low/high 为 `None`。
  `per_label` 和 confusion matrix 不加 CI，以控制输出体积。
- 报告：有 CI 时在值后显示 `[low, high]`，并在页首说明 bootstrap 设置。
- 文档：说明这个区间只反映**条目抽样**的不确定性，不包含模型采样随机性（后者见 T2.5 的重复运行配方），也不适用于条目之间不独立的情况（例如同一推文的多张图片，参见 CrisisMMD 说明）。

**测试：**

- 同一 seed 两次运行输出完全相同；不同 seed 输出不同。
- 所有预测都正确的数据集：CI 为 `[1, 1]`。
- 一个小数据集在 `N=200, seed=0` 下的具体 low/high 值写死在测试中（CI 会在 3.10/3.12/3.14 上运行，用来验证跨版本确定性）。
- `--bootstrap 0` 时输出与金标一致。

**性能目标：** 1000 条目 × 3 模型 × 3 字段、N=1000，在普通笔记本上 60 秒内完成。在 PR 中报告实测耗时；超出时先优化热点（例如预先计算标签索引），不要引入 numpy。

#### T1.6 `scores.json` 结构文档

- 新增 `docs/scores-schema.md`：逐键说明含义、类型、何时出现、对应版本。
- 写明兼容策略：`version` 保持 1；新增键属于向后兼容变更；使用方必须忽略未知键；任何破坏性变更都要求 `version` 升到 2，并在 CHANGELOG 中说明。
- 可选：新增 `docs/scores.schema.json`（JSON Schema），在 test extra 中加入 `jsonschema`，并用 demo 输出做校验测试。

---

### Phase 2：研究工作流

#### T2.1 `modelagree validate CONFIG [--limit N]`

**规格：** 只做预检，不创建 run 目录、不加锁、不构造 provider、不发网络请求。向 stdout 输出 JSON：

- `run_dir`、`items`、`items_with_images`、`models`（id/provider/model）、`planned_requests`（条目数 × 模型数）；
- `reference_coverage`：每个字段的 known/unknown 计数；
- `missing_environment`：缺失的环境变量**名称**（绝不输出值）；
- `run_status`：`new`、`resumable`（附带各状态计数：completed、permanent_error、retryable_error、not_requested）或 `fingerprint_mismatch`。

退出码：配置无效或指纹不匹配时为 1；其他情况为 0（缺环境变量只作为警告）。

**测试：** 新目录、部分完成的目录、指纹不匹配、缺失 key 只输出名称；断言执行后 run 目录不存在。

#### T2.2 `modelagree export RUN_DIR [--output PATH]`

**规格：** 默认写到 `RUN_DIR/predictions.csv`，长表格式，每个（模型, 条目, 字段）一行，列为：
`item_id, model_id, field, task_type, reference, reference_known, prediction, prediction_valid, prediction_error, response_status, format_violations`。

- multi_label 的值用 JSON 编码，保持原始顺序；缺失值写空字符串；`format_violations` 用分号连接。
- 行顺序：模型 ID 排序，条目按 manifest 顺序，字段按 schema 顺序。使用标准库 `csv`，UTF-8 编码。
- 不修改单元格内容来防范电子表格公式注入，但在文档中说明这一风险。

**测试：** demo 导出 12 条目 × 2 模型 × 3 字段 = 72 行加表头；抽查几行，包括无效预测、未知参考和多标签。

#### T2.3 多人工标注员与人类基线

**目的：** 回答第 1 节问题 3：模型和人的一致性，是否落在人与人之间的一致性范围内。

**数据格式：** 条目可选字段 `"annotations": {"<annotator_id>": {"<field>": value}}`。

- `load_dataset` 校验结构：annotator ID 为非空字符串，值为映射。值本身的合法性在评分时用 `validate_value` 判断，非法值视为缺失并计数。
- `labels` 的语义不变，仍是主参考。
- 没有 annotations 的数据集，manifest 和指纹完全不变（金标测试兜底）。
- **请求中绝不能包含 annotations**：加测试断言 request 和 api_request 中都没有 annotations。

**输出：** 至少有一个条目带 annotations 时，`scores.json` 新增顶层键 `human_baseline`，每个字段包含：

- `annotators`：排序后的 ID 列表；`items_with_annotations`；
- `annotator_pairwise_pooled`：所有标注员两两之间、在双方都有效的条目上合并计算的精确一致率（ratio 形式）。
  multi_label 另给合并后的 mean Jaccard；
- `annotator_alpha`：标注员之间的 Krippendorff alpha（复用 T1.4；multi_label 逐标签计算）；
- `per_model[<model_id>]`：
  - `model_annotator_pooled`：模型与每位标注员在双方都有效的条目上合并计算的精确一致率；
  - `model_annotator_pooled_failure_as_wrong`：模型无效、而标注员有效的配对算作不一致；
  - `alpha_annotators_plus_model`：把该模型作为额外评分者加入后的 alpha；
- 开启 bootstrap 时，以上标量都附带 `ci`。另给
  `difference_vs_human = model_annotator_pooled − annotator_pairwise_pooled` 及其在同一组重采样上的 CI，
  它是一个差值而非比例，单独说明其含义。

**报告：** 新增 “Human baseline” 小节，用一张表把人与人、模型与人的一致性并列展示。

**示例：** 新增 `examples/annotators-demo.jsonl` 和 `examples/annotators-demo.yaml`：
沿用 demo 的 12 个条目 ID 和文本（这样可以复用 `mock-a.json`、`mock-b.json`），加入 3 位虚构标注员，包含分歧和缺失。所有内容必须是合成的。

**测试：** 手算一个 3 条目 × 2 标注员 × 1 模型的小例子，覆盖所有新键；无 annotations 时不出现 `human_baseline`。

#### T2.4 多数投票参考标签策略（P2）

- 新配置键 `reference_policy: labels | annotator_majority`，默认 `labels`。默认值时**不写入**冻结配置（AGENTS.md 第 6 条）。
- `annotator_majority`：categorical/ordinal 取严格过半（多于有效标注数的一半）的值，否则为未知；
  multi_label 中某标签被超过一半的有效标注员选中才计入；没有有效标注时为未知。
- 派生出的参考标签记录在 `scores.json` 中，manifest 保留原始数据。
- 文档说明：用多数投票做参考后再和单个标注员比较存在偏差，`human_baseline` 不使用派生参考。

#### T2.5 使用配方文档（P2）

新增 `docs/recipes.md`，内容包括：

- **自一致性 / 重测信度：** 同一个 provider 模型配置两次，使用不同的 `id`，然后看 pairwise 一致性。说明 temperature 设置的影响，以及 provider 侧可能存在缓存。
- **参数对比：** 同一模型、不同参数，配置为不同 ID。
- **先小规模试跑：** 用 `--limit` 试跑，再换新的 `run_dir` 跑全量。
- **人类基线：** 指向 T4.4 的教程。

---

### Phase 3：更多模型

所有 provider 都遵守现有模式：只用标准库 HTTPS、固定端点（T3.2 例外，见下）、凭据只来自环境变量、拒绝重定向、错误只记录固定错误码。
测试一律 mock `http.open_request`，参照 `tests/test_providers.py`。新增的密钥变量要加入 `security.KEY_VARIABLES`。

#### T3.1 Anthropic provider

- `provider: anthropic`，环境变量 `ANTHROPIC_API_KEY`。
- `POST https://api.anthropic.com/v1/messages`，请求头 `x-api-key`、`anthropic-version: 2023-06-01`、`content-type: application/json`。
- 请求体：`model`；`max_tokens`（来自 `parameters.max_output_tokens`，Anthropic 必填，配置校验时缺失直接报错，不设隐式默认值）；
  `system` 为冻结的 prompt；`messages: [{"role":"user","content":[{"type":"text","text":...}, 图片块]}]`。
  图片块为 `{"type":"image","source":{"type":"base64","media_type":...,"data":...}}`。
  内容块顺序与现有 provider 保持一致（文本在前、图片在后），以保证跨模型可比，并在 DESIGN.md 中记录这一选择。
- 参数白名单：`max_output_tokens`（正整数）；`effort`（映射到 `output_config.effort`，取值 `low|medium|high|xhigh|max`）；
  `temperature`（**[0,1]**，与 OpenAI 的 [0,2] 不同，`validate_parameters` 需要按 provider 区分范围）；`top_p`（[0,1]）；`top_k`（正整数）。
  文档写明：当前一代 Claude 模型会以 HTTP 400 拒绝非默认的采样参数，这类请求会记录为 permanent error；采样参数只对较旧的模型有效。
- **不要**发送 `fallbacks` 或任何服务端回退参数（AGENTS.md 第 10 条），也不要设置 `thinking`。
- 响应解析：拼接所有 `type == "text"` 的内容块文本，跳过 thinking 等其他块。
  `stop_reason`（包括 `refusal`、`max_tokens`）保留在原始 HTTP 响应中；拒答或截断时照常保存为 completed，评分时按无效处理。
  用量：`input_tokens`、`output_tokens`；`total_tokens` 记为 `None`，API 不直接提供，也不自行推算。
- 529 和其他 5xx 已经按可重试处理，确认现有逻辑覆盖即可。

**测试：** 请求构造（请求头含版本号，`api_request` 中没有 key）、图片块、用量、thinking 块被跳过、refusal、缺少 `max_output_tokens` 的配置报错、temperature>1 被拒、`ANTHROPIC_API_KEY` 被脱敏。

#### T3.2 OpenAI 兼容接口 provider

- `provider: openai_compatible`，模型级必填键 `base_url`（只允许出现在这个 provider 上，会进入指纹）。
  可选环境变量 `OPENAI_COMPATIBLE_API_KEY`，设置了才发送 `Authorization: Bearer`。
- `base_url` 校验：scheme 必须是 `https`；`http` 只允许用于 `localhost`、`127.0.0.1`、`::1`。
  不允许 userinfo、query、fragment。端点为 `base_url.rstrip('/') + '/chat/completions'`。
- 请求体：`model`；`messages: [{"role":"system","content":prompt}, {"role":"user","content":...}]`。
  无图片时 user content 用纯字符串，兼容性最好；有图片时用 `[{"type":"text",...},{"type":"image_url","image_url":{"url":"data:..."}}]`。
  参数白名单：`temperature`（[0,2]）、`top_p`、`max_output_tokens`（映射为 `max_tokens`）、`seed`。
- 响应：`choices[0].message.content`（字符串，或 `type == "text"` 的部件列表）；`message.refusal` 是字符串时拼接进文本。
  用量：`prompt_tokens`、`completion_tokens`、`total_tokens`。
- DESIGN.md 记录安全上的取舍：这是唯一允许用户指定端点的 provider；它使用独立的密钥变量，所以 OpenAI 的 key 永远不会被发往任意主机。

**测试：** URL 校验的各种拒绝情形；有 key 和无 key 两种请求；图片；字符串和列表两种 content；refusal；用量。

#### T3.3 并发执行 `--workers N`（P2）

- `run` 新增 `--workers N`（默认 1，此时行为与现在完全一致）。用 `ThreadPoolExecutor` 并发处理待请求的（模型, 条目）对。
  每个任务内部沿用现有的重试循环，写入各自独立的记录文件。`--workers` 不进入指纹。
- provider 实例每个模型只创建一次，并确认它们是线程安全的（现有 HTTP provider 无状态，mock 只读）。
- Ctrl-C 时取消尚未开始的任务，等待进行中的任务写完；锁由现有的 context manager 释放。
- 文档提示：并发会更快触发 429 限流，靠现有的重试和退避处理。

**测试：** mock provider 下 `--workers 4` 与 `--workers 1` 产生的记录，除时间戳和延迟外完全相同；可重试错误的行为不变；不会有两个任务写同一路径。

#### T3.4 真实 API 冒烟脚本（P2，不进 CI）

`scripts/live_smoke.py CONFIG`：只有设置了 `MODELAGREE_LIVE=1` 才运行；对每个模型只跑前 2 个条目，写到临时 `run_dir`；打印每条记录的状态和解析结果。
用途是让维护者用真实 key 验证 provider 兼容性。不被 pytest 收集，不在 CI 中运行。

---

### Phase 4：发布与传播

#### T4.1 打包与 PyPI 发布

- 发版时把版本号同步到 `pyproject.toml` 和 `__init__.py`（T0.3 的测试保证两者一致），并整理 CHANGELOG。
- CI 新增 job：`python -m build` 加 `twine check --strict dist/*`。
- 新增 `.github/workflows/release.yml`：推送 `v*` 标签时触发，先构建，再用 `pypa/gh-action-pypi-publish` 通过 Trusted Publishing 发布
  （`permissions: id-token: write`，`environment: pypi`）。不使用任何 token secret。
- README 的安装方式改为 `pip install modelagree`，保留源码安装说明。

#### T4.2 README 截图与对比说明

- 如果环境里有 Chromium/Playwright，就用 headless 方式截取 demo 报告（开启 bootstrap，带 annotators demo），保存为 `docs/images/report.png`，控制在 300 KB 以内；
  环境不支持时，留下 TODO 和生成命令，交给维护者手动截图。
- 完善 README 中“侧重点区别”一节：只陈述本项目做了什么（显式分母、failure-as-wrong、人类基线、可审计记录），不点名评价其他工具的缺点。

#### T4.3 社区文件

- `CONTRIBUTING.md`：开发命令、测试约定、Invariants 摘要（链接到 AGENTS.md）、PR 要求。
- `CITATION.cff`：作者姓名、ORCID 等用 `TODO` 占位，由维护者本人填写。
- `.github/ISSUE_TEMPLATE/`：bug 报告和功能请求两种模板。bug 模板要求附上 `modelagree --version` 和最小配置，并提醒**不要粘贴 API key 和真实数据**。
- `SECURITY.md`：如何私下报告安全问题，具体渠道由维护者填写。

#### T4.4 人类基线教程

`docs/tutorial-human-baseline.md`：以 `examples/annotators-demo.yaml` 为例，从 `validate` 到 `run`、`score --bootstrap 1000`、`report`、`export`，完整走一遍。
文中展示真实命令输出（由测试或脚本生成，不手写数字），并解释怎样解读“模型与人的一致性 vs 人与人的一致性”及其置信区间。

#### T4.5 JOSS 论文草稿（P2，可选，由维护者决定是否投稿）

- `paper/paper.md` 和 `paper/paper.bib`，遵循 JOSS 格式，正文约 1000 词：Summary、Statement of need、功能、与相关工作的关系。
- **不得编造参考文献。** 只使用维护者提供的文献，或能确认存在的经典文献（例如 Cohen 1960 的 kappa、Krippendorff 的信度方法、关于用 LLM 做文本标注的研究）。
  每条 bib 记录都加上 `note = {TODO: verify}`，由维护者逐条核实。

---

## 4. 需要维护者本人完成的事

这些事 Codex 做不了，或者不应该替你做：

1. **真实数据验证：** 下载 CrisisMMD v2.0，运行转换器，再用真实 key 跑 `--limit 12` 的小规模评估（会产生少量 API 费用）。
   把发现的问题提成 issue。这是 README 里 “Known limitations” 中两条限制的唯一解法。
2. **T3.4 冒烟测试：** 新 provider 合并后，用真实 key 跑一次。
3. **PyPI：** 注册账号，为本仓库配置 Trusted Publisher（workflow 为 `release.yml`，environment 为 `pypi`），然后推送 `v0.2.0` 标签。
4. **身份信息：** 填写 `pyproject.toml` 的 `authors`、`CITATION.cff`、`SECURITY.md` 的联系方式。
5. **GitHub 仓库设置：** 填写 description；topics 建议加 `llm`、`annotation`、`inter-rater-reliability`、`cohens-kappa`、`krippendorff-alpha`、`evaluation`。
6. **决定是否投 JOSS：** JOSS 看重实际使用和学术工作量，建议在有真实案例（第 1 条）之后再投。
7. **逐个审阅 PR**（见第 6 节）。

## 5. 明确不做的事

- Web 界面、数据库、账户系统、任务队列（DESIGN.md 已说明理由）。
- 自由文本的 LLM-as-judge 评分、prompt 自动优化。
- 依赖各 provider 的结构化输出或 JSON mode：不同 provider 的约束机制不一致，会破坏跨模型可比性（见 DESIGN.md）。
- 服务端拒答回退或跨模型自动重试（AGENTS.md 第 10 条）。
- 暂缓、以后再评估：跨 run 的比较命令（例如比较不同 prompt）、provider 的 Batch API、更多 provider。

## 6. 每个 PR 的审阅清单

- [ ] 只做了一个任务，没有夹带无关改动或大面积格式化。
- [ ] `python -m pytest` 全部通过，CI 三个 Python 版本都是绿色。
- [ ] `tests/test_compat.py` 未被修改，或修改理由充分且已在 PR 中说明（只允许新增断言，不允许放宽）。
- [ ] 没有新增运行时依赖（查看 `pyproject.toml` 的 diff）。
- [ ] 新指标有手算测试，注释里写了算式。
- [ ] 未定义的情形返回 `None` 加原因，没有用 0 或 1 兜底。
- [ ] 报告仍然没有 JavaScript 和外部资源，新输出都经过 `esc()`。
- [ ] README 或 `docs/`、`DESIGN.md`、`CHANGELOG.md` 已同步更新。
- [ ] 没有 API key、真实数据或 `runs/` 目录被提交。
