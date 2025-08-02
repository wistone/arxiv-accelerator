import datetime as dt, pandas as pd, feedparser, re, time, requests
import os
import sys
from contextlib import redirect_stdout, redirect_stderr

def crawl_arxiv_papers(target_date_str, category="cs.CV"):
    """
    爬取指定日期的arXiv论文
    
    Args:
        target_date_str (str): 目标日期，格式为 'YYYY-MM-DD'
        category (str): 论文分类，支持 'cs.CV' 或 'cs.LG'
    
    Returns:
        bool: 是否成功
    """
    try:
        # 解析目标日期
        target_date = dt.datetime.strptime(target_date_str, '%Y-%m-%d').date()
        yesterday = target_date - dt.timedelta(days=1)
        
        # 创建log文件夹
        log_folder = "log"
        os.makedirs(log_folder, exist_ok=True)
        
        # 设置日志文件路径
        log_file = os.path.join(log_folder, f"{target_date_str}-{category}-log.txt")
        result_file = os.path.join(log_folder, f"{target_date_str}-{category}-result.md")
        
        # 重定向输出到日志文件
        with open(log_file, 'w', encoding='utf-8') as f:
            with redirect_stdout(f), redirect_stderr(f):
                print(f"目标日期: {target_date}")
                print(f"论文分类: {category}")
                print(f"昨天的日期: {yesterday}")
                print(f"当前UTC时间: {dt.datetime.now(dt.UTC)}")
                print(f"当前本地时间: {dt.datetime.now()}")
                
                # 构建日期范围查询
                # 如果目标日期是今天或昨天，使用宽松的查询方式
                today = dt.date.today()
                if target_date >= today - dt.timedelta(days=1):
                    URL = ("http://export.arxiv.org/api/query?"
                           f"search_query=cat:{category}&"
                           "sortBy=submittedDate&sortOrder=descending&"
                           "max_results=1000")
                else:
                    # 对于更早的日期，使用严格的日期范围查询
                    # arXiv API使用UTC时间，格式为YYYYMMDDHHMMSS
                    start_date = target_date.strftime('%Y%m%d') + '000000'
                    end_date = target_date.strftime('%Y%m%d') + '235959'
                    
                    URL = ("http://export.arxiv.org/api/query?"
                           f"search_query=cat:{category}+AND+submittedDate:[{start_date}+TO+{end_date}]&"
                           "sortBy=submittedDate&sortOrder=descending&"
                           "max_results=1000") 
                
                print(f"使用的URL: {URL}")
                feed = feedparser.parse(requests.get(URL, timeout=30).text)
                rows = []
                print(f"获取到 {len(feed.entries)} 篇论文")
                
                for i, entry in enumerate(feed.entries):
                    pub_date = dt.datetime(*entry.published_parsed[:6]).date()
                    pub_datetime = dt.datetime(*entry.published_parsed[:6])
                    print(f"论文 {i+1}: 发布日期 {pub_date}, 发布时间 {pub_datetime}, 标题: {entry.title[:50]}...")
                
                print("\n现在检查所有论文...")
                for i, entry in enumerate(feed.entries):
                    pub_date = dt.datetime(*entry.published_parsed[:6]).date()
                    
                    # 只保留目标日期的论文
                    if pub_date == target_date:
                        print(f"找到目标日期的论文: {entry.title[:50]}...")
                        
                        rows.append({
                            "No.":       len(rows) + 1,  # 从1开始的序号
                            "number_id": re.search(r'(\d+\.\d+)', entry.id).group(1),
                            "title":     entry.title.strip().replace('\n', ' '),
                            "authors":   ', '.join(a.name for a in entry.authors),
                            "abstract":  entry.summary.strip().replace('\n', ' '),
                            "link":      entry.link
                        })
                    elif pub_date < target_date:
                        # 如果遇到早于目标日期的论文，说明已经过了目标日期，可以停止搜索
                        print(f"发布日期 {pub_date} 早于目标日期 {target_date}，停止搜索")
                        break
                
                print(f"找到 {len(rows)} 篇论文")
                
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