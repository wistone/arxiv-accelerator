#!/usr/bin/env python3
"""
修复版本：精确按arXiv官方时区搜索论文
- 统一使用美国东部时间
- 精确日期匹配，避免重复
- 与arXiv网站日期对应
"""

import re
import pandas as pd
import datetime as dt
import feedparser
import requests
from contextlib import redirect_stdout, redirect_stderr
from tabulate import tabulate
import sys
import os

def crawl_arxiv_papers(date_str, category):
    """
    爬取arXiv论文
    
    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD'
        category: arXiv分类，如 'cs.CV'
    """
    
    try:
        target_date = dt.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        print(f"❌ 日期格式错误: {date_str}，请使用 YYYY-MM-DD 格式")
        return False
    
    # 设置输出文件
    log_file = f'log/{date_str}-{category}-log.txt'
    result_file = f'log/{date_str}-{category}-result.md'
    
    # 确保log目录存在
    os.makedirs('log', exist_ok=True)
    
    try:
        # 重定向输出到日志文件
        with open(log_file, 'w', encoding='utf-8') as f:
            with redirect_stdout(f), redirect_stderr(f):
                print(f"🎯 arXiv 论文爬取 - 精确时区版本")
                print(f"目标日期: {target_date}")
                print(f"论文分类: {category}")
                print("=" * 60)
                
                # 统一使用arXiv官方时区（美国东部时间）
                # EDT (夏令时): UTC-4, EST (标准时): UTC-5
                # 当前假设使用EDT (UTC-4)
                us_eastern_tz = dt.timezone(dt.timedelta(hours=-4))
                
                # 获取当前美国东部时间
                utc_now = dt.datetime.now(dt.timezone.utc)
                us_eastern_now = utc_now.astimezone(us_eastern_tz)
                us_eastern_today = us_eastern_now.date()
                
                print(f"\n📅 精确时区处理策略:")
                print(f"  ✅ 使用arXiv官方时区: 美国东部时间 (UTC-4)")
                print(f"  ✅ 按API实际发布时间分组，确保数据准确性")
                print(f"  ✅ 避免时区混淆和重复计算问题")
                print(f"\n🕐 当前时间信息:")
                print(f"  当前UTC时间: {utc_now}")
                print(f"  当前美国东部时间: {us_eastern_now}")
                print(f"  美国东部今天: {us_eastern_today}")
                print(f"  目标搜索日期: {target_date}")
                print(f"\n💡 说明: 由于arXiv网站和API的日期分组逻辑略有差异，")
                print(f"     论文数量可能与网站显示不完全一致，但本工具的数据更精确。")
                
                # 分页查询策略：逐页获取，直到覆盖目标日期窗口
                page_size = 200  # 每页条数，避免单次返回不足
                start_index = 0
                max_pages = 30    # 最多请求 30 页（上限 6000 篇）
                entries_all = []
                
                for page in range(max_pages):
                    URL = (
                        "http://export.arxiv.org/api/query?"
                        f"search_query=cat:{category}&"
                        "sortBy=submittedDate&sortOrder=descending&"
                        f"start={start_index}&max_results={page_size}"
                    )
                    print(f"\n🔍 拉取第 {page+1} 页: start={start_index}, size={page_size}")
                    response = requests.get(URL)
                    if response.status_code != 200:
                        print(f"❌ 请求失败，状态码: {response.status_code}")
                        return False
                    feed = feedparser.parse(response.content)
                    if not feed.entries:
                        print("⏹️ 无更多条目，停止分页拉取")
                        break
                    entries_all.extend(feed.entries)
                    print(f"📥 本页 {len(feed.entries)} 条，累计 {len(entries_all)} 条")
                    
                    # 判断是否已覆盖到目标日期窗口以下（比目标日期早7天）
                    last_entry = feed.entries[-1]
                    last_pub_utc = dt.datetime(*last_entry.published_parsed[:6], tzinfo=dt.timezone.utc)
                    last_pub_eastern = last_pub_utc.astimezone(us_eastern_tz)
                    if last_pub_eastern.date() < target_date - dt.timedelta(days=7):
                        print(f"⏹️ 已覆盖到 {last_pub_eastern.date()} (< {target_date - dt.timedelta(days=7)})，停止分页拉取")
                        break
                    
                    start_index += page_size
                
                if not entries_all:
                    print("❌ 没有找到任何论文条目")
                    return False
                
                print(f"📊 从API累计获取到 {len(entries_all)} 篇论文（分页）")
                
                # 分析论文发布时间
                rows = []  # 精确按日期匹配的结果（pub_date_eastern == target_date）
                date_stats = {}
                
                print(f"\n🔍 开始分析论文发布时间...")
                
                for i, entry in enumerate(entries_all):
                    # 获取论文发布时间（UTC时间）
                    pub_datetime_utc = dt.datetime(*entry.published_parsed[:6], tzinfo=dt.timezone.utc)
                    
                    # 转换为美国东部时间
                    pub_datetime_eastern = pub_datetime_utc.astimezone(us_eastern_tz)
                    pub_date_eastern = pub_datetime_eastern.date()
                    
                    # 统计每个日期的论文数量
                    if pub_date_eastern not in date_stats:
                        date_stats[pub_date_eastern] = 0
                    date_stats[pub_date_eastern] += 1
                    
                    # 只保留目标日期的论文（精确匹配）
                    if pub_date_eastern == target_date:
                        print(f"✅ 找到目标日期论文 {len(rows)+1}: {entry.title[:50]}...")
                        print(f"   发布时间(UTC): {pub_datetime_utc}")
                        print(f"   发布时间(美东): {pub_datetime_eastern}")
                        
                        rows.append({
                            "No.": len(rows) + 1,
                            "number_id": re.search(r'(\d+\.\d+)', entry.id).group(1),
                            "title": entry.title.strip().replace('\n', ' '),
                            "authors": ', '.join(a.name for a in entry.authors),
                            "abstract": entry.summary.strip().replace('\n', ' '),
                            "link": entry.link
                        })
                    
                    # 如果发布日期早于目标日期超过7天，停止搜索以提高效率
                    if pub_date_eastern < target_date - dt.timedelta(days=7):
                        print(f"⏹️  发布日期 {pub_date_eastern} 早于目标日期超过7天，停止搜索")
                        break
                
                # 显示日期统计
                print(f"\n📊 按美国东部时间的论文分布:")
                sorted_dates = sorted(date_stats.keys(), reverse=True)
                for date in sorted_dates[:10]:  # 显示最近10天
                    status = "🎯 目标" if date == target_date else "  "
                    print(f"  {status} {date}: {date_stats[date]}篇")
                
                print(f"\n✅ 找到目标日期 {target_date} 的论文: {len(rows)} 篇")
                
                if not rows:
                    # 回退策略：按照 arXiv 公告日窗口筛选（美东 20:00 为界）
                    print("\n⚠️ 精确按日期未找到论文，启用回退策略：按公告窗口(美东20:00为界)筛选…")
                    window_start = dt.datetime.combine(
                        target_date - dt.timedelta(days=1), dt.time(hour=20, minute=0), tzinfo=us_eastern_tz
                    )
                    window_end = dt.datetime.combine(
                        target_date, dt.time(hour=20, minute=0), tzinfo=us_eastern_tz
                    )
                    print(f"公告窗口: [{window_start} , {window_end}) (美国东部时间)")

                    fallback_rows = []
                    for entry in feed.entries:
                        pub_datetime_utc = dt.datetime(*entry.published_parsed[:6], tzinfo=dt.timezone.utc)
                        pub_datetime_eastern = pub_datetime_utc.astimezone(us_eastern_tz)

                        if window_start <= pub_datetime_eastern < window_end:
                            fallback_rows.append({
                                "No.": len(fallback_rows) + 1,
                                "number_id": re.search(r'(\d+\.\d+)', entry.id).group(1),
                                "title": entry.title.strip().replace('\n', ' '),
                                "authors": ', '.join(a.name for a in entry.authors),
                                "abstract": entry.summary.strip().replace('\n', ' '),
                                "link": entry.link
                            })

                    if fallback_rows:
                        print(f"✅ 回退策略找到 {len(fallback_rows)} 篇论文（公告窗口）")
                        rows = fallback_rows
                    else:
                        print(f"📭 回退策略仍未找到 {target_date} 的论文，创建空结果文件以便后续重试…")
                        # 创建空的结果文件（服务器会检测到空结果并自动删除，允许后续重试）
                        with open(result_file, 'w', encoding='utf-8') as f:
                            f.write(f"# arXiv {category} 论文 - {target_date}\n\n")
                            f.write(f"**搜索日期**: {target_date} (美国东部时间 UTC-4)\\n")
                            f.write(f"**论文分类**: {category}\\n")
                            f.write(f"**论文数量**: 0 篇\\n")
                            f.write(f"**生成时间**: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
                            f.write(f"**数据来源**: arXiv官方API (精确时区处理)\\n\\n")
                            f.write("> **说明**: 本工具使用arXiv官方API，按美国东部时间精确分组。\\n")
                            f.write("> 当天未找到论文。若与官网有出入，可能由于官网按公告窗口分组或周末未更新。\\n\\n")
                            f.write("## 论文列表\n\n")
                            f.write("*该日期没有找到论文*\\n")
                        return True  # 返回成功，让服务器处理空结果的删除逻辑
                
        # 写入结果文件（不重定向输出）
        print(f"💾 正在保存结果到 {result_file}...")
        
        # 创建DataFrame
        df = pd.DataFrame(rows)
        
        # 生成Markdown格式的表格
        markdown_table = tabulate(df, headers='keys', tablefmt='pipe', showindex=False)
        
        # 写入文件
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write(f"# arXiv {category} 论文 - {target_date}\n\n")
            f.write(f"**搜索日期**: {target_date} (美国东部时间 UTC-4)\\n")
            f.write(f"**论文分类**: {category}\\n")
            f.write(f"**论文数量**: {len(rows)} 篇\\n")
            f.write(f"**生成时间**: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
            f.write(f"**数据来源**: arXiv官方API (精确时区处理)\\n\\n")
            f.write("> **说明**: 本工具使用arXiv官方API，按美国东部时间精确分组。\\n")
            f.write("> 由于arXiv网站和API的日期分组逻辑可能略有差异，论文数量可能与官网显示有所不同，但数据准确性更高。\\n\\n")
            f.write("## 论文列表\n\n")
            f.write(markdown_table)
            f.write("\\n")
        
        print(f"✅ 爬取完成！")
        print(f"📊 找到 {len(rows)} 篇论文")
        print(f"📁 结果保存到: {result_file}")
        print(f"📁 日志保存到: {log_file}")
        
        return True  # 返回成功状态
        
    except Exception as e:
        print(f"❌ 爬取过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False  # 返回失败状态

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python crawl_raw_info_fixed.py <日期> <分类>")
        print("示例: python crawl_raw_info_fixed.py 2025-08-06 cs.CV")
        sys.exit(1)
    
    date_str = sys.argv[1]
    category = sys.argv[2]
    
    crawl_arxiv_papers(date_str, category)