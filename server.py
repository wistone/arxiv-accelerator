from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import re
import json
from datetime import datetime
from crawl_raw_info import crawl_arxiv_papers

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 设置静态文件目录
@app.route('/')
def index():
    return send_from_directory('.', 'arxiv_assistant.html')

@app.route('/api/search_articles', methods=['POST'])
def search_articles():
    try:
        data = request.get_json()
        selected_date = data.get('date')
        selected_category = data.get('category', 'cs.CV')  # 默认使用cs.CV
        
        if not selected_date:
            return jsonify({'error': '请选择日期'}), 400
        
        # 检查是否是今天
        today = datetime.now().date()
        selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
        is_today = selected_date_obj == today
        
        # 构建文件名
        date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
        filename = f"{date_obj.strftime('%Y-%m-%d')}-{selected_category}-result.md"
        filepath = os.path.join('log', filename)
        
        # 检查文件是否存在，如果不存在则尝试爬取
        if not os.path.exists(filepath):
            print(f"文件不存在: {filepath}，开始爬取数据...")
            
            # 调用爬虫函数
            success = crawl_arxiv_papers(selected_date, selected_category)
            
            if not success:
                return jsonify({'error': f'爬取 {selected_date} 的 {selected_category} 数据失败，请稍后重试'}), 500
            
            # 重新检查文件是否存在
            if not os.path.exists(filepath):
                return jsonify({'error': f'爬取完成但未找到生成的文件: {filepath}'}), 500
        
        # 读取并解析markdown文件
        articles = parse_markdown_file(filepath, selected_category)
        
        # 如果是今天且没有找到论文，返回特殊错误信息并删除log文件
        if is_today and len(articles) == 0:
            # 删除当天的log文件
            log_file = os.path.join('log', f"{date_obj.strftime('%Y-%m-%d')}-{selected_category}-log.txt")
            if os.path.exists(log_file):
                os.remove(log_file)
            if os.path.exists(filepath):
                os.remove(filepath)
            
            return jsonify({
                'error': f'今天没有新的{selected_category}论文被提交到arXiv。这是正常现象，因为论文提交和索引需要时间。'
            }), 404
        
        # 如果不是今天且没有论文，返回一般性错误
        if len(articles) == 0:
            return jsonify({'error': f'未找到 {selected_date} 的 {selected_category} 论文数据'}), 404
        
        return jsonify({
            'success': True,
            'articles': articles,
            'total': len(articles),
            'date': selected_date,
            'category': selected_category
        })
        
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

def parse_markdown_file(filepath, category_filter=''):
    """解析markdown文件并提取文章信息"""
    articles = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 分割表格行
        lines = content.strip().split('\n')
        
        # 跳过标题行和分隔行
        data_lines = []
        for line in lines:
            if line.startswith('|') and not line.startswith('|------'):
                data_lines.append(line)
        
        # 解析每一行数据
        for i, line in enumerate(data_lines[1:], 1):  # 跳过表头
            parts = [part.strip() for part in line.split('|')[1:-1]]  # 去掉首尾的 |
            
            if len(parts) >= 6:
                try:
                    number = int(parts[0])
                    number_id = parts[1]
                    title = parts[2]
                    authors = parts[3]
                    abstract = parts[4]
                    link = parts[5]
                    
                    # 不再进行类别筛选，因为文件已经是按类别生成的
                    
                    articles.append({
                        'number': number,
                        'id': number_id,
                        'title': title,
                        'authors': authors,
                        'abstract': abstract,
                        'link': link
                    })
                except (ValueError, IndexError):
                    continue
    
    except Exception as e:
        print(f"解析文件 {filepath} 时出错: {e}")
    
    return articles

@app.route('/api/analyze_articles', methods=['POST'])
def analyze_articles():
    try:
        data = request.get_json()
        selected_date = data.get('date')
        
        if not selected_date:
            return jsonify({'error': '请选择日期'}), 400
        
        # 构建文件名
        date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
        filename = f"{date_obj.strftime('%Y-%m-%d')}-result.md"
        filepath = os.path.join('log', filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': f'未找到 {selected_date} 的数据文件'}), 404
        
        # 读取文章进行简单分析
        articles = parse_markdown_file(filepath)
        
        # 简单的分析逻辑
        analysis = analyze_articles_data(articles)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'total_articles': len(articles)
        })
        
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

def analyze_articles_data(articles):
    """分析文章数据"""
    if not articles:
        return {
            'top_keywords': [],
            'research_areas': [],
            'summary': '没有找到文章数据'
        }
    
    # 提取关键词（简单的实现）
    all_text = ' '.join([article['title'] + ' ' + article['abstract'] for article in articles])
    
    # 常见的研究领域关键词
    keywords = {
        'computer vision': ['vision', 'image', 'detection', 'segmentation', 'recognition'],
        'machine learning': ['learning', 'neural', 'network', 'model', 'training'],
        'deep learning': ['deep', 'neural', 'transformer', 'attention'],
        'robotics': ['robot', 'control', 'navigation', 'manipulation'],
        'natural language processing': ['language', 'text', 'nlp', 'translation'],
        'audio processing': ['audio', 'speech', 'sound', 'acoustic']
    }
    
    # 统计关键词出现次数
    keyword_counts = {}
    for area, area_keywords in keywords.items():
        count = sum(1 for keyword in area_keywords if keyword.lower() in all_text.lower())
        if count > 0:
            keyword_counts[area] = count
    
    # 排序获取热门领域
    top_areas = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    
    # 提取常见词汇
    words = re.findall(r'\b\w+\b', all_text.lower())
    word_freq = {}
    for word in words:
        if len(word) > 3 and word not in ['the', 'and', 'for', 'with', 'this', 'that', 'from', 'have', 'been', 'they', 'their']:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        'top_keywords': [word for word, count in top_keywords],
        'research_areas': [area for area, count in top_areas],
        'summary': f'分析了 {len(articles)} 篇文章，主要研究方向包括：{", ".join([area for area, count in top_areas])}。热门关键词：{", ".join([word for word, count in top_keywords[:5]])}。'
    }

@app.route('/api/available_dates', methods=['GET'])
def get_available_dates():
    """获取可用的日期列表"""
    try:
        log_dir = 'log'
        if not os.path.exists(log_dir):
            return jsonify({'dates': []})
        
        dates = []
        for filename in os.listdir(log_dir):
            if filename.endswith('-result.md'):
                # 提取日期部分
                date_part = filename.replace('-result.md', '')
                try:
                    # 验证日期格式
                    datetime.strptime(date_part, '%Y-%m-%d')
                    dates.append(date_part)
                except ValueError:
                    continue
        
        # 按日期排序
        dates.sort(reverse=True)
        
        return jsonify({'dates': dates})
        
    except Exception as e:
        return jsonify({'error': f'获取日期列表失败: {str(e)}'}), 500

if __name__ == '__main__':
    print("启动Arxiv文章初筛小助手服务器...")
    print("访问地址: http://localhost:8080")
    app.run(debug=True, host='0.0.0.0', port=8080) 