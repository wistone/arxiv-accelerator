# 📚 Arxiv 论文智能分析助手

一个基于数据库的现代化论文分析工具，集成了论文爬取、AI智能分析和Web界面，帮助研究人员高效筛选和分析Arxiv论文。

🌐 **在线演示**: https://arxiv-accelerator.onrender.com/

## 🌟 核心特性

### 📊 智能论文爬取
- ✅ 支持 arXiv cs.CV、cs.LG 和 cs.AI 分类
- ✅ 自动处理时区差异和历史日期查询
- ✅ 智能增量导入，避免重复数据
- ✅ 直接存储到 Supabase 数据库，性能优异

### 🤖 AI 智能分析
- ✅ 基于豆包大模型的深度论文分析 (Doubao-1.6-flash)
- ✅ 多模态大模型相关度评估
- ✅ 智能评分系统（核心特征 + 加分特征）
- ✅ 自动获取作者机构信息
- ✅ 实时分析进度跟踪

### 🖥️ 现代化 Web 界面
- ✅ 响应式设计，支持桌面和移动设备
- ✅ 实时分析进度显示 (Server-Sent Events)
- ✅ 智能缓存系统，提升用户体验
- ✅ 可排序的分析结果表格
- ✅ 直接跳转到 PDF 链接

### 🗃️ 数据库驱动架构
- ✅ 基于 Supabase/PostgreSQL 的高性能存储
- ✅ 完整的关系型数据模型
- ✅ 智能索引优化，查询速度提升 3-5 倍
- ✅ 支持并发访问和数据一致性

## 🚀 快速开始

### 1. 环境准备
```bash
# 克隆项目
git clone https://github.com/yourusername/arxiv-accelerator.git
cd arxiv-accelerator

# 安装依赖
pip install -r requirements.txt
```

### 2. 数据库配置
配置 Supabase 数据库连接：
```bash
# 复制环境变量模板
cp env.example .env

# 编辑 .env 文件
SUPABASE_URL=your-supabase-project-url
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### 3. AI 模型配置
配置豆包 API：
```bash
# 在 .env 文件中添加
DOUBAO_API_KEY=your-doubao-api-key
DOUBAO_MODEL=your-doubao-model-endpoint
```

#### 获取豆包 API 密钥
1. 访问 [豆包大模型控制台](https://console.volcengine.com/ai/)
2. 创建应用并获取 API 密钥
3. 记录模型接入点 ID

### 4. 数据库初始化
```bash
# 使用提供的 SQL 脚本初始化数据库
# 在 Supabase 控制台中运行 sql/ 目录下的脚本：
# - 001_init_schema.sql (数据库结构)
# - 002_seed_basics.sql (基础数据)
# - 003_permission_setup.sql (权限设置)
```

### 5. 启动服务
```bash
# Linux/Mac
./start.sh

# 或手动启动
python server.py
```

### 6. 开始使用
打开浏览器访问 http://localhost:8080

## 📋 使用流程

1. **📅 选择日期和分类** - 从下拉菜单选择目标日期和研究分类
2. **🔍 搜索文章列表** - 系统自动爬取并存储论文到数据库
3. **🤖 智能分析** - 选择分析范围，启动 AI 分析任务
4. **📊 查看结果** - 实时查看分析结果，支持排序和筛选

## 🏗️ 技术架构

### 数据库设计

**[数据库架构设计](wiki/DATABASE_ARCHITECTURE.md)** - 核心数据模型、索引策略和性能优化
```sql
-- 核心表结构
app.papers           -- 论文基础信息
app.categories       -- 分类信息
app.paper_categories -- 论文分类关联
app.prompts          -- AI 提示词管理
app.analysis_results -- 分析结果
```

### 系统架构
```
前端 (HTML/CSS/JS)
      ↓ AJAX/SSE
后端 (Flask)
      ↓ SQL
数据库 (Supabase/PostgreSQL)
      ↓ API
外部服务 (arXiv API, 豆包 AI)
```

## 🔧 核心 API
**[API 文档](wiki/API_DOCUMENTATION.md)** - 完整的 RESTful API 接口说明和使用示例

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/search_articles` | POST | 搜索/导入论文 |
| `/api/analyze_papers` | POST | 启动分析任务 |
| `/api/check_analysis_exists` | POST | 检查分析状态 |
| `/api/get_analysis_results` | POST | 获取分析结果 |
| `/api/analysis_progress` | GET | 实时进度 (SSE) |
| `/api/fetch_affiliations` | POST | 获取作者机构 |
| `/api/clear_cache` | POST | 清理缓存 |

## 📊 分析评分系统

### 核心特征 (2分/项)
- **multi_modal**: 涉及视觉且语言
- **large_scale**: 使用大规模模型  
- **unified_framework**: 统一框架解决多任务
- **novel_paradigm**: 新颖训练范式

### 加分特征 (1分/项)
- **new_benchmark**: 提出新基准
- **sota**: 刷新 SOTA
- **fusion_arch**: 融合架构创新
- **real_world_app**: 真实应用
- **reasoning_planning**: 推理/规划
- **scaling_modalities**: 扩展多模态
- **open_source**: 开源

### 评分规则
- **原始分**: 核心特征分 + 加分特征分
- **标准分**: min(10, 原始分)
- **通过阈值**: 标准分 ≥ 4

## 🚀 生产环境部署

### Render 云部署 (推荐)

1. **准备代码仓库**
```bash
git clone https://github.com/yourusername/arxiv-accelerator.git
```

2. **在 Render 创建服务**
- 访问 [Render 控制台](https://dashboard.render.com/)
- 创建 Web Service，连接 GitHub 仓库
- 配置构建命令: `pip install -r requirements.txt`
- 配置启动命令: `./start.sh`

3. **设置环境变量**
```bash
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
DOUBAO_API_KEY=your-doubao-api-key
DOUBAO_MODEL=your-doubao-model
```

## 🎯 性能优化

### 数据库优化
- ✅ 复合索引优化查询性能
- ✅ 批量插入减少网络开销
- ✅ 智能分页避免内存溢出
- ✅ 查询结果缓存

### 应用优化
- ✅ 多级缓存策略
- ✅ 异步任务处理
- ✅ 连接池管理
- ✅ PDF 下载优化

## 📁 项目架构总览

### 🏗️ 完整目录结构

```
arxiv-accelerator/
├── 🌐 前端 Frontend
│   ├── frontend/
│   │   ├── js/                    # JavaScript 模块
│   │   │   ├── analysis.js           # 分析功能
│   │   │   ├── config.js             # 配置管理
│   │   │   ├── layout.js             # 布局控制
│   │   │   ├── main.js               # 主入口
│   │   │   ├── progress.js           # 进度显示
│   │   │   ├── search.js             # 搜索功能
│   │   │   ├── table.js              # 表格渲染
│   │   │   ├── ui.js                 # UI 工具
│   │   │   └── url.js                # URL 管理
│   │   ├── css/                   # 样式文件
│   │   │   └── styles.css            # 主样式
│   │   └── index.html             # 主页面 (根目录)
│
├── 🏢 后端 Backend  
│   ├── backend/
│   │   ├── services/              # 业务逻辑层
│   │   │   ├── analysis_service.py   # 论文分析服务
│   │   │   ├── arxiv_service.py      # arXiv数据导入服务
│   │   │   └── affiliation_service.py # 作者机构解析服务
│   │   ├── clients/               # 外部服务客户端
│   │   │   ├── ai_client.py          # AI模型客户端 (豆包等)
│   │   │   └── arxiv_client.py       # arXiv API客户端
│   │   ├── utils/                 # 工具函数层
│   │   │   └── pdf_parser.py         # PDF解析工具
│   │   └── db/                    # 数据访问层
│   │       ├── client.py             # 数据库连接
│   │       └── repo.py               # 数据访问对象
│   └── server.py                  # Flask Web服务器 (根目录)
│
├── 📊 数据库脚本
│   └── sql/                       # SQL 初始化脚本
│       ├── 001_init_schema.sql       # 数据库结构
│       ├── 002_seed_basics.sql       # 基础数据
│       ├── 003_permission_setup.sql  # 权限设置
│       └── 006_performance_indexes.sql # 性能索引
│
├── 📚 文档
│   ├── wiki/                      # 项目文档
│   │   ├── README.md                 # Wiki 首页
│   │   ├── DATABASE_ARCHITECTURE.md  # 数据库架构
│   │   ├── API_DOCUMENTATION.md      # API 文档
│   │   └── RENDER_DEPLOYMENT_GUIDE.md # 部署指南
│   ├── prompt/                    # AI 提示词
│   │   ├── system_prompt.md          # 分析提示词
│   │   └── author_affliation_prompt.md # 机构提取提示词
│   └── README.md                  # 项目主文档
│
├── ⚙️ 配置文件
│   ├── requirements.txt           # Python依赖
│   ├── start.sh                  # 启动脚本
│   ├── env.example               # 环境变量模板
│   └── .gitignore                # Git忽略文件
```

### 🎯 架构设计原则

#### 1. 前后端分离
- **Frontend**: 纯静态资源，专注用户界面和交互
- **Backend**: 业务逻辑和数据处理，提供 RESTful API

#### 2. 分层架构
```
表示层 (Presentation Layer)
    ↓
业务逻辑层 (Business Logic Layer)  
    ↓
数据访问层 (Data Access Layer)
    ↓
数据库层 (Database Layer)
```

#### 3. 模块化设计
- **Services**: 核心业务功能
- **Clients**: 外部服务封装
- **Utils**: 通用工具函数
- **DB**: 数据库操作抽象

### 📊 数据流架构

#### 论文导入流程
```
arXiv API → services/arxiv_service.py → db/repo.py → PostgreSQL
```

#### AI 分析流程  
```
User Request → server.py → services/analysis_service.py → clients/ai_client.py → 豆包 AI
                                        ↓
                            db/repo.py → PostgreSQL
```

#### 机构解析流程
```
PDF URL → clients/arxiv_client.py → utils/pdf_parser.py → services/affiliation_service.py
                                                              ↓
                                                        clients/ai_client.py → 豆包 AI
```

## 💡 使用技巧

### 分析模式选择
| 模式 | 数量 | 适用场景 | 预计耗时 |
|------|------|----------|----------|
| 仅前5篇 | 5 | 功能测试 | ~2分钟 |
| 仅前10篇 | 10 | 快速验证 | ~5分钟 |
| 仅前20篇 | 20 | 中等规模 | ~10分钟 |
| 全部分析 | 全部 | 完整分析 | ~30-60分钟 |

### 智能缓存策略
- **搜索缓存**: 5分钟 TTL，提升重复查询速度
- **导入缓存**: 30分钟 TTL，避免频繁 API 调用
- **机构缓存**: 永久缓存，减少 PDF 处理时间

## 🐛 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查 `SUPABASE_URL` 和 `SUPABASE_SERVICE_ROLE_KEY`
   - 确认网络连接正常

2. **论文导入失败**
   - 检查 arXiv API 连通性
   - 查看后端日志错误信息

3. **AI 分析异常**
   - 验证豆包 API 密钥和模型配置
   - 检查 `prompt/system_prompt.md` 文件

4. **前端显示问题**
   - 清理浏览器缓存和 Cookie
   - 检查开发者工具网络请求

### 性能调优
- 数据库查询慢：检查索引使用情况
- 内存占用高：调整批处理大小
- PDF下载慢：检查网络带宽和超时设置

## 📄 开源协议

MIT License - 仅供学习和研究使用

---

**🚀 Happy Researching! 让 AI 助力您的学术探索之旅！ 📚**