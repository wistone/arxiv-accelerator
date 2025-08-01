# 📚 GitHub Actions 自动备份配置操作手册

本手册将指导您完成通过GitHub Actions自动备份日志分析文件的完整配置过程。

## 🎯 方案概述

**完全免费的自动备份方案**：
- **触发器**: GitHub Actions (免费2000分钟/月)
- **执行环境**: Render服务器容器内
- **安全性**: HMAC密钥验证
- **频率**: 每1小时自动执行

**工作原理**：
```
GitHub Actions (定时触发) 
    ↓ HTTP POST请求
Render服务器 (/internal/backup API)
    ↓ 读取并返回分析文件内容
GitHub Actions (接收文件内容)
    ↓ 写入文件到仓库
GitHub Actions (Git提交推送)
    ↓ 完成备份
```

**关键优势**：
- **解决权限问题**: Render容器无需Git推送权限
- **数据安全**: 只传输必要的文件内容，不涉及Git凭据
- **容错性强**: GitHub Actions处理Git操作更稳定
- **监控完善**: 可以在GitHub查看所有备份历史

## 🛠️ 配置步骤

### 第一步：生成备份密钥

在您的本地计算机上生成一个安全的备份密钥：

#### 方法1：使用Python (推荐)
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

#### 方法2：使用OpenSSL
```bash
openssl rand -hex 32
```

#### 方法3：使用在线工具
访问：https://www.random.org/strings/ 生成64位随机字符串

**示例密钥**: `a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456`

⚠️ **重要**: 请妥善保存此密钥，后续步骤需要使用！

### 第二步：配置Render环境变量

1. **登录Render控制台**
   - 访问：https://dashboard.render.com/
   - 找到您的`arxiv-accelerator`服务

2. **添加环境变量**
   - 点击服务名称进入详情页
   - 选择 `Environment` 标签
   - 点击 `Add Environment Variable`
   - 添加以下变量：

   ```
   Key: BACKUP_SECRET
   Value: 您在第一步生成的密钥
   ```

3. **重启服务** (重要!)
   - 点击 `Manual Deploy` → `Deploy Latest Commit`
   - 等待服务重启完成

### 第三步：配置GitHub Secrets

1. **打开GitHub仓库**
   - 访问您的GitHub仓库页面
   - 例如：`https://github.com/yourusername/arxiv-accelerator`

2. **进入Settings页面**
   - 点击仓库页面右上角的 `Settings` 按钮
   - 在左侧菜单中找到 `Secrets and variables`
   - 点击 `Actions`

3. **添加Repository Secret**
   - 点击 `New repository secret` 按钮
   - 输入以下信息：

   ```
   Name: BACKUP_SECRET
   Secret: 您在第一步生成的密钥（与Render中的相同）
   ```

   - 点击 `Add secret` 保存

### 第四步：推送代码到GitHub

确保以下文件已推送到您的GitHub仓库：

```bash
# 检查文件是否存在
ls -la .github/workflows/auto-backup.yml
ls -la server.py
ls -la auto_commit_logs.py

# 提交并推送到GitHub
git add .github/workflows/auto-backup.yml
git add server.py
git commit -m "Add GitHub Actions auto backup feature"
git push origin main
```

### 第五步：验证配置

#### 5.1 手动测试GitHub Actions

1. **进入Actions页面**
   - 在GitHub仓库中点击 `Actions` 标签
   - 您应该能看到 `自动备份日志分析文件` 工作流

2. **手动触发测试**
   - 点击工作流名称
   - 点击右上角的 `Run workflow` 按钮
   - 选择分支 (通常是 `main`)
   - 可选启用调试模式
   - 点击 `Run workflow`

3. **查看执行结果**
   - 等待几分钟执行完成
   - 点击运行记录查看详细日志
   - 成功的话应该显示绿色的 ✅

#### 5.2 手动测试API端点

使用curl命令直接测试备份API：

```bash
# 生成签名 (替换为您的实际密钥)
BACKUP_SECRET="your-backup-secret-here"
SIGNATURE=$(echo -n "run" | openssl dgst -sha256 -hmac "$BACKUP_SECRET" | cut -d' ' -f2)

# 测试API
curl -X POST \
  -H "X-Backup-Sign: $SIGNATURE" \
  -H "Content-Type: application/json" \
  https://arxiv-accelerator.onrender.com/internal/backup
```

**预期成功响应**：
```json
{
  "ok": true,
  "message": "备份操作执行成功",
  "output": "...",
  "timestamp": "2025-08-01 12:00:00"
}
```

## ⏰ 定时配置

### 当前设置
- **频率**: 每2小时执行一次
- **时区**: UTC (国际标准时间)
- **对应北京时间**: UTC+8

### 修改执行频率

编辑 `.github/workflows/auto-backup.yml` 文件中的cron表达式：

```yaml
schedule:
  # 每2小时执行一次
  - cron: '0 */2 * * *'
  
  # 其他选项：
  # 每小时执行: '0 * * * *'
  # 每4小时执行: '0 */4 * * *'
  # 每天执行一次(北京时间上午8点): '0 0 * * *'
  # 工作日执行(北京时间上午10点): '0 2 * * 1-5'
```

## 🔍 监控与故障排查

### 查看执行日志

1. **GitHub Actions日志**
   - GitHub仓库 → Actions → 选择执行记录
   - 查看每个步骤的详细输出

2. **Render服务日志**
   - Render控制台 → 服务详情 → Logs
   - 查看备份API调用记录

### 常见问题解决

#### ❌ 问题1：签名验证失败 (HTTP 403)
**原因**: BACKUP_SECRET配置不一致
**解决**:
1. 检查Render环境变量中的BACKUP_SECRET
2. 检查GitHub Secrets中的BACKUP_SECRET
3. 确保两者完全一致
4. 重启Render服务

#### ❌ 问题2：API端点不存在 (HTTP 404)
**原因**: server.py中的API路由未部署
**解决**:
1. 确认server.py包含`/internal/backup`路由
2. 重新部署Render服务
3. 检查Render部署日志是否有错误

#### ❌ 问题3：服务器无响应 (HTTP 000)
**原因**: Render免费服务可能处于睡眠状态
**解决**:
1. GitHub Actions会自动尝试唤醒服务
2. 等待几分钟后重试
3. 可以先手动访问网站唤醒服务

#### ❌ 问题4：没有文件需要提交
**原因**: 所有分析文件都已是最新状态
**解决**:
1. 这是正常情况，不需要处理
2. 脚本会返回成功状态

### 手动测试命令

```bash
# 1. 测试API签名生成
echo -n "run" | openssl dgst -sha256 -hmac "your-secret-here" | cut -d' ' -f2

# 2. 测试备份API调用
curl -X POST \
  -H "X-Backup-Sign: your-signature-here" \
  -H "Content-Type: application/json" \
  -v \
  https://arxiv-accelerator.onrender.com/internal/backup

# 3. 查看API响应格式
curl -X POST \
  -H "X-Backup-Sign: your-signature-here" \
  -H "Content-Type: application/json" \
  -s \
  https://arxiv-accelerator.onrender.com/internal/backup | jq '.'
```

## 💰 成本分析

### GitHub Actions免费额度
- **免费分钟数**: 2,000分钟/月
- **单次执行时间**: ~30秒
- **每月执行次数**: 360次 (每2小时一次)
- **每月消耗**: ~180分钟
- **剩余额度**: 1,820分钟

### Render免费服务
- **睡眠时间**: 15分钟无访问后睡眠
- **唤醒时间**: ~30秒
- **备份执行时间**: ~10秒
- **月度影响**: 几乎无额外消耗

**结论**: 此方案每月消耗GitHub Actions额度约9%，完全在免费范围内。

## 🚀 高级配置

### 添加通知功能

可以添加Slack、Discord或邮件通知：

```yaml
# 在.github/workflows/auto-backup.yml中添加
- name: 发送成功通知
  if: success()
  uses: 8398a7/action-slack@v3
  with:
    status: success
    text: "✅ Arxiv日志备份成功完成"
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### 添加健康检查

```yaml
# 同时触发网站预热
- name: 网站预热
  run: |
    curl -s https://arxiv-accelerator.onrender.com/ > /dev/null
    echo "✅ 网站预热完成"
```

## ✅ 验证清单

完成配置后，请确认：

- [ ] BACKUP_SECRET已在Render环境变量中配置
- [ ] BACKUP_SECRET已在GitHub Secrets中配置  
- [ ] 两个密钥完全一致
- [ ] Render服务已重启
- [ ] GitHub Actions工作流文件已推送
- [ ] 手动触发测试成功
- [ ] API端点手动测试成功
- [ ] 查看执行日志无错误

## 📞 技术支持

如果遇到问题，请检查：

1. **GitHub Actions运行日志**
2. **Render服务器日志**  
3. **本操作手册的故障排查部分**

配置完成后，您的日志分析文件将每2小时自动备份，无需任何手动干预！🎉