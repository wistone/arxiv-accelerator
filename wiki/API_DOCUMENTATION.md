# API 文档

## 概述

Arxiv 论文智能分析助手提供完整的 RESTful API 接口，支持论文搜索、AI 分析、结果查询等核心功能。所有 API 都遵循统一的数据格式和错误处理机制。

## 通用规范

### 基础信息
- **基础 URL**: `http://localhost:8080` (本地) / `https://arxiv-accelerator.onrender.com` (生产)
- **数据格式**: JSON
- **字符编码**: UTF-8
- **HTTP 方法**: GET, POST

### 请求格式
```http
Content-Type: application/json
```

### 响应格式
```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "timestamp": "2025-08-11T12:00:00Z"
}
```

### 错误响应
```json
{
  "error": "错误信息",
  "code": 400
}
```

## 核心 API 接口

### 1. 搜索/导入论文

**端点**: `POST /api/search_articles`

**功能**: 从 arXiv 搜索并导入指定日期和分类的论文到数据库

**请求体**:
```json
{
  "date": "2025-08-08",
  "category": "cs.CV"
}
```

**响应**:
```json
{
  "success": true,
  "articles": [
    {
      "number": 1,
      "id": "2508.06485v1",
      "title": "论文标题",
      "authors": "作者列表",
      "abstract": "论文摘要",
      "link": "http://arxiv.org/abs/2508.06485v1",
      "author_affiliation": ""
    }
  ],
  "total": 93,
  "date": "2025-08-08",
  "category": "cs.CV",
  "performance": {
    "total_time": 5.48,
    "import_time": 0.00,
    "db_read_time": 0.00,
    "cache_hit": false
  }
}
```

**性能特性**:
- 智能缓存：重复请求直接返回缓存结果
- 增量导入：只导入新增论文，避免重复处理
- 批量操作：使用数据库批量插入提升性能

---

### 2. 检查分析状态

**端点**: `POST /api/check_analysis_exists`

**功能**: 检查指定日期和分类下论文的分析完成状态

**请求体**:
```json
{
  "date": "2025-08-08",
  "category": "cs.CV"
}
```

**响应**:
```json
{
  "exists": true,
  "total": 93,
  "completed": 45,
  "pending": 48,
  "all_analyzed": false
}
```

**字段说明**:
- `exists`: 是否存在已完成的分析
- `total`: 该日期分类下论文总数
- `completed`: 已完成分析的论文数
- `pending`: 待分析的论文数
- `all_analyzed`: 是否全部分析完成

---

### 3. 启动分析任务

**端点**: `POST /api/analyze_papers`

**功能**: 启动 AI 分析任务，支持增量分析和范围限制

**请求体**:
```json
{
  "date": "2025-08-08",
  "category": "cs.CV",
  "range_type": "top20"
}
```

**范围类型**:
- `top5`: 仅分析前5篇
- `top10`: 仅分析前10篇  
- `top20`: 仅分析前20篇
- `full`: 全部分析

**响应**:
```json
{
  "success": true,
  "task_id": "2025-08-08-cs.CV",
  "message": "分析任务已启动",
  "target_count": 20,
  "pending_count": 15
}
```

**智能分析特性**:
- **增量分析**: 只分析未处理的论文，避免重复工作
- **填充模式**: 支持从少到多的渐进式分析 (5→10→20→全部)
- **自动机构获取**: 对通过筛选的论文自动获取作者机构信息

---

### 4. 获取分析进度

**端点**: `GET /api/analysis_progress`

**功能**: 实时获取分析任务进度 (Server-Sent Events)

**查询参数**:
```
?date=2025-08-08&category=cs.CV&test_count=20
```

**SSE 数据流**:
```javascript
data: {
  "current": 15,
  "total": 20,
  "status": "processing",
  "paper": {
    "title": "当前处理的论文标题",
    "arxiv_id": "2508.06485v1",
    "status": "正在调用AI模型分析..."
  },
  "analysis_result": null
}
```

**状态类型**:
- `starting`: 任务启动中
- `processing`: 正在分析
- `fetching_affiliations`: 正在获取机构信息
- `completed`: 分析完成
- `error`: 分析出错

---

### 5. 获取分析结果

**端点**: `POST /api/get_analysis_results`

**功能**: 获取已完成的论文分析结果

**请求体**:
```json
{
  "date": "2025-08-08",
  "category": "cs.CV",
  "range_type": "top20"
}
```

**响应**:
```json
{
  "success": true,
  "articles": [
    {
      "number": 1,
      "id": "2508.06485v1",
      "title": "论文标题",
      "authors": "作者列表",
      "abstract": "论文摘要",
      "link": "http://arxiv.org/abs/2508.06485v1",
      "author_affiliation": "[{\"name\": \"清华大学\", \"country\": \"中国\"}]",
      "pass_filter": true,
      "score": 8,
      "analysis_result": "{\"pass_filter\": true, \"core_features\": {...}}"
    }
  ],
  "total": 20,
  "date": "2025-08-08",
  "category": "cs.CV",
  "range_type": "top20"
}
```

---

### 6. 获取作者机构

**端点**: `POST /api/fetch_affiliations`

**功能**: 为指定论文获取作者机构信息

**请求体**:
```json
{
  "paper_id": 12345,
  "link": "http://arxiv.org/abs/2508.06485v1"
}
```

**响应**:
```json
{
  "success": true,
  "affiliations": [
    {
      "name": "清华大学",
      "country": "中国"
    },
    {
      "name": "Stanford University", 
      "country": "美国"
    }
  ],
  "paper_id": 12345,
  "processing_time": 15.2
}
```

**处理流程**:
1. 下载论文 PDF 文件
2. 解析首页文本内容
3. 调用 AI 模型提取机构信息
4. 更新数据库并返回结果

---

### 7. 获取可用日期

**端点**: `GET /api/available_dates`

**功能**: 获取数据库中有论文数据的日期列表

**响应**:
```json
{
  "dates": [
    "2025-08-08",
    "2025-08-07", 
    "2025-08-06",
    "2025-08-05"
  ]
}
```

---

### 8. 清理缓存

**端点**: `POST /api/clear_cache`

**功能**: 清理服务器端缓存 (主要用于开发调试)

**请求体**:
```json
{
  "type": "all"
}
```

**缓存类型**:
- `all`: 清理所有缓存
- `search`: 只清理搜索缓存
- `import`: 只清理导入缓存

**响应**:
```json
{
  "success": true,
  "message": "已清理all缓存",
  "remaining_cache_keys": []
}
```

## 缓存策略

### 多级缓存设计

1. **搜索结果缓存**
   - TTL: 5分钟
   - 键格式: `{date}_{category}`
   - 作用: 避免重复数据库查询

2. **导入状态缓存**
   - TTL: 30分钟
   - 键格式: `import_{date}_{category}`
   - 作用: 避免频繁 arXiv API 调用

3. **机构信息缓存**
   - TTL: 永久 (重启清空)
   - 键格式: `affiliation_{arxiv_id}`
   - 作用: 避免重复 PDF 处理

### 缓存命中优化
```javascript
// 前端缓存检测
if (cache_hit) {
  // 直接返回缓存结果，响应时间 < 100ms
} else {
  // 执行完整查询，更新缓存
}
```

## 性能监控

### 关键指标

**响应时间**:
- 搜索 API: 平均 3-8 秒 (首次), < 100ms (缓存)
- 分析 API: 10-30 秒/篇论文
- 结果 API: 1-3 秒

**吞吐量**:
- 支持并发分析任务
- 批量数据库操作 (50-100 条/批)

**错误率**:
- 网络超时自动重试 (最多3次)
- 优雅降级处理

### 性能优化

**数据库优化**:
```sql
-- 关键查询索引
CREATE INDEX idx_papers_date_category 
ON app.papers(update_date, primary_category);

-- 分析结果复合索引  
CREATE INDEX idx_analysis_paper_prompt
ON app.analysis_results(paper_id, prompt_id);
```

**网络优化**:
- gzip 压缩减少传输量
- 连接复用减少建连开销
- 分页查询避免大数据传输

## 错误处理

### 常见错误码

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| 400 | 请求参数错误 | 检查请求格式和必需参数 |
| 404 | 资源不存在 | 确认日期和分类参数正确 |
| 500 | 服务器内部错误 | 查看服务器日志，联系管理员 |
| 503 | 服务暂时不可用 | 稍后重试或检查依赖服务 |

### 错误处理最佳实践

**客户端**:
```javascript
try {
  const response = await fetch('/api/search_articles', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({date, category})
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  
  const data = await response.json();
  return data;
} catch (error) {
  console.error('API调用失败:', error);
  // 显示用户友好的错误信息
}
```

**服务端**:
```python
@app.route('/api/search_articles', methods=['POST'])
def search_articles():
    try:
        # 业务逻辑
        return jsonify({'success': True, 'data': result})
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"API错误: {e}")
        return jsonify({'error': '服务器内部错误'}), 500
```

## API 版本控制

### 当前版本: v1

**版本策略**:
- 向后兼容的更改：补丁版本号递增
- 新增字段或端点：小版本号递增  
- 破坏性更改：大版本号递增

**版本标识**:
```http
X-API-Version: 1.0.0
```

## 安全考虑

### API 安全
- 参数验证防止注入攻击
- 请求频率限制防止滥用
- CORS 配置控制跨域访问

### 数据安全
- 参数化查询防止 SQL 注入
- 敏感信息脱敏处理
- 访问日志记录审计

---

通过这套完整的 API 接口，开发者可以轻松集成论文分析功能，构建自定义的学术研究工具。
