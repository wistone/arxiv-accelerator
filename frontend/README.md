# Frontend 前端代码

## 目录结构

```
frontend/
├── js/          # JavaScript 模块
│   ├── analysis.js    # 分析功能
│   ├── config.js      # 配置管理
│   ├── layout.js      # 布局控制
│   ├── main.js        # 主入口
│   ├── progress.js    # 进度显示
│   ├── search.js      # 搜索功能
│   ├── table.js       # 表格渲染
│   ├── ui.js          # UI 工具
│   └── url.js         # URL 管理
├── css/         # 样式文件
│   └── styles.css     # 主样式
├── index.html   # 主页面 (根目录)
```

## 技术栈

- **Vanilla JavaScript**: 原生 JavaScript，模块化设计
- **CSS3**: 现代响应式设计
- **Server-Sent Events**: 实时进度推送
- **Fetch API**: 异步网络请求

## 模块说明

### JavaScript 模块

- **analysis.js**: 论文分析功能，包含分析模态框和分析任务管理
- **config.js**: 全局配置和常量定义
- **layout.js**: 页面布局和导航控制
- **main.js**: 应用主入口，初始化和事件绑定
- **progress.js**: 实时进度显示，SSE 连接管理
- **search.js**: 论文搜索功能
- **table.js**: 数据表格渲染和交互
- **ui.js**: 通用 UI 组件和工具函数
- **url.js**: URL 参数管理和路由

### CSS 样式

- **styles.css**: 完整的样式定义，包含响应式设计和动画效果
