from flask import Flask, jsonify, request, send_from_directory, Response, abort
from flask_cors import CORS
import os
import re
import json
import time
import threading
import subprocess
import hmac
import hashlib
from datetime import datetime

# 加载环境变量文件
try:
    from dotenv import load_dotenv
    load_dotenv()  # 加载.env文件中的环境变量
except ImportError:
    print("⚠️  python-dotenv未安装，使用系统环境变量")

from crawl_raw_info import crawl_arxiv_papers
from paper_analysis_processor import analyze_paper, parse_markdown_table, generate_analysis_markdown, generate_analysis_fail_markdown
from doubao_client import DoubaoClient
from auto_commit_github_api import GitHubAutoCommit

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置静态文件路由，允许访问js目录下的文件
@app.route('/js/<path:filename>')
def serve_js_files(filename):
    return send_from_directory('js', filename)

# 配置静态文件路由，允许访问css目录下的文件
@app.route('/css/<path:filename>')
def serve_css_files(filename):
    return send_from_directory('css', filename)

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
        
        # 如果没有找到论文，返回错误信息并删除空文件，这样下次可以重新尝试
        if len(articles) == 0:
            # 删除空的log文件和结果文件
            log_file = os.path.join('log', f"{date_obj.strftime('%Y-%m-%d')}-{selected_category}-log.txt")
            if os.path.exists(log_file):
                os.remove(log_file)
                print(f"已删除空的日志文件: {log_file}")
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"已删除空的结果文件: {filepath}")
            
            return jsonify({
                'error': f'当天没有新的{selected_category}论文被提交到arXiv。这是正常现象，因为论文提交和索引需要时间。可能您选择了今天的日期，或者arXiv周末未更新。'
            }), 404
        
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
        
        # 检查所有可能的分析文件
        possible_files = [
            f"{selected_date}-{selected_category}-analysis.md",  # 全部分析
            f"{selected_date}-{selected_category}-analysis-top20.md",  # 前20篇
            f"{selected_date}-{selected_category}-analysis-top10.md",  # 前10篇
            f"{selected_date}-{selected_category}-analysis-top5.md",   # 前5篇
        ]
        
        existing_files = []
        for filename in possible_files:
            filepath = os.path.join('log', filename)
            if os.path.exists(filepath):
                # 根据文件名确定分析范围
                if 'top5' in filename:
                    range_type = 'top5'
                    range_desc = '前5篇'
                    test_count = 5
                elif 'top10' in filename:
                    range_type = 'top10'
                    range_desc = '前10篇'
                    test_count = 10
                elif 'top20' in filename:
                    range_type = 'top20'
                    range_desc = '前20篇'
                    test_count = 20
                else:
                    range_type = 'full'
                    range_desc = '全部分析'
                    test_count = None
                
                existing_files.append({
                    'filename': filename,
                    'filepath': filepath,
                    'range_type': range_type,
                    'range_desc': range_desc,
                    'test_count': test_count
                })
        
        # 按优先级排序：全部分析 > 前20篇 > 前10篇 > 前5篇
        existing_files.sort(key=lambda x: {
            'full': 0, 'top20': 1, 'top10': 2, 'top5': 3
        }[x['range_type']])
        
        # 确定可用的分析选项
        available_options = []
        if existing_files:
            best_file = existing_files[0]
            best_range = best_file['range_type']
            
            # 根据最佳文件确定可用的选项
            if best_range == 'full':
                # 有全部分析，只能选择全部分析
                available_options = ['full']
            elif best_range == 'top20':
                # 有前20篇分析，可以选择前20篇或重新生成全部分析
                available_options = ['top20', 'full']
            elif best_range == 'top10':
                # 有前10篇分析，可以选择前10篇、前20篇或重新生成全部分析
                available_options = ['top10', 'top20', 'full']
            elif best_range == 'top5':
                # 有前5篇分析，可以选择前5篇、前10篇、前20篇或重新生成全部分析
                available_options = ['top5', 'top10', 'top20', 'full']
        
        return jsonify({
            'exists': len(existing_files) > 0,
            'existing_files': existing_files,
            'best_file': existing_files[0] if existing_files else None,
            'available_options': available_options
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

def auto_commit_analysis_file(output_file, task_id):
    """
    自动提交分析结果文件到 GitHub
    
    Args:
        output_file: 生成的输出文件路径
        task_id: 任务ID，用于日志标识
    
    Returns:
        bool: 提交是否成功
    """
    try:
        print(f"🔄 开始自动提交文件到 GitHub: {output_file}")
        
        # 初始化 GitHub 提交工具
        committer = GitHubAutoCommit()
        
        # 提取文件名 
        file_name = os.path.basename(output_file)
        
        # 提交文件
        result = committer.commit_file_by_name(file_name)
        
        if result["success"]:
            print(f"✅ 成功提交文件到 GitHub: {file_name}")
            print(f"🔗 提交链接: {result.get('commit_url', 'N/A')}")
            return True
        else:
            error_msg = result.get('error', '未知错误')
            print(f"❌ GitHub 提交失败: {error_msg}")
            return False
    
    except Exception as e:
        print(f"⚠️  GitHub 自动提交异常 (任务: {task_id}): {e}")
        print("📝 提示: 检查 .env 文件中的 GITHUB_TOKEN 和 GITHUB_REPO 配置")
        return False

def run_analysis_task(task_id, input_file, selected_date, selected_category, test_count):
    """后台运行分析任务"""
    import sys
    
    # 强制刷新输出流，确保日志实时显示
    sys.stdout.flush()
    sys.stderr.flush()
    
    print(f"🚀 开始分析任务: {task_id}, 文件: {input_file}, 测试数量: {test_count}")
    print(f"🏷️  Instance 标识: {os.getenv('RENDER_INSTANCE_ID', 'local')}")
    print(f"⏰ 任务开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
        print(f"📡 初始化豆包客户端... 🔍 Task ID: {task_id} - Instance 开始处理")
        client = DoubaoClient()
        print(f"✅ 豆包客户端初始化成功 - 准备开始AI分析")
        
        # 处理每篇论文
        print(f"📄 开始处理 {len(papers)} 篇论文")
        
        # 添加论文分析统计
        success_count = 0
        error_count = 0
        
        # 初始化 GitHub 提交状态
        commit_success = False
        
        for i, paper in enumerate(papers):
            try:
                with analysis_lock:
                    analysis_progress[task_id]['current'] = i + 1
                    analysis_progress[task_id]['paper'] = paper
                    analysis_progress[task_id]['analysis_result'] = None
                
                # 调用论文分析
                print(f"🔍 分析第 {i+1}/{len(papers)} 篇论文: {paper['title'][:50]}...")
                sys.stdout.flush()  # 立即刷新输出
                start_time = time.time()
                
                analysis_result = analyze_paper(client, system_prompt, paper['title'], paper['abstract'])
                paper['analysis_result'] = analysis_result
                
                # 检查是否通过筛选，如果通过则获取作者机构信息
                paper['author_affiliation'] = ""  # 默认为空
                
                try:
                    # 解析分析结果JSON
                    import json
                    analysis_json = json.loads(analysis_result)
                    
                    # 如果通过筛选，调用豆包API获取机构信息
                    if analysis_json.get('pass_filter', False):
                        print(f"🏢 论文通过筛选，正在获取作者机构信息...")
                        from parse_author_affli_from_doubao import get_author_affiliations
                        
                        try:
                            affiliations = get_author_affiliations(paper['link'])
                            if affiliations:
                                # 将机构列表转换为JSON字符串存储
                                paper['author_affiliation'] = json.dumps(affiliations, ensure_ascii=False)
                                print(f"✅ 成功获取 {len(affiliations)} 个作者机构: {affiliations}")
                            else:
                                paper['author_affiliation'] = "[]"  # 空的JSON数组
                                print("⚠️ 未找到作者机构信息")
                        except Exception as affil_error:
                            import traceback
                            print(f"⚠️ 获取作者机构失败: {affil_error}")
                            print(f"🔍 详细错误信息: {traceback.format_exc()}")
                            paper['author_affiliation'] = ""  # 出错时保持为空
                    else:
                        print("⏭️ 论文未通过筛选，跳过机构信息获取")
                        
                except (json.JSONDecodeError, Exception) as e:
                    print(f"⚠️ 解析分析结果失败，跳过机构信息获取: {e}")
                    paper['author_affiliation'] = ""
                
                elapsed_time = time.time() - start_time
                
                # 检查分析结果是否包含错误
                if '"error"' in analysis_result:
                    error_count += 1
                    print(f"⚠️  第 {i+1} 篇论文分析有错误，耗时: {elapsed_time:.2f}秒")
                else:
                    success_count += 1
                    print(f"✅ 第 {i+1} 篇论文分析完成，耗时: {elapsed_time:.2f}秒")
                
                with analysis_lock:
                    analysis_progress[task_id]['analysis_result'] = analysis_result
                    analysis_progress[task_id]['success_count'] = success_count
                    analysis_progress[task_id]['error_count'] = error_count
                
                # 每10篇论文输出一次进度摘要
                if (i + 1) % 10 == 0 or i == len(papers) - 1:
                    print(f"📊 进度摘要: {i+1}/{len(papers)} 完成，成功: {success_count}，错误: {error_count}")
                
                # 简单延时以便前端能看到进度
                time.sleep(0.1)
                
            except Exception as e:
                error_count += 1
                print(f"❌ 第 {i+1} 篇论文处理异常: {e}")
                # 给出默认错误结果
                paper['analysis_result'] = f'{{"error": "Processing exception: {str(e)}"}}'
                
                with analysis_lock:
                    analysis_progress[task_id]['analysis_result'] = paper['analysis_result']
                    analysis_progress[task_id]['error_count'] = error_count
                
                # 继续处理下一篇论文
                continue
        
        # 检查是否有成功的分析结果
        if success_count == 0:
            # 如果没有任何成功的分析，生成失败文件
            if test_count:
                if test_count <= 5:
                    output_name = f"{selected_date}-{selected_category}-analysis-top5-fail.md"
                    completed_range_type = 'top5'
                elif test_count <= 10:
                    output_name = f"{selected_date}-{selected_category}-analysis-top10-fail.md"
                    completed_range_type = 'top10'
                elif test_count <= 20:
                    output_name = f"{selected_date}-{selected_category}-analysis-top20-fail.md"
                    completed_range_type = 'top20'
                else:
                    output_name = f"{selected_date}-{selected_category}-analysis-fail.md"
                    completed_range_type = 'full'
            else:
                output_name = f"{selected_date}-{selected_category}-analysis-fail.md"
                completed_range_type = 'full'
            
            output_file = os.path.join('log', output_name)
            generate_analysis_fail_markdown(papers, output_file, error_count)
            
            # 自动提交失败分析文件到 GitHub
            print(f"📤 准备提交失败分析文件到 GitHub...")
            commit_success = auto_commit_analysis_file(output_file, task_id)
            if commit_success:
                print(f"✅ 失败分析文件已成功提交到 GitHub")
            else:
                print(f"⚠️  失败分析文件提交到 GitHub 失败，但不影响本地分析结果")
            
            print(f"❌ 分析任务失败！总计: {len(papers)} 篇，成功: {success_count} 篇，错误: {error_count} 篇")
        else:
            # 如果有成功的分析，生成正常文件
            if test_count:
                if test_count <= 5:
                    output_name = f"{selected_date}-{selected_category}-analysis-top5.md"
                    completed_range_type = 'top5'
                elif test_count <= 10:
                    output_name = f"{selected_date}-{selected_category}-analysis-top10.md"
                    completed_range_type = 'top10'
                elif test_count <= 20:
                    output_name = f"{selected_date}-{selected_category}-analysis-top20.md"
                    completed_range_type = 'top20'
                else:
                    output_name = f"{selected_date}-{selected_category}-analysis.md"
                    completed_range_type = 'full'
            else:
                output_name = f"{selected_date}-{selected_category}-analysis.md"
                completed_range_type = 'full'
            
            output_file = os.path.join('log', output_name)
            generate_analysis_markdown(papers, output_file)
            
            # 自动提交成功分析文件到 GitHub
            print(f"📤 准备提交分析结果文件到 GitHub...")
            commit_success = auto_commit_analysis_file(output_file, task_id)
            if commit_success:
                print(f"✅ 分析结果文件已成功提交到 GitHub")
            else:
                print(f"⚠️  分析结果文件提交到 GitHub 失败，但不影响本地分析结果")
            
            print(f"🎊 分析任务完成！总计: {len(papers)} 篇，成功: {success_count} 篇，错误: {error_count} 篇")
        
        with analysis_lock:
            analysis_progress[task_id]['status'] = 'completed'
            analysis_progress[task_id]['output_file'] = output_file
            analysis_progress[task_id]['completed_range_type'] = completed_range_type
            analysis_progress[task_id]['final_success_count'] = success_count
            analysis_progress[task_id]['final_error_count'] = error_count
            # 记录 GitHub 提交状态
            analysis_progress[task_id]['github_commit_success'] = commit_success
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ 分析任务失败: {task_id}, 错误: {error_msg}")
        import traceback
        print("错误详情:")
        traceback.print_exc()
        
        with analysis_lock:
            analysis_progress[task_id]['status'] = 'error'
            analysis_progress[task_id]['error'] = error_msg

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
        max_loops = 1800  # 最多循环30分钟（1800秒）
        
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
                    'summary': f'分析完成！共处理 {progress.get("total", 0)} 篇论文',
                    'completed_range_type': progress.get('completed_range_type', 'full')
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
        selected_range = data.get('range_type', 'full') # 默认全部分析
        
        if not selected_date:
            return jsonify({'error': '请选择日期'}), 400
        
        # 根据选择的范围构建分析结果文件路径
        if selected_range == 'top5':
            filename = f"{selected_date}-{selected_category}-analysis-top5.md"
            fail_filename = f"{selected_date}-{selected_category}-analysis-top5-fail.md"
        elif selected_range == 'top10':
            filename = f"{selected_date}-{selected_category}-analysis-top10.md"
            fail_filename = f"{selected_date}-{selected_category}-analysis-top10-fail.md"
        elif selected_range == 'top20':
            filename = f"{selected_date}-{selected_category}-analysis-top20.md"
            fail_filename = f"{selected_date}-{selected_category}-analysis-top20-fail.md"
        else:
            filename = f"{selected_date}-{selected_category}-analysis.md"
            fail_filename = f"{selected_date}-{selected_category}-analysis-fail.md"
        
        filepath = os.path.join('log', filename)
        fail_filepath = os.path.join('log', fail_filename)
        
        # 先检查是否存在失败文件
        if os.path.exists(fail_filepath):
            # 解析失败文件
            fail_info = parse_analysis_fail_file(fail_filepath)
            return jsonify({
                'success': False,
                'is_analysis_failed': True,
                'fail_info': fail_info,
                'date': selected_date,
                'category': selected_category,
                'range_type': selected_range
            })
        
        if not os.path.exists(filepath):
            return jsonify({'error': f'未找到 {selected_date} 的 {selected_category} {selected_range} 分析结果文件'}), 404
        
        # 解析分析结果文件
        articles = parse_analysis_markdown_file(filepath)
        
        if len(articles) == 0:
            return jsonify({'error': f'分析结果文件为空'}), 404
        
        return jsonify({
            'success': True,
            'articles': articles,
            'total': len(articles),
            'date': selected_date,
            'category': selected_category,
            'range_type': selected_range
        })
        
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

def parse_analysis_fail_file(filepath):
    """解析分析失败markdown文件"""
    fail_info = {
        'total_papers': 0,
        'error_count': 0,
        'fail_time': '',
        'papers': []
    }
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取失败信息
        lines = content.split('\n')
        for line in lines:
            if '**总计论文数**:' in line:
                fail_info['total_papers'] = int(line.split(':')[1].strip())
            elif '**失败数**:' in line:
                fail_info['error_count'] = int(line.split(':')[1].strip())
            elif '**失败时间**:' in line:
                fail_info['fail_time'] = line.split(':', 1)[1].strip()
        
        # 解析论文列表（如果需要）
        data_lines = []
        for line in lines:
            if line.startswith('|') and not line.startswith('|------') and '错误信息' not in line:
                data_lines.append(line)
        
        # 解析论文数据行
        for line in data_lines:
            parts = [part.strip() for part in line.split('|')[1:-1]]  # 去掉首尾的 |
            if len(parts) >= 6:
                paper = {
                    'no': parts[0],
                    'error_msg': parts[1],
                    'title': parts[2],
                    'authors': parts[3],
                    'abstract': parts[4],
                    'link': parts[5]
                }
                fail_info['papers'].append(paper)
        
        return fail_info
        
    except Exception as e:
        print(f"解析失败文件出错: {e}")
        return fail_info

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
                    
                    # 处理新的 author_affiliation 字段（第7列）
                    author_affiliation = ""
                    if len(parts) >= 7:
                        author_affiliation = parts[6].replace('\\|', '|')
                    
                    articles.append({
                        'number': number,
                        'analysis_result': analysis_result,
                        'title': title,
                        'authors': authors,
                        'abstract': abstract,
                        'link': link,
                        'author_affiliation': author_affiliation
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
    import sys
    
    # 强制刷新标准输出，确保在Render中能看到日志
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    
    print("启动Arxiv文章初筛小助手服务器...")
    print("访问地址: http://localhost:8080")
    print(f"Python版本: {sys.version}")
    print(f"当前工作目录: {os.getcwd()}")
    
    # 在生产环境中禁用debug模式，但保持日志输出
    is_production = os.getenv('RENDER') is not None
    if is_production:
        print("🌐 检测到Render生产环境，优化日志配置")
        app.run(debug=False, host='0.0.0.0', port=8080)
    else:
        print("🖥️  本地开发环境")
        app.run(debug=True, host='0.0.0.0', port=8080) 