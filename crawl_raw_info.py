import datetime as dt, pandas as pd, feedparser, re, time, requests
import os
import sys
import pytz
from contextlib import redirect_stdout, redirect_stderr

def crawl_arxiv_papers(target_date_str, category="cs.CV"):
    """
    爬取指定日期的arXiv论文，使用ET时区的14:00截止时间
    
    Args:
        target_date_str (str): 目标日期，格式为 'YYYY-MM-DD'
        category (str): 论文分类，支持 'cs.CV' 或 'cs.LG'
    
    Returns:
        bool: 是否成功
    """
    try:
        # 解析目标日期
        target_date = dt.datetime.strptime(target_date_str, '%Y-%m-%d').date()
        
        # 设置ET时区 (8月是夏令时，EDT = UTC-4)
        et_tz = pytz.timezone('US/Eastern')
        
        # 计算时间窗口：前一天20:00 ET 到目标日期20:00 ET
        # ArXiv在每天晚上8点(20:00)发布新论文，论文在前一天14:00截止后处理
        start_et = et_tz.localize(dt.datetime.combine(target_date - dt.timedelta(days=1), dt.time(20, 0)))
        end_et = et_tz.localize(dt.datetime.combine(target_date, dt.time(20, 0)))
        
        # 转换为UTC时间（arXiv API使用UTC）
        start_utc = start_et.astimezone(dt.timezone.utc)
        end_utc = end_et.astimezone(dt.timezone.utc)
        
        # 创建log文件夹
        log_folder = "log"
        os.makedirs(log_folder, exist_ok=True)
        
        # 设置日志文件路径
        log_file = os.path.join(log_folder, f"{target_date_str}-{category}-log.txt")
        result_file = os.path.join(log_folder, f"{target_date_str}-{category}-result.md")
        
        # 重定向输出到日志文件
        with open(log_file, 'w', encoding='utf-8') as f:
            with redirect_stdout(f), redirect_stderr(f):
                print(f"目标日期 (ET): {target_date}")
                print(f"论文分类: {category}")
                print(f"时间窗口 (ET): {start_et.strftime('%Y-%m-%d %H:%M:%S')} to {end_et.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"时间窗口 (UTC): {start_utc.strftime('%Y-%m-%d %H:%M:%S')} to {end_utc.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"当前UTC时间: {dt.datetime.now(dt.timezone.utc)}")
                print(f"当前本地时间: {dt.datetime.now()}")
                
                # 构建日期范围查询，使用UTC时间
                start_date_str = start_utc.strftime('%Y%m%d%H%M%S')
                end_date_str = end_utc.strftime('%Y%m%d%H%M%S')
                
                URL = ("http://export.arxiv.org/api/query?"
                       f"search_query=cat:{category}+AND+submittedDate:[{start_date_str}+TO+{end_date_str}]&"
                       "sortBy=submittedDate&sortOrder=descending&"
                       "max_results=2000")
                
                print(f"使用的URL: {URL}")
                response = requests.get(URL, timeout=30)
                feed = feedparser.parse(response.text)
                rows = []
                print(f"API返回了 {len(feed.entries)} 篇论文")

                for i, entry in enumerate(feed.entries):
                    pub_date = dt.datetime(*entry.published_parsed[:6]).date()
                    pub_datetime = dt.datetime(*entry.published_parsed[:6])
                    print(f"论文 {i+1}: 发布日期 {pub_date}, 发布时间 {pub_datetime}, 标题: {entry.title[:50]}...")
                
                print("\n现在检查所有论文...")                
                
                # 将提交时间在时间窗口内的论文收集起来
                for i, entry in enumerate(feed.entries):
                    pub_utc = dt.datetime(*entry.published_parsed[:6], tzinfo=dt.timezone.utc)
                    
                    # 检查论文是否在我们的时间窗口内
                    if start_utc <= pub_utc <= end_utc:
                        rows.append({
                            "No.":       len(rows) + 1,  # 从1开始的序号
                            "number_id": re.search(r'(\d+\.\d+)', entry.id).group(1),
                            "title":     entry.title.strip().replace('\n', ' '),
                            "authors":   ', '.join(a.name for a in entry.authors),
                            "abstract":  entry.summary.strip().replace('\n', ' '),
                            "link":      entry.link
                        })
                    else:
                        print(f"论文 {i+1}: 发布日期 {pub_date} 不在时间窗口内")
                
                print(f"最终筛选出 {len(rows)} 篇目标日期的论文")
                
                if rows:
                    df = pd.DataFrame(rows)
                    df.to_markdown(result_file, index=False)
                    print(f"结果已保存到: {result_file}")
                    return True
                else:
                    print("未找到任何论文")
                    # 即使没有找到论文，也创建一个空的结果文件
                    with open(result_file, 'w', encoding='utf-8') as f:
                        f.write("| No. | number_id | title | authors | abstract | link |\n")
                        f.write("|-----|-----------|-------|---------|----------|------|\n")
                    print(f"创建空结果文件: {result_file}")
                    return True
                    
    except Exception as e:
        print(f"发生错误: {str(e)}")
        return False

if __name__ == "__main__":
    import sys
    
    # 支持命令行参数：python crawl_raw_info.py [date] [category]
    if len(sys.argv) >= 3:
        target_date = sys.argv[1]
        category = sys.argv[2]
    elif len(sys.argv) >= 2:
        target_date = sys.argv[1]
        category = "cs.CV"
    else:
        # 如果没有参数，使用今天的日期和cs.CV分类
        target_date = dt.date.today().strftime('%Y-%m-%d')
        category = "cs.CV"
    
    success = crawl_arxiv_papers(target_date, category)
    print(f"爬取{'成功' if success else '失败'}")