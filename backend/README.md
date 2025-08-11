# Backend 后端代码

## 目录结构

```
backend/
├── services/                  # 🏢 业务逻辑层
│   ├── __init__.py
│   ├── analysis_service.py       # 论文分析服务
│   ├── arxiv_service.py          # arXiv数据导入服务
│   └── affiliation_service.py    # 作者机构解析服务
├── clients/                   # 🔌 外部服务客户端
│   ├── __init__.py
│   ├── ai_client.py             # AI模型客户端 (豆包等)
│   └── arxiv_client.py          # arXiv API客户端
├── utils/                     # 🛠️ 工具函数层
│   ├── __init__.py
│   └── pdf_parser.py            # PDF解析工具
└── db/                        # 💾 数据访问层
    ├── __init__.py
    ├── client.py               # 数据库连接
    └── repo.py                 # 数据访问对象
```

## 技术栈

- **Flask**: Python Web 框架
- **Supabase**: PostgreSQL 数据库服务
- **豆包 AI**: 智能论文分析模型
- **feedparser**: RSS/Atom 解析
- **pdfminer**: PDF 文本提取
- **requests**: HTTP 网络请求

## 架构层次

### 1. Services 业务逻辑层

负责核心业务功能的实现，不依赖具体的外部服务实现。

#### analysis_service.py
- 论文AI分析逻辑
- 分析结果解析和验证
- 评分计算和标准化

#### arxiv_service.py  
- arXiv API 数据获取
- 论文数据解析和清洗
- 数据库批量导入

#### affiliation_service.py
- 作者机构信息提取
- PDF处理和AI解析
- 结果缓存管理

### 2. Clients 外部服务客户端

封装与外部服务的交互，提供统一的接口。

#### ai_client.py
- AI模型（豆包）接口封装
- 请求重试和错误处理
- 会话管理

#### arxiv_client.py
- arXiv服务网络交互
- PDF文件下载优化
- 元数据获取

### 3. Utils 工具函数层

提供通用的工具函数，被各层复用。

#### pdf_parser.py
- PDF文本提取优化
- arXiv ID解析
- 文本清理和预处理

### 4. DB 数据访问层

管理数据库连接和数据操作。

#### client.py
- Supabase 连接管理
- 数据库配置

#### repo.py
- 数据访问对象 (DAO)
- 数据库操作封装
- 查询优化

## 设计原则

### 单一职责原则 (SRP)
每个模块只负责一个明确的功能域，职责清晰。

### 依赖倒置原则 (DIP)  
高层模块不依赖低层模块，都依赖于抽象。

### 开闭原则 (OCP)
对扩展开放，对修改封闭。便于添加新功能。

### 接口隔离原则 (ISP)
客户端不应该依赖它不需要的接口。

## 最佳实践

### 错误处理
分层错误处理，每层负责适当的错误转换和上下文添加。

### 日志记录
结构化日志，便于问题定位和性能监控。

### 配置管理
环境变量集中管理，支持开发/生产环境切换。

### 测试友好
松耦合设计，便于 Mock 和单元测试。
