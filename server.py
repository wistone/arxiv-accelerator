from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
import os
import re
import json
import time
import threading
from datetime import datetime
from crawl_raw_info import crawl_arxiv_papers
from paper_analysis_processor import analyze_paper, parse_markdown_table, generate_analysis_markdown
from doubao_client import DoubaoClient

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局变量用于跟踪分析进度
analysis_progress = {}
analysis_lock = threading.Lock()

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

@app.route('/api/check_analysis_exists', methods=['POST'])
def check_analysis_exists():
    """检查分析结果文件是否已存在"""
    try:
        data = request.get_json()
        selected_date = data.get('date')
        selected_category = data.get('category', 'cs.CV')
        
        if not selected_date:
            return jsonify({'error': '请选择日期'}), 400
        
        # 构建分析结果文件路径
        filename = f"{selected_date}-{selected_category}-analysis.md"
        filepath = os.path.join('log', filename)
        
        exists = os.path.exists(filepath)
        
        return jsonify({
            'exists': exists,
            'filepath': filepath if exists else None
        })
        
    except Exception as e:
        return jsonify({'error': f'检查文件失败: {str(e)}'}), 500

@app.route('/api/analyze_papers', methods=['POST'])
def analyze_papers():
    """启动论文分析"""
    try:
        data = request.get_json()
        selected_date = data.get('date')
        selected_category = data.get('category', 'cs.CV')
        test_count = data.get('test_count')
        
        if not selected_date:
            return jsonify({'error': '请选择日期'}), 400
        
        # 构建输入文件路径
        filename = f"{selected_date}-{selected_category}-result.md"
        filepath = os.path.join('log', filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': f'未找到 {selected_date} 的 {selected_category} 数据文件'}), 404
        
        # 创建分析任务ID
        task_id = f"{selected_date}-{selected_category}"
        
        # 启动后台分析任务
        thread = threading.Thread(
            target=run_analysis_task,
            args=(task_id, filepath, selected_date, selected_category, test_count)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'task_id': task_id})
        
    except Exception as e:
        return jsonify({'error': f'启动分析失败: {str(e)}'}), 500

def run_analysis_task(task_id, input_file, selected_date, selected_category, test_count):
    """后台运行分析任务"""
    try:
        with analysis_lock:
            analysis_progress[task_id] = {
                'current': 0,
                'total': 0,
                'status': 'starting',
                'paper': None,
                'analysis_result': None
            }
        
        # 读取system prompt
        system_prompt_file = "prompt/system_prompt.md"
        if not os.path.exists(system_prompt_file):
            raise Exception("system_prompt.md文件不存在")
            
        with open(system_prompt_file, 'r', encoding='utf-8') as f:
            system_prompt = f.read().strip()
        
        # 解析原始markdown文件
        papers = parse_markdown_table(input_file)
        if not papers:
            raise Exception("无法解析markdown文件")
        
        # 如果指定了测试数量，只处理前N篇
        if test_count:
            papers = papers[:test_count]
        
        with analysis_lock:
            analysis_progress[task_id]['total'] = len(papers)
            analysis_progress[task_id]['status'] = 'processing'
        
        # 创建doubao客户端
        client = DoubaoClient()
        
        # 处理每篇论文
        for i, paper in enumerate(papers):
            with analysis_lock:
                analysis_progress[task_id]['current'] = i + 1
                analysis_progress[task_id]['paper'] = paper
                analysis_progress[task_id]['analysis_result'] = None
            
            # 调用论文分析
            analysis_result = analyze_paper(client, system_prompt, paper['title'], paper['abstract'])
            paper['analysis_result'] = analysis_result
            
            with analysis_lock:
                analysis_progress[task_id]['analysis_result'] = analysis_result
            
            # 简单延时以便前端能看到进度
            time.sleep(0.1)
        
        # 生成输出文件
        output_name = f"{selected_date}-{selected_category}-analysis.md"
        output_file = os.path.join('log', output_name)
        generate_analysis_markdown(papers, output_file)
        
        with analysis_lock:
            analysis_progress[task_id]['status'] = 'completed'
            analysis_progress[task_id]['output_file'] = output_file
        
    except Exception as e:
        with analysis_lock:
            analysis_progress[task_id]['status'] = 'error'
            analysis_progress[task_id]['error'] = str(e)

@app.route('/api/analysis_progress')
def analysis_progress_stream():
    """Server-Sent Events流，用于实时获取分析进度"""
    # 在请求上下文中获取参数
    date = request.args.get('date')
    category = request.args.get('category', 'cs.CV')
    task_id = f"{date}-{category}"
    
    def generate(task_id):
        last_current = -1
        last_status = None
        loop_count = 0
        max_loops = 300  # 最多循环5分钟（300秒）
        
        # 立即发送初始状态
        yield f"data: {json.dumps({'status': 'connecting', 'current': 0, 'total': 0}, ensure_ascii=False)}\n\n"
        
        while loop_count < max_loops:
            loop_count += 1
            
            with analysis_lock:
                progress = analysis_progress.get(task_id, {})
            
            status = progress.get('status', 'unknown')
            current = progress.get('current', 0)
            
            # 减少调试信息的频率，只在状态或进度变化时打印
            if status != last_status or current != last_current:
                print(f"SSE Debug - task_id: {task_id}, status: {status}, current: {current}, loop: {loop_count}")
            
            # 只在进度有变化时发送数据，或者是特殊状态
            should_send = (
                current != last_current or 
                status != last_status or
                status in ['completed', 'error', 'starting']
            )
            
            if should_send:
                data = {
                    'current': current,
                    'total': progress.get('total', 0),
                    'status': status,
                    'paper': progress.get('paper'),
                    'analysis_result': progress.get('analysis_result')
                }
                
                print(f"SSE Sending data - current: {current}, status: {status}, has_result: {bool(data['analysis_result'])}")
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                last_current = current
                last_status = status
            
            if status == 'completed':
                # 发送完成事件
                completion_data = {
                    'summary': f'分析完成！共处理 {progress.get("total", 0)} 篇论文'
                }
                yield f"event: complete\ndata: {json.dumps(completion_data, ensure_ascii=False)}\n\n"
                print(f"SSE stream completed for task_id: {task_id}")
                break
            elif status == 'error':
                error_data = {
                    'error': progress.get('error', '未知错误')
                }
                yield f"event: error\ndata: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                print(f"SSE stream error for task_id: {task_id}")
                break
            
            time.sleep(1)  # 每秒检查一次
        
        # 如果循环超时，发送超时错误
        if loop_count >= max_loops:
            timeout_data = {'error': 'SSE stream timeout'}
            yield f"event: error\ndata: {json.dumps(timeout_data, ensure_ascii=False)}\n\n"
            print(f"SSE stream timeout for task_id: {task_id}")
    
    return Response(generate(task_id), mimetype='text/event-stream')

@app.route('/api/get_analysis_results', methods=['POST'])
def get_analysis_results():
    """获取分析结果"""
    try:
        data = request.get_json()
        selected_date = data.get('date')
        selected_category = data.get('category', 'cs.CV')
        
        if not selected_date:
            return jsonify({'error': '请选择日期'}), 400
        
        # 构建分析结果文件路径
        filename = f"{selected_date}-{selected_category}-analysis.md"
        filepath = os.path.join('log', filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': f'未找到 {selected_date} 的 {selected_category} 分析结果文件'}), 404
        
        # 解析分析结果文件
        articles = parse_analysis_markdown_file(filepath)
        
        if len(articles) == 0:
            return jsonify({'error': f'分析结果文件为空'}), 404
        
        return jsonify({
            'success': True,
            'articles': articles,
            'total': len(articles),
            'date': selected_date,
            'category': selected_category
        })
        
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

def parse_analysis_markdown_file(filepath):
    """解析分析结果markdown文件"""
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
                    analysis_result = parts[1].replace('\\|', '|')  # 还原转义的管道符
                    title = parts[2].replace('\\|', '|')
                    authors = parts[3].replace('\\|', '|')
                    abstract = parts[4].replace('\\|', '|')
                    link = parts[5].replace('\\|', '|')
                    
                    articles.append({
                        'number': number,
                        'analysis_result': analysis_result,
                        'title': title,
                        'authors': authors,
                        'abstract': abstract,
                        'link': link
                    })
                except (ValueError, IndexError):
                    continue
    
    except Exception as e:
        print(f"解析分析结果文件 {filepath} 时出错: {e}")
    
    return articles

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