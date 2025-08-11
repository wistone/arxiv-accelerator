# 数据库架构设计

## 概述

Arxiv 论文智能分析助手采用现代化的数据库驱动架构，完全替代了之前基于文件存储的方案。系统使用 Supabase (PostgreSQL) 作为核心数据存储，提供高性能、高可靠性的数据服务。

## 核心优势

### 性能提升
- **查询速度**: 数据库索引查询比文件扫描快 10+ 倍
- **并发处理**: 支持多用户同时访问，无文件锁冲突
- **缓存优化**: 多级缓存策略，响应时间降低 50%+

### 数据一致性
- **ACID 事务**: 保证数据完整性，避免并发冲突
- **外键约束**: 确保关联数据的引用完整性
- **唯一约束**: 防止重复数据插入

### 可扩展性
- **水平扩展**: 支持读写分离和分片
- **结构化存储**: 便于数据分析和报表生成
- **API 化访问**: 标准 REST API，易于集成

## 数据库结构

### 表设计

#### 1. papers (论文主表)
```sql
CREATE TABLE app.papers (
    paper_id SERIAL PRIMARY KEY,
    arxiv_id VARCHAR(50) UNIQUE NOT NULL,      -- arXiv ID (如: 2508.05636v1)
    title TEXT NOT NULL,                       -- 论文标题
    authors TEXT,                              -- 作者列表
    abstract TEXT,                             -- 摘要
    link VARCHAR(500),                         -- arXiv 链接
    primary_category VARCHAR(50),              -- 主分类
    update_date DATE,                          -- 更新日期
    update_time TIMESTAMP,                     -- 更新时间
    author_affiliation TEXT,                   -- 作者机构 (JSON格式)
    ingest_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. categories (分类表)
```sql
CREATE TABLE app.categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(50) UNIQUE NOT NULL, -- 分类名称 (如: cs.CV)
    display_name VARCHAR(100),                 -- 显示名称
    description TEXT,                          -- 分类描述
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3. paper_categories (论文分类关联表)
```sql
CREATE TABLE app.paper_categories (
    paper_id INTEGER REFERENCES app.papers(paper_id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES app.categories(category_id) ON DELETE CASCADE,
    PRIMARY KEY (paper_id, category_id)
);
```

#### 4. prompts (提示词管理表)
```sql
CREATE TABLE app.prompts (
    prompt_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_name VARCHAR(100) UNIQUE NOT NULL,   -- 提示词名称
    prompt_content TEXT NOT NULL,               -- 提示词内容
    version VARCHAR(20),                        -- 版本号
    is_active BOOLEAN DEFAULT true,            -- 是否启用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 5. analysis_results (分析结果表)
```sql
CREATE TABLE app.analysis_results (
    analysis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id INTEGER REFERENCES app.papers(paper_id) ON DELETE CASCADE,
    prompt_id UUID REFERENCES app.prompts(prompt_id) ON DELETE CASCADE,
    pass_filter BOOLEAN NOT NULL,               -- 是否通过筛选
    exclude_reason TEXT,                        -- 排除原因
    raw_score INTEGER DEFAULT 0,               -- 原始分数
    norm_score INTEGER DEFAULT 0,              -- 标准化分数
    analysis_result TEXT,                       -- 完整分析结果 (JSON)
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(paper_id, prompt_id)                -- 防止重复分析
);
```

### 索引优化

#### 性能关键索引
```sql
-- 论文表索引
CREATE INDEX idx_papers_update_date_fast ON app.papers(update_date DESC, paper_id);
CREATE INDEX idx_papers_date_arxiv ON app.papers(update_date DESC, arxiv_id DESC);
CREATE INDEX idx_papers_arxiv_id ON app.papers(arxiv_id);

-- 分类关联索引
CREATE INDEX idx_paper_categories_category_paper ON app.paper_categories(category_id, paper_id);
CREATE INDEX idx_paper_categories_paper ON app.paper_categories(paper_id);

-- 分析结果索引
CREATE INDEX idx_analysis_results_paper_prompt ON app.analysis_results(paper_id, prompt_id);
CREATE INDEX idx_analysis_results_pass_filter ON app.analysis_results(pass_filter);
```

## 数据流设计

### 1. 论文导入流程
```
arXiv API → 解析论文信息 → 去重检查 → 批量插入 papers
                ↓
         解析分类信息 → 插入/更新 categories → 建立关联 paper_categories
```

### 2. AI 分析流程
```
选择待分析论文 → 调用 AI 模型 → 解析分析结果 → 插入 analysis_results
        ↓
   自动获取作者机构 → 更新 papers.author_affiliation
```

### 3. 结果查询流程
```
用户查询请求 → JOIN 多表查询 → 应用缓存 → 返回结构化结果
```

## 性能优化策略

### 查询优化
1. **复合索引**: 针对常用查询条件建立复合索引
2. **分页查询**: 使用 LIMIT/OFFSET 避免大数据量传输
3. **选择性查询**: 只查询必要字段，减少网络传输

### 写入优化
1. **批量操作**: 使用 upsert 批量插入，减少网络往返
2. **事务控制**: 合理使用事务，平衡一致性和性能
3. **连接池**: 复用数据库连接，减少连接开销

### 缓存策略
1. **应用缓存**: 5分钟 TTL 缓存热点查询结果
2. **导入缓存**: 30分钟 TTL 避免重复 API 调用
3. **机构缓存**: 永久缓存 PDF 解析结果

## 数据一致性保证

### 事务设计
```python
# 论文导入事务
with transaction():
    papers = upsert_papers_bulk(papers_data)
    categories = upsert_categories_bulk(category_names)
    upsert_paper_categories_bulk(associations)
```

### 约束设计
- **外键约束**: 保证关联数据完整性
- **唯一约束**: 防止重复数据 (arxiv_id, paper_id+prompt_id)
- **非空约束**: 确保核心字段数据完整

### 错误处理
- **优雅降级**: 单条数据失败不影响批量操作
- **重试机制**: 网络异常自动重试
- **日志记录**: 详细记录操作日志便于排查

## 监控和维护

### 性能监控
- 查询执行时间监控
- 索引使用率分析
- 缓存命中率统计

### 数据维护
- 定期清理测试数据
- 索引重建和统计信息更新
- 备份策略制定

## 迁移指南

### 从文件存储迁移
1. **数据提取**: 解析现有 Markdown 文件
2. **数据清洗**: 标准化数据格式
3. **批量导入**: 使用脚本批量导入数据库
4. **验证数据**: 对比迁移前后数据一致性

### 架构优势对比

| 方面 | 文件存储 | 数据库存储 |
|------|----------|------------|
| 查询性能 | O(n) 文件扫描 | O(log n) 索引查询 |
| 并发处理 | 文件锁冲突 | 支持高并发 |
| 数据一致性 | 手动保证 | ACID 事务 |
| 扩展性 | 受限于文件系统 | 支持水平扩展 |
| 维护成本 | 手动文件管理 | 自动化管理 |

## 最佳实践

### 开发建议
1. **使用 ORM**: 通过 repo 层抽象数据访问
2. **参数化查询**: 防止 SQL 注入
3. **连接管理**: 正确关闭数据库连接
4. **错误处理**: 全面的异常捕获和处理

### 性能建议
1. **避免 N+1 查询**: 使用 JOIN 或批量查询
2. **合理分页**: 避免一次查询过多数据
3. **索引维护**: 定期分析和优化索引
4. **监控慢查询**: 及时发现和优化性能瓶颈

---

通过这个现代化的数据库架构，系统实现了高性能、高可靠性和良好的可扩展性，为用户提供了流畅的使用体验。
