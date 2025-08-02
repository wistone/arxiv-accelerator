# JavaScript 模块化说明

## 📁 文件结构

原先的 `arxiv_assistant.html` 文件中包含了超过1500行的JavaScript代码，为了提高代码的可维护性和可读性，已将其拆分为以下9个模块化文件：

### 1. `config.js` - 全局配置和变量
- 定义全局变量和状态管理
- 包含 `window.AppState` 对象用于模块间状态共享

### 2. `ui.js` - UI控制相关函数
- 显示/隐藏加载状态、错误、成功消息
- 统计信息更新
- 模态框控制
- 事件监听器初始化

### 3. `search.js` - 搜索功能
- 文章搜索API调用
- 搜索结果展示
- 搜索表格生成

### 4. `analysis.js` - 分析功能管理
- 分析流程控制
- 分析选项管理
- 重试分析功能

### 5. `progress.js` - 进度管理和SSE连接
- 实时进度更新
- Server-Sent Events连接管理
- 备用进度检查机制
- 分析完成处理

### 6. `table.js` - 表格显示和排序
- 分析结果表格生成
- 排序功能实现
- 失败分析结果展示
- 表格交互功能（展开/收起）

### 7. `layout.js` - 页面布局管理
- 搜索模式和分析模式切换
- 容器宽度动态调整

### 8. `url.js` - URL状态管理
- URL参数解析和更新
- 浏览器历史管理
- 深度链接支持

### 9. `main.js` - 主初始化文件
- DOM加载完成后的初始化
- 事件监听器绑定
- 可用日期列表加载
- URL参数执行

## 🔗 模块依赖关系

```
main.js (入口)
├── config.js (全局状态)
├── ui.js (UI控制)
├── search.js → ui.js, url.js, layout.js
├── analysis.js → ui.js, progress.js, table.js, url.js
├── progress.js → ui.js, analysis.js
├── table.js → ui.js, layout.js
├── layout.js (独立)
└── url.js → search.js, analysis.js
```

## 📋 引入顺序

在 HTML 文件中，JavaScript 文件按以下顺序引入：

1. `config.js` - 必须最先加载，提供全局状态
2. `ui.js` - 提供基础UI控制函数
3. `search.js` - 搜索功能
4. `analysis.js` - 分析功能
5. `progress.js` - 进度管理
6. `table.js` - 表格显示
7. `layout.js` - 布局管理
8. `url.js` - URL管理
9. `main.js` - 最后加载，执行初始化

## 🎯 优势

1. **可维护性**：每个文件职责单一，易于理解和修改
2. **可读性**：代码结构清晰，逻辑分离
3. **可重用性**：模块化的函数可以在不同场景下复用
4. **可测试性**：各模块可以独立测试
5. **协作友好**：多人开发时减少代码冲突

## 🔧 全局状态管理

通过 `window.AppState` 对象在模块间共享状态：

```javascript
window.AppState = {
    currentArticles,      // 当前文章列表
    hasSearched,         // 是否已搜索
    currentAnalysisArticles, // 当前分析结果
    sortColumn,          // 排序列
    sortDirection,       // 排序方向
    currentEventSource,  // SSE连接
    progressCheckInterval, // 进度检查定时器
    analysisStartTime,   // 分析开始时间
    lastProgressUpdate   // 最后进度更新时间
}
```

## 📝 注意事项

- 所有模块都依赖于原生JavaScript，无第三方依赖
- 保持了原有的所有功能和用户体验
- 全局函数（如onClick事件处理）仍然可以正常工作
- 兼容原有的HTML结构和CSS样式