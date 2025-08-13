# 总体思路概述

目前系统通过 Markdown 文件按日期和分类组织论文数据和分析结果。我们计划将这些数据迁移到 Supabase 提供的关系型数据库中，以实现多用户支持、数据规范管理和便捷查询。主要需要设计以下几类数据表：用户（Users）、提示词（Prompts）、论文信息（Papers）、论文分类（Categories）以及分析结果（Analysis Results）。通过将不同实体分别建表并建立关联，可以避免数据冗余，满足业务规则并提高扩展性。

## 用户（Supabase Auth）
使用 Supabase Auth（`auth.users`）作为唯一的用户来源，不再自建本地 `users` 业务表。

- 所有涉及“创建者/执行者”的外键字段（如 `created_by`）均引用 `auth.users.id`（UUID）。
- 行级安全（RLS）策略可直接基于 `auth.uid()` 编写。

## 提示词表（Prompts）
**作用：** 存储AI分析所用的提示词（prompt），包括系统默认提示词和用户自定义的分析提示词。这样可以支持多个不同的分析提示模板，并允许在数据库中引用。

**字段示例：**
- prompt_id (主键)：提示词唯一标识。
- prompt_name：提示词名称或描述（如“系统默认打分Prompt”）。
- prompt_content：提示词具体内容（文本，大段字符串）。
- created_by：创建该提示词的用户ID，外键引用 `auth.users.id`（UUID）。
- created_at：提示词创建时间。

**说明：** 提示词可以预先存储一份默认的系统分析Prompt（即现在的 `multi-modal-llm` 提示词），也可以让用户日后添加新的分析Prompt。根据需求，一个Prompt可以被多个用户共享使用，因此我们将提示词定义为全局表，而非每个用户各自一份。通过 `created_by` 记录哪个用户创建了该Prompt，但不限制读取；可通过 RLS/应用逻辑限制非创建者的写操作。分析结果表仅引用 `prompt_id`，避免冗余存储。

## 论文信息表（Papers）
**作用：** 存储从 arXiv 获取的论文元数据。原先各 *-result.md 文件中的论文列表将汇总到这一全局表中。每条记录对应一篇论文，不重复存储，实现论文信息的集中管理。

**字段示例：**
- paper_id (主键)：论文记录内部唯一ID。
- arxiv_id：论文的 arXiv 标识符，例如 `2508.05636v1`。用原始字符串（含版本号）保存；对 `arxiv_id` 建唯一索引。
- title：论文标题。
- authors：论文作者列表（如逗号分隔）。
- author_affiliation：作者机构/单位信息（可选，若数据源提供，先以 `text` 存储；后续可演进为 `jsonb`）。
- abstract：论文摘要。
- link：论文链接（如 arXiv URL）。
- update_date：论文的 arXiv 更新/版本日期（用于日期查询）。
- primary_category：论文主分类（可选）。
- ingest_at：论文入库时间。

**说明：**
- **唯一性：** 可以对arxiv_id字段设置唯一索引，确保同一篇论文只存储一份。这样如果不同日期或分类抓取到同一论文（例如跨类别论文），不会在表中重复。
- **分类存储：** 我们不在该表直接设定多值的分类字段，而采用独立的分类表做多对多关联（见下文），以支持一篇论文属于多个分类的情况（例如跨领域论文，满足需求3每篇paper可能有多个category）。
- **规范化：** 论文表只存储论文本身的信息，不包含任何分析结果或用户关联，保证这一层数据的独立性。原先 Markdown 表格中，每个分析结果行都重复包含标题、作者等，现在这些字段统一在Papers表维护，避免了重复和不一致。

## 论文分类表（Categories）及关联表（Paper_Categories）
**作用：** 存储论文的类别标签（例如 arXiv 分类 cs.CV、cs.AI 等），并建立论文与类别的多对多关系。这样可以实现按分类过滤论文列表，并支持一篇论文对应多个类别。

**Categories表字段示例：**
- category_id (主键)：类别ID。
- category_name：标准arXiv代码（例如cs.CV、cs.AI等）。category_name是唯一索引。

**Paper_Categories表字段示例：**
- paper_id：论文ID，外键引用 Papers 表。
- category_id：类别ID，外键引用 Categories 表。
- 联合唯一键(paper_id, category_id)，并对category_id建索引。

**说明：**
- 每当从arXiv抓取论文时，根据其所属分类，在Paper_Categories插入对应关系。如果一篇论文有多个分类标签（arXiv允许交叉列出类别），则会有多条关联记录。
- 通过这个设计，我们可以方便地按类别查询论文。例如，查询某日期属于cs.CV类别的所有论文时，只需在Paper_Categories筛选category_id对应cs.CV，再根据paper_id关联论文表。相较于在Papers表用一个字段存储多个分类，这种范式设计更加规范，查询也灵活。
- Categories表也有助于避免在Papers表中反复存储类别字符串，提高了数据的一致性。

## 分析结果表（Analysis_Results）
**作用：** 存储每篇论文的AI分析结果。它将论文、提示词以及分析输出关联起来，相当于原先每个 *-analysis.md 文件中的内容，但以结构化方式保存。

**字段示例：**
- analysis_id (主键)：分析记录ID（可使用自增ID或UUID）。
- paper_id：被分析论文ID，外键引用 Papers 表。
- prompt_id：所使用提示词ID，外键引用 Prompts 表。
- analysis_result：分析结果内容（`jsonb`）。该 JSON 结构遵循 `multi-modal-llm` 提示词的输出约定，至少包含：
  - `pass_filter`: boolean
  - `raw_score`: number
  - `norm_score`: number（0-10）
  - `reason`: string
  - 以及 `core_features` / `plus_features` 等字段。
- created_by：执行此分析的用户ID（外键引用 `auth.users.id`）。
- created_at：分析创建时间戳。

**说明：**
- **唯一约束：** 对 `(paper_id, prompt_id)` 建联合唯一约束，避免同一论文+同一Prompt重复分析。
- **多Prompt支持：** 同一论文可用不同Prompt分析，互不冲突。
- **JSONB 存储与查询：**
  - 将完整输出存入 `jsonb`，便于灵活扩展；
  - 典型过滤需求：按 `pass_filter=true`、或按 `raw_score` 阈值/排序；
  - 建议：
    1) 对 `analysis_result` 建 GIN 索引（加速键/等值过滤，如 `pass_filter`）。
    2) 为高频排序/区间过滤字段（`raw_score`、可选 `norm_score`）增加“生成列（generated column）”，并建 B-Tree 索引，避免每次查询进行 JSON 提取与类型转换。

  - 示例查询：
    - 仅使用 JSONB（GIN 适合等值/包含匹配）：
      `where analysis_result @> '{"pass_filter": true}'`
    - 使用生成列（推荐用于排序/区间）：
      `where raw_score >= 8 order by raw_score desc limit 20`

- **不重复存储论文信息：** 分析表不再保存论文标题、作者等冗余字段，通过 `paper_id` 关联 `Papers` 获取。

## 关系与权限设计
**表关系概况：**
- Users 表通过用户ID与 Prompts 和 Analysis_Results 表相关联，用于标识创建者或执行者。
- Prompts 表与 Analysis_Results 表通过 prompt_id 相连（一对多，一条Prompt对应多条分析记录）。
- Papers 表与 Analysis_Results 表通过 paper_id 相连（一篇论文可对应多条不同Prompt的分析记录）。
- Papers 表与 Categories 表是多对多关系，通过 Paper_Categories 表实现。

**权限与共享：**
按照需求 4，所有用户可以读取彼此的分析结果和 Prompt 配置，但不能修改他人的内容：
- `Prompts`：SELECT 向经过身份验证用户开放；非创建者禁止 UPDATE/DELETE。
- `Analysis_Results`：SELECT 向经过身份验证用户开放；非创建者禁止 UPDATE/DELETE。

在 Supabase 中通过 RLS 策略实现（基于 `auth.uid()` 与 `created_by`），本设计已预留 `created_by` 字段以支持策略编写。

## 根据日期和分类的检索
新的设计能方便地按日期和分类查询论文及其分析：
- **按日期查询：** 如果要获取某一天新增/分析的论文，可以利用 Papers 表的 update_date 字段过滤，或者使用 Analysis_Results 的 created_at 字段（如果分析都是当日进行）。例如：“查询2025-08-02的所有分析结果”，可以执行：筛选 Papers.update_date = '2025-08-02'，连接 Analysis_Results 获取对应分析；或直接筛选 Analysis_Results.created_at = '2025-08-02' 的记录。具体取决于你想按论文发布日期还是分析执行日期查询，两者在本项目每日运行的情况下通常是一致的。
- **按分类查询：** 利用 Paper_Categories 关联。比如要获取 cs.CV 类别下某天的分析结果：先通过 Categories 表找到category_name = 'cs.CV'的ID，然后在 Paper_Categories 找出该 category 下所有 paper_id，再结合上述日期条件和 Analysis_Results 表筛选出对应分析记录。也可以建立视图或用JOIN简化查询。

通过规范的表结构和关联，实现类似当前文件命名（日期+分类）的层次查询效果，但查询更加灵活。例如，可以很容易地查询“某分类在一段日期范围内最高分的论文”这类复杂需求，这是文件存储难以实现的。