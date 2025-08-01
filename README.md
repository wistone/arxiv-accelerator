# 📚 Arxiv 论文智能分析助手

一个集成了论文爬取、智能分析和Web界面的完整工具，帮助研究人员高效筛选和分析Arxiv论文。

https://arxiv-accelerator.onrender.com/

## 🌟 功能特点

### 📊 论文爬取
- ✅ 支持 arXiv cs.CV、cs.LG 和 cs.AI 分类
- ✅ 自动处理时区差异和历史日期查询
- ✅ 智能URL构建，支持最新和历史论文爬取
- ✅ 生成结构化的 Markdown 表格

### 🤖 智能分析
- ✅ 基于豆包大模型的深度论文分析(目前使用Doubao-Seed-1.6-flash)
- ✅ 多模态大模型相关度评估
- ✅ 智能评分系统（核心特征 + 加分特征）
- ✅ 支持批量处理和测试模式

### 🖥️ Web界面
- ✅ 响应式设计，支持桌面和移动设备
- ✅ 实时分析进度显示
- ✅ 智能缓存检测，避免重复分析
- ✅ 可排序的分析结果表格
- ✅ 摘要展开/收起功能

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置豆包API
在使用AI分析功能前，需要配置豆包API密钥：

#### 方法一：手动创建环境文件（推荐）
1. 复制环境变量模板文件：
   ```bash
   cp env.example .env
   ```

2. 编辑 `.env` 文件，填入您的豆包API信息：
   ```bash
   DOUBAO_API_KEY=your-doubao-api-key-here
   DOUBAO_MODEL=your-doubao-model-endpoint-here
   ```

#### 方法二：设置系统环境变量
```bash
# Linux/Mac
export DOUBAO_API_KEY="your-doubao-api-key"
export DOUBAO_MODEL="your-doubao-model-endpoint"

# Windows
set DOUBAO_API_KEY=your-doubao-api-key
set DOUBAO_MODEL=your-doubao-model-endpoint
```

#### 获取豆包API密钥
1. 访问 [豆包大模型控制台](https://console.volcengine.com/ai/)
2. 创建应用并获取API密钥
3. 记录模型接入点ID

#### 测试API连接
配置完成后，您可以运行测试验证API是否正常工作：
```bash
python test/test_doubao.py
```

### 3. 启动服务
```bash
# Linux/Mac
./start.sh

# 或手动启动
python server.py
```

### 4. 访问应用
打开浏览器访问: http://localhost:8080

### 5. 使用流程
1. **选择日期和板块** (cs.CV、cs.LG 或 cs.AI)
2. **搜索文章列表** - 爬取指定日期的论文
3. **开始分析** - 使用AI对论文进行深度分析
4. **查看结果** - 浏览分析结果，支持按总分排序

## 🚀 生产环境部署

### 方案一：Render 云部署（推荐）

#### 1. 准备GitHub仓库
```bash
# 克隆项目到本地
git clone https://github.com/yourusername/arxiv-accelerator.git
cd arxiv-accelerator

# 推送代码到GitHub
git add .
git commit -m "Initial commit"
git push origin main
```

#### 2. 在Render创建服务
1. 访问 [Render控制台](https://dashboard.render.com/)
2. 点击 "New +" → "Web Service"
3. 连接您的GitHub仓库
4. 配置服务：
   - **Name**: `arxiv-accelerator`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python server.py`

#### 3. 配置环境变量
在Render服务设置中添加：
```
DOUBAO_API_KEY=your-doubao-api-key
DOUBAO_MODEL=your-doubao-model-endpoint
BACKUP_SECRET=your-backup-secret-key
```

#### 4. 配置自动备份
参考 [Wiki文档](./wiki/README.md) 中的部署配置说明。

### 方案二：本地部署

#### 1. 安装依赖
```bash
pip install -r requirements.txt
```

#### 2. 配置环境变量
```bash
cp env.example .env
# 编辑 .env 文件，填入您的API密钥
```

#### 3. 启动服务
```bash
python server.py
```

## 📚 详细文档

- **[GitHub Actions自动备份](./wiki/GITHUB_ACTIONS_SETUP.md)** - 推荐的自动备份方案

## 📁 项目结构

```
arxiv-accelerator/
├── 📄 核心文件
│   ├── server.py                      # Flask Web服务器
│   ├── arxiv_assistant.html           # 前端界面
│   ├── crawl_raw_info.py              # 论文爬取模块
│   ├── paper_analysis_processor.py    # 论文分析处理器
│   └── doubao_client.py               # 豆包API客户端
├── 🧪 测试脚本
│   ├── test_paper_analysis.py         # 论文分析测试
│   ├── test_paper_evaluation.py       # 论文评估测试
│   ├── test_doubao.py                 # API连接测试
│   ├── test_historical_dates.py       # 历史日期测试
│   └── demo_paper_analysis.py         # 分析功能演示
├── 📝 配置文件
│   ├── requirements.txt               # Python依赖
│   ├── start.sh                      # 启动脚本
│   ├── env.example                   # 环境变量模板
│   └── .gitignore                    # Git忽略文件
├── 📚 文档
│   └── wiki/                         # 详细文档
│       └── GITHUB_ACTIONS_SETUP.md   # GitHub Actions配置
├── 📋 提示词
│   └── prompt/
│       └── system_prompt.md          # AI分析提示词
└── 📊 数据目录
    └── log/                          # 论文数据和分析结果
        ├── YYYY-MM-DD-cs.CV-result.md    # 原始论文数据
        ├── YYYY-MM-DD-cs.CV-analysis.md  # 分析结果
        └── YYYY-MM-DD-cs.CV-log.txt      # 处理日志
```

## 🔧 API接口

### 主要API端点
- `POST /api/search_articles` - 搜索/爬取论文
- `POST /api/check_analysis_exists` - 检查分析结果
- `POST /api/analyze_papers` - 启动分析任务
- `GET /api/analysis_progress` - 获取分析进度 (SSE)
- `POST /api/get_analysis_results` - 获取分析结果
- `GET /api/available_dates` - 获取可用日期

## 📊 分析评分标准

### 核心特征 (每项2分)
- **multi_modal**: 涉及视觉且语言
- **large_scale**: 使用大规模模型
- **unified_framework**: 统一框架解决多任务
- **novel_paradigm**: 新颖训练范式

### 加分特征 (每项1分)
- **new_benchmark**: 提出新基准
- **sota**: 刷新SOTA
- **fusion_arch**: 融合架构创新
- **real_world_app**: 真实应用
- **reasoning_planning**: 推理/规划
- **scaling_modalities**: 扩展多模态
- **open_source**: 开源

### 评分公式
- **原始分**: 核心特征分 + 加分特征分
- **标准分**: min(10, 原始分)

## 💡 使用技巧

### 分析模式选择
- **仅前5篇**: 功能测试 (~2分钟)
- **仅前10篇**: 小规模验证 (~5分钟)
- **仅前20篇**: 中等规模测试 (~10分钟)
- **全部分析**: 完整分析 (~30-60分钟)

### 数据文件说明
- `*-result.md`: 原始爬取的论文数据
- `*-analysis.md`: AI分析后的结果数据
- `*-log.txt`: 详细的处理日志

### 智能缓存
系统会自动检测已有的分析结果，支持：
- 加载现有分析结果
- 增量分析（从短范围扩展到长范围）
- 避免重复分析

## 🛠️ 开发和测试

### 运行测试
```bash
# 测试论文分析功能
python test_paper_analysis.py

# 测试API连接
python test_doubao.py

# 测试历史日期爬取
python test_historical_dates.py

# 演示分析功能
python demo_paper_analysis.py
```

### 命令行使用
```bash
# 爬取指定日期论文
python crawl_raw_info.py

# 分析指定文件
python paper_analysis_processor.py log/2025-07-31-cs.CV-result.md --test 10
```

## 🐛 故障排除

### 常见问题

1. **服务器无法启动**
   - 检查端口8080是否被占用
   - 确认所有依赖已正确安装

2. **无法爬取论文**
   - 检查网络连接
   - 确认arXiv API可访问

3. **分析功能异常**
   - 检查豆包API密钥是否正确设置
   - 验证环境变量 `DOUBAO_API_KEY` 和 `DOUBAO_MODEL`
   - 查看`prompt/system_prompt.md`是否存在
   - 检查网络连接到豆包API服务

4. **前端显示问题**
   - 清除浏览器缓存
   - 检查浏览器控制台错误

### 调试方法
- 查看服务器控制台输出
- 检查`log/`目录下的日志文件
- 使用浏览器开发者工具检查网络请求

## 📈 技术架构

### 前端技术
- **HTML5**: 语义化标签
- **CSS3**: 响应式设计，现代UI
- **JavaScript**: 异步API调用，实时进度更新

### 后端技术
- **Flask**: 轻量级Web框架
- **Flask-CORS**: 跨域支持
- **豆包API**: AI论文分析
- **feedparser**: RSS数据解析
- **pandas**: 数据处理

### 架构特点
- **前后端分离**: JSON API通信
- **实时通信**: Server-Sent Events
- **多线程处理**: 后台分析任务
- **智能缓存**: 避免重复计算

## 🎯 使用场景

### 学术研究
- 快速筛选相关领域论文
- 识别高质量研究工作
- 跟踪最新技术趋势

### 技术调研
- 多模态大模型论文筛选
- SOTA方法快速定位
- 新技术范式发现

### 教学辅助
- 为学生推荐优质论文
- 构建课程阅读清单
- 研究方向指导

## 📝 贡献指南

欢迎提交Issue和Pull Request来改进项目！

### 开发建议
1. 遵循现有代码风格
2. 添加必要的测试用例
3. 更新相关文档
4. 确保向后兼容性

## 📄 许可证

MIT License - 仅供学习和研究使用

---

**Happy Researching! 🚀📚**