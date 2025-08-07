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
                print(f"当前UTC时间: {dt.datetime.now(dt.timezone.utc)}")
                print(f"当前本地时间: {dt.datetime.now()}")
                
                # 显示不同时区的时间，便于调试
                utc_now = dt.datetime.now(dt.timezone.utc)
                singapore_time = utc_now.astimezone(dt.timezone(dt.timedelta(hours=8)))
                us_eastern_time = utc_now.astimezone(dt.timezone(dt.timedelta(hours=-4)))  # EDT
                print(f"新加坡时间 (UTC+8): {singapore_time}")
                print(f"美国东部时间 (UTC-4): {us_eastern_time}")
                print(f"arXiv通常按美国东部时间发布论文")
                
                # 构建日期范围查询
                # 考虑时区差异：在新加坡时间下，arXiv的"今天"可能实际上是昨天
                # arXiv使用美国东部时间，新加坡比美国东部时间快12小时
                today_utc = dt.datetime.now(dt.timezone.utc).date()
                us_eastern_today = utc_now.astimezone(dt.timezone(dt.timedelta(hours=-4))).date()
                
                print(f"UTC今天: {today_utc}")
                print(f"美国东部今天: {us_eastern_today}")
                print(f"目标日期: {target_date}")
                
                # 如果目标日期是最近3天内，使用宽松的查询方式
                if target_date >= today_utc - dt.timedelta(days=2):
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
                    # print(f"论文 {i+1}: 发布日期 {pub_date}, 发布时间 {pub_datetime}, 标题: {entry.title[:50]}...")
                
                print("\n现在检查所有论文...")
                for i, entry in enumerate(feed.entries):
                    pub_date = dt.datetime(*entry.published_parsed[:6]).date()
                    pub_datetime = dt.datetime(*entry.published_parsed[:6])
                    print(f"论文 {i+1}: 发布日期 {pub_date}, 发布时间 {pub_datetime}, 标题: {entry.title[:50]}...")
                    
                    # 对于最近的日期，使用更宽松的匹配策略
                    if target_date >= today_utc - dt.timedelta(days=2):
                        # 考虑时区影响，匹配目标日期的前后一天
                        # 这是因为arXiv使用美国东部时间，而服务器可能在其他时区
                        date_tolerance = [
                            target_date - dt.timedelta(days=1),  # 前一天
                            target_date,                          # 目标日期
                            target_date + dt.timedelta(days=1)   # 后一天
                        ]
                        
                        if pub_date in date_tolerance:
                            print(f"找到目标日期的论文 (发布日期: {pub_date}): {entry.title[:50]}...")
                            
                            rows.append({
                                "No.":       len(rows) + 1,  # 从1开始的序号
                                "number_id": re.search(r'(\d+\.\d+)', entry.id).group(1),
                                "title":     entry.title.strip().replace('\n', ' '),
                                "authors":   ', '.join(a.name for a in entry.authors),
                                "abstract":  entry.summary.strip().replace('\n', ' '),
                                "link":      entry.link
                            })
                    else:
                        # 对于较早的日期，使用严格匹配
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
                        elif pub_date < target_date - dt.timedelta(days=1):
                            # 如果遇到比目标日期早两天的论文，停止搜索
                            print(f"发布日期 {pub_date} 比目标日期 {target_date} 早两天，停止搜索")
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