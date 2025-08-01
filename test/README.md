# 🧪 测试脚本目录

本目录包含项目的所有测试脚本和演示脚本。

## 📋 脚本列表

### 核心功能测试

#### `test_paper_analysis.py`
- **功能**: 测试论文分析处理功能
- **用途**: 验证AI分析流程是否正常
- **特点**: 处理前10篇论文，显示详细分析日志
- **运行**: `python test/test_paper_analysis.py`

#### `test_doubao.py`
- **功能**: 测试豆包API连接
- **用途**: 验证API配置和网络连接
- **特点**: 简单的API调用测试
- **运行**: `python test/test_doubao.py`

#### `test_historical_dates.py`
- **功能**: 测试历史日期论文爬取
- **用途**: 验证不同日期的论文爬取功能
- **特点**: 测试多个历史日期
- **运行**: `python test/test_historical_dates.py`

#### `test_paper_evaluation.py`
- **功能**: 测试论文评估功能
- **用途**: 验证论文评分逻辑
- **特点**: 测试评分系统的准确性
- **运行**: `python test/test_paper_evaluation.py`

### 演示脚本

#### `demo_paper_analysis.py`
- **功能**: 演示论文分析功能
- **用途**: 展示分析结果格式和输出
- **特点**: 不调用实际API，生成示例结果
- **运行**: `python test/demo_paper_analysis.py`

## 🚀 快速测试

### 完整功能测试
```bash
# 1. 测试API连接
python test/test_doubao.py

# 2. 测试论文爬取
python test/test_historical_dates.py

# 3. 测试论文分析
python test/test_paper_analysis.py

# 4. 查看演示结果
python test/demo_paper_analysis.py
```

### 分步测试

#### 第一步：验证基础环境
```bash
# 检查依赖是否安装完整
python test/test_doubao.py
```

#### 第二步：测试数据获取
```bash
# 验证论文爬取功能
python test/test_historical_dates.py
```

#### 第三步：测试分析功能
```bash
# 验证AI分析流程
python test/test_paper_analysis.py
```

## 📊 测试结果说明

### 预期输出

#### test_doubao.py
```
✅ 豆包API连接成功
🔗 API响应正常
```

#### test_historical_dates.py
```
📅 测试日期: 2025-07-30
✅ cs.CV: 成功爬取 XX 篇论文
✅ cs.LG: 成功爬取 XX 篇论文
```

#### test_paper_analysis.py
```
📄 开始分析论文...
🔄 处理第 1/10 篇论文
✅ 分析完成，生成结果文件
```

### 常见问题

#### API连接失败
- 检查网络连接
- 验证API密钥配置
- 确认API服务可用

#### 论文爬取失败
- 检查arXiv服务状态
- 验证日期格式
- 确认网络访问权限

#### 分析功能异常
- 检查input文件是否存在
- 验证prompt文件路径
- 确认日志文件权限

## 🛠️ 开发测试

### 添加新测试
1. 在test目录创建新的测试文件
2. 命名规范：`test_功能名.py`
3. 包含必要的测试用例
4. 更新本README文档

### 测试最佳实践
- 使用小规模数据进行测试
- 包含错误处理验证
- 添加详细的日志输出
- 确保测试可重复运行

## 📈 持续集成

这些测试脚本可以用于：
- 本地开发验证
- 部署前检查
- 功能回归测试
- 性能基准测试

---

**Happy Testing! 🧪✨**