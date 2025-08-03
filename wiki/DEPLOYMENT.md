# 🚀 部署指南

Arxiv智能分析助手支持多种部署方式，包括本地开发、Render云部署等。

## 📋 部署前准备

### 必需的环境变量
```bash
DOUBAO_API_KEY=your-doubao-api-key
DOUBAO_MODEL=your-doubao-model-endpoint
BACKUP_SECRET=your-backup-secret-key  # 可选，用于自动备份
```

### 系统要求
- **Python**: 3.8+
- **Node.js**: 16+ (可选，仅React前端需要)
- **内存**: 512MB+ (建议1GB+)

## 🏠 本地部署

### 方案1: 一键启动 (推荐)
```bash
# 克隆项目
git clone <your-repo-url>
cd arxiv-accelerator

# 配置环境变量
cp env.example .env
# 编辑.env文件，填入API密钥

# 一键启动
./start.sh
```

### 方案2: 分步启动

#### 仅后端 + HTML界面
```bash
# 安装Python依赖
pip install -r requirements.txt

# 启动后端
python server.py

# 访问: http://localhost:8080
```

#### 后端 + React开发模式
```bash
# 终端1: 启动后端
pip install -r requirements.txt
python server.py

# 终端2: 启动React前端
cd frontend
npm install
npm run dev

# 访问React界面: http://localhost:3000
# 访问HTML界面: http://localhost:8080/classic
```

#### 生产模式
```bash
# 构建React前端
cd frontend
npm install
npm run build
cd ..

# 启动后端 (自动服务React构建文件)
python server.py

# 访问: http://localhost:8080 (React界面)
# 经典界面: http://localhost:8080/classic
```

## ☁️ Render云部署

### 准备工作
1. 将代码推送到GitHub仓库
2. 注册[Render账户](https://render.com/)

### 部署步骤

#### 1. 创建Web Service
1. 访问 [Render控制台](https://dashboard.render.com/)
2. 点击 "New +" → "Web Service"
3. 连接GitHub仓库选择 `arxiv-accelerator`

#### 2. 配置构建设置
```yaml
Name: arxiv-accelerator
Environment: Python 3
Region: Oregon (US West) # 或其他就近区域

# 构建设置
Build Command: chmod +x start.sh && ./start.sh --build-only
Start Command: python server.py

# 高级设置
Auto-Deploy: Yes
```

#### 3. 环境变量配置
在Render服务设置中添加以下环境变量：
```bash
# 必需
DOUBAO_API_KEY=your-doubao-api-key
DOUBAO_MODEL=your-doubao-model-endpoint

# 可选
BACKUP_SECRET=your-backup-secret-key
FRONTEND_MODE=auto
```

#### 4. 部署验证
- 部署完成后访问提供的URL
- 确认React界面正常加载
- 测试论文搜索和分析功能
- 验证 `/classic` 路由可访问HTML界面

### Render构建优化

#### package.json for Render
如果需要在Render上自动安装Node.js依赖，可以在根目录创建：
```json
{
  "name": "arxiv-accelerator",
  "scripts": {
    "build": "cd frontend && npm install && npm run build",
    "start": "python server.py"
  },
  "engines": {
    "node": ">=16.0.0"
  }
}
```

#### 构建脚本增强
```bash
# 在start.sh中增加Render特定逻辑
if [ "$RENDER" = "true" ]; then
    echo "🔧 检测到Render环境，使用优化配置..."
    export FRONTEND_MODE="auto"
fi
```

## 🐳 Docker部署 (可选)

### Dockerfile
```dockerfile
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.9-alpine
WORKDIR /app

# 安装Python依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制后端代码
COPY *.py ./
COPY js/ ./js/
COPY css/ ./css/
COPY prompt/ ./prompt/
COPY *.html ./

# 复制React构建文件
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 创建必要目录
RUN mkdir -p log

EXPOSE 8080

CMD ["python", "server.py"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DOUBAO_API_KEY=${DOUBAO_API_KEY}
      - DOUBAO_MODEL=${DOUBAO_MODEL}
      - FRONTEND_MODE=auto
    volumes:
      - ./log:/app/log
```

## 🧪 测试部署

### 本地测试脚本
```bash
#!/bin/bash
echo "🧪 开始部署测试..."

# 测试API连接
python test/test_doubao.py
if [ $? -ne 0 ]; then
    echo "❌ API连接测试失败"
    exit 1
fi

# 测试前端构建
cd frontend
npm run build
if [ $? -ne 0 ]; then
    echo "❌ 前端构建失败"
    exit 1
fi
cd ..

# 测试服务器启动
timeout 10s python server.py &
PID=$!
sleep 5

# 测试API端点
curl -f http://localhost:8080/api/available_dates
if [ $? -eq 0 ]; then
    echo "✅ API端点测试通过"
else
    echo "❌ API端点测试失败"
fi

kill $PID
echo "✅ 部署测试完成"
```

### 部署验证清单
- [ ] 环境变量正确配置
- [ ] API连接测试通过
- [ ] 前端界面可访问
- [ ] 论文搜索功能正常
- [ ] 分析功能正常
- [ ] 静态资源加载正常
- [ ] 移动端响应式正常
- [ ] 错误处理正常

## 🔧 故障排除

### 常见问题

#### 1. React前端无法访问
```bash
# 检查构建文件
ls -la frontend/dist/

# 检查构建日志
cd frontend && npm run build

# 强制使用HTML界面
export FRONTEND_MODE=html
python server.py
```

#### 2. API调用失败
```bash
# 检查环境变量
echo $DOUBAO_API_KEY
echo $DOUBAO_MODEL

# 测试API连接
python test/test_doubao.py
```

#### 3. 依赖安装失败
```bash
# 更新pip
pip install --upgrade pip

# 清除缓存重新安装
pip cache purge
pip install -r requirements.txt
```

#### 4. 端口占用
```bash
# 检查端口占用
lsof -i :8080

# 使用不同端口
export PORT=8081
python server.py
```

## 📊 监控和维护

### 日志监控
```bash
# 实时查看服务器日志
tail -f log/*.log

# 查看错误日志
grep "ERROR" log/*.log
```

### 性能监控
- 内存使用: 建议512MB+
- CPU使用: 正常情况下 < 50%
- 磁盘空间: 预留1GB+用于日志存储

### 定期维护
- 清理过期日志文件
- 更新依赖包版本
- 备份重要数据
- 检查API密钥有效性

---

*部署有问题？查看[故障排除指南](./wiki/)或提交[Issue](https://github.com/yourusername/arxiv-accelerator/issues)* 🆘