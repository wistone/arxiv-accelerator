# 🧪 测试指南

完整的测试流程，确保Arxiv智能分析助手的所有功能正常工作。

## 🚀 快速测试 (5分钟)

### 1. 环境检查
```bash
# 检查Python版本
python3 --version  # 应该 >= 3.8

# 检查Node.js版本 (可选)
node --version     # 应该 >= 16.0
npm --version      # 应该 >= 8.0
```

### 2. 依赖安装测试
```bash
# 安装Python依赖
pip install -r requirements.txt

# 检查关键依赖
python3 -c "import flask, pandas, requests; print('✅ Python依赖正常')"
```

### 3. API连接测试
```bash
# 复制环境变量模板
cp env.example .env

# 编辑.env文件，填入真实API密钥
# DOUBAO_API_KEY=your-api-key
# DOUBAO_MODEL=your-model-endpoint

# 测试API连接
python test/test_doubao.py
```

**期望输出:**
```
✅ API连接测试通过
✅ 模型响应正常
```

### 4. 启动服务测试
```bash
# 一键启动
./start.sh

# 或者分步启动
python server.py
```

**期望输出:**
```
🎨 前端模式: auto
⚛️  React构建可用: True/False
🚀 启动服务器...
📱 访问地址: http://localhost:8080
```

### 5. 界面访问测试
```bash
# 在浏览器中访问
open http://localhost:8080      # 主界面
open http://localhost:8080/classic  # 经典界面
```

## 🔍 详细功能测试

### 1. 前端界面测试

#### React界面测试
1. 访问 `http://localhost:8080`
2. 检查页面是否正常加载
3. 验证shadcn/ui组件显示正常
4. 测试响应式设计 (调整浏览器窗口大小)

#### 经典HTML界面测试
1. 访问 `http://localhost:8080/classic`
2. 检查原始界面是否正常显示
3. 验证所有按钮和控件可用

### 2. 论文搜索功能测试

#### 基础搜索测试
```bash
# 测试步骤:
# 1. 选择日期: 选择最近的工作日
# 2. 选择分类: cs.CV
# 3. 点击"搜索文章列表"
# 4. 等待搜索完成

# 期望结果:
# - 显示"成功加载 XX 篇文章"
# - 表格显示论文列表
# - 分析按钮变为可用状态
```

#### 不同分类测试
```bash
# 分别测试以下分类:
# - cs.CV (计算机视觉)
# - cs.LG (机器学习)  
# - cs.AI (人工智能)

# 每个分类都应该能正常搜索到论文
```

### 3. 智能分析功能测试

#### 小规模分析测试 (推荐用于日常测试)
```bash
# 测试步骤:
# 1. 先完成论文搜索
# 2. 点击"分析"按钮
# 3. 选择"仅前5篇"
# 4. 点击"开始分析"
# 5. 观察实时进度显示

# 期望结果:
# - 进度条正常更新
# - 显示当前处理的论文信息
# - 分析完成后显示结果表格
# - 结果包含筛选结果和评分
```

#### 完整分析测试 (耗时较长)
```bash
# 仅在确认功能正常后进行
# 选择"全部分析"会处理所有论文
# 预计耗时: 30-60分钟
```

### 4. API端点测试

#### 手动API测试
```bash
# 测试搜索API
curl -X POST http://localhost:8080/api/search_articles \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-08-02", "category": "cs.CV"}'

# 测试可用日期API
curl http://localhost:8080/api/available_dates

# 测试分析存在检查API
curl -X POST http://localhost:8080/api/check_analysis_exists \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-08-02", "category": "cs.CV"}'
```

#### 自动化API测试
```bash
# 运行内置测试脚本
python test/test_paper_analysis.py
python test/test_historical_dates.py
```

### 5. 双前端切换测试

#### 强制模式测试
```bash
# 测试仅HTML模式
./start.sh --frontend html
# 访问 http://localhost:8080 应显示经典界面

# 测试仅React模式 (需要先构建)
cd frontend && npm run build && cd ..
./start.sh --frontend react
# 访问 http://localhost:8080 应显示React界面
```

#### 自动模式测试
```bash
# 测试自动检测
./start.sh --frontend auto
# 系统应自动选择最佳前端界面
```

## 🔧 性能测试

### 1. 并发测试
```bash
# 安装测试工具
pip install locust

# 创建简单的负载测试
# 访问主页10次
for i in {1..10}; do
  curl -s http://localhost:8080 > /dev/null
  echo "请求 $i 完成"
done
```

### 2. 内存测试
```bash
# 监控内存使用
ps aux | grep python

# 使用htop监控 (如果安装了)
htop -p $(pgrep -f server.py)
```

### 3. 响应时间测试
```bash
# 测试API响应时间
time curl http://localhost:8080/api/available_dates

# 测试页面加载时间
time curl http://localhost:8080
```

## 🐛 错误场景测试

### 1. 网络错误测试
```bash
# 测试无效日期
curl -X POST http://localhost:8080/api/search_articles \
  -H "Content-Type: application/json" \
  -d '{"date": "invalid-date", "category": "cs.CV"}'

# 应返回400错误
```

### 2. API密钥错误测试
```bash
# 临时设置错误的API密钥
export DOUBAO_API_KEY="invalid-key"
python test/test_doubao.py

# 应显示API连接失败
```

### 3. 缺失依赖测试
```bash
# 卸载关键依赖
pip uninstall flask -y

# 尝试启动服务器
python server.py

# 应显示导入错误
# 重新安装: pip install flask
```

## 📊 测试结果验证

### 成功标准
- [ ] 所有Python依赖正常安装
- [ ] API连接测试通过
- [ ] 服务器正常启动 (端口8080)
- [ ] React界面正常加载
- [ ] 经典HTML界面正常加载
- [ ] 论文搜索功能正常
- [ ] 智能分析功能正常
- [ ] 实时进度显示正常
- [ ] 分析结果正确显示
- [ ] API端点响应正常
- [ ] 错误处理正常

### 性能基准
- 服务器启动时间: < 10秒
- 页面加载时间: < 3秒
- API响应时间: < 2秒
- 内存使用: < 500MB (空闲状态)
- 小规模分析 (5篇): < 3分钟

## 🚨 故障排除

### 常见测试失败原因

#### 1. 服务器启动失败
```bash
# 检查端口占用
lsof -i :8080
# 杀死占用进程: kill -9 <PID>

# 检查Python版本
python3 --version
# 确保 >= 3.8
```

#### 2. React界面无法加载
```bash
# 检查构建文件
ls -la frontend/dist/
# 如果不存在，运行: cd frontend && npm run build

# 检查Node.js环境
node --version
npm --version
```

#### 3. API连接失败
```bash
# 检查环境变量
cat .env
# 确认API密钥正确设置

# 检查网络连接
ping console.volcengine.com
```

#### 4. 前端依赖安装失败
```bash
# 清除npm缓存
cd frontend
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### 测试日志收集
```bash
# 保存测试日志
./start.sh 2>&1 | tee test_log.txt

# 检查错误日志
grep -i error test_log.txt
grep -i warning test_log.txt
```

## 🎯 自动化测试脚本

### 创建完整测试脚本
```bash
#!/bin/bash
# test_complete.sh

echo "🧪 开始完整功能测试..."

# 1. 环境检查
echo "1️⃣ 检查环境..."
python3 --version || exit 1

# 2. 依赖安装
echo "2️⃣ 安装依赖..."
pip install -r requirements.txt || exit 1

# 3. API测试
echo "3️⃣ 测试API连接..."
python test/test_doubao.py || exit 1

# 4. 前端构建
echo "4️⃣ 构建前端..."
cd frontend && npm install && npm run build && cd .. || echo "前端构建跳过"

# 5. 服务器测试
echo "5️⃣ 测试服务器启动..."
timeout 15s python server.py &
SERVER_PID=$!
sleep 10

# 6. API端点测试
echo "6️⃣ 测试API端点..."
curl -f http://localhost:8080/api/available_dates || echo "API测试失败"

# 7. 清理
kill $SERVER_PID 2>/dev/null

echo "✅ 测试完成！"
```

```bash
# 运行完整测试
chmod +x test_complete.sh
./test_complete.sh
```

---

**测试有问题？** 查看[故障排除指南](./DEPLOYMENT.md#故障排除)或提交[Issue](https://github.com/yourusername/arxiv-accelerator/issues) 🆘