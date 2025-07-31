# arXiv 论文爬取工具

这是一个用于爬取arXiv计算机视觉(CS.CV)和机器学习(CS.LG)分类最新论文的Python工具。

## 功能特点

- ✅ 爬取指定日期的arXiv论文（支持cs.CV和cs.LG分类）
- ✅ 自动处理时区差异
- ✅ 智能URL构建：根据日期自动选择查询策略
- ✅ 支持历史日期查询（使用日期范围API）
- ✅ 生成带序号的markdown表格
- ✅ 日志重定向到指定文件夹
- ✅ 返回成功/失败状态
- ✅ 包含论文ID、标题、作者、摘要和链接

## 文件结构

```
arxiv-accelerator/
├── crawl-raw-info.py    # 主要的爬取函数
├── test_historical_dates.py  # 测试脚本
├── example_usage.py     # 使用示例
├── README.md           # 项目说明
└── log/                # 日志和结果文件夹
    ├── YYYY-MM-DD-cs.CV-log.txt      # 日志文件
    ├── YYYY-MM-DD-cs.CV-result.md    # 结果文件
    ├── YYYY-MM-DD-cs.LG-log.txt      # 日志文件
    └── YYYY-MM-DD-cs.LG-result.md    # 结果文件
```

## 安装依赖

```bash
pip install pandas feedparser requests tabulate
```

## 使用方法

### 1. 直接运行脚本

```bash
python crawl-raw-info.py
```

这会爬取今天的论文并保存到当前目录的 `cs_cv_today.md` 文件。

### 2. 作为函数使用

```python
import importlib.util

# 动态导入模块
spec = importlib.util.spec_from_file_location("crawl_raw_info", "crawl-raw-info.py")
crawl_raw_info = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crawl_raw_info)
crawl_arxiv_papers = crawl_raw_info.crawl_arxiv_papers

# 爬取指定日期的论文
success = crawl_arxiv_papers("2025-07-30", "cs.CV")  # 计算机视觉
if success:
    print("爬取成功！")
else:
    print("爬取失败！")

# 爬取机器学习论文
success = crawl_arxiv_papers("2025-07-30", "cs.LG")  # 机器学习
if success:
    print("爬取成功！")
else:
    print("爬取失败！")
```

### 3. 运行测试

```bash
python test_historical_dates.py
```

### 4. 查看使用示例

```bash
python example_usage.py
```

## 函数参数

### `crawl_arxiv_papers(target_date_str, category="cs.CV")`

**参数：**
- `target_date_str` (str): 目标日期，格式为 'YYYY-MM-DD'
- `category` (str): 论文分类，支持 'cs.CV'（计算机视觉）或 'cs.LG'（机器学习）

**返回值：**
- `bool`: 是否成功

**输出文件：**
- 日志文件：`log/YYYY-MM-DD-category-log.txt`
- 结果文件：`log/YYYY-MM-DD-category-result.md`

## 输出格式

生成的markdown表格包含以下列：

| 列名 | 说明 |
|------|------|
| No. | 序号（从1开始） |
| number_id | arXiv论文ID |
| title | 论文标题 |
| authors | 作者列表 |
| abstract | 论文摘要 |
| link | arXiv链接 |

## 示例输出

```markdown
| No. | number_id | title | authors | abstract | link |
|-----|-----------|-------|---------|----------|------|
| 1 | 2507.22885 | Viser: Imperative, Web-based 3D Visualization... | Brent Yi, Chung Min Kim... | We present Viser... | http://arxiv.org/abs/2507.22885v1 |
```

## 注意事项

1. **时区处理**：工具会自动处理UTC时区和本地时区的差异
2. **日期范围**：会包含目标日期和前一天的论文（考虑时区差异）
3. **智能查询**：
   - 对于最近日期（今天/昨天）：使用标准查询获取最新300篇论文
   - 对于历史日期：使用日期范围查询获取指定日期的论文
4. **网络请求**：需要网络连接访问arXiv API
5. **文件编码**：所有文件使用UTF-8编码

## 错误处理

- 无效日期格式会返回 `False`
- 网络错误会记录在日志中并返回 `False`
- 未找到论文时会返回 `False`

## 许可证

本项目仅供学习和研究使用。 