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

# 导入重构后的服务层
from backend.services.analysis_service import analyze_paper
from backend.services.arxiv_service import import_arxiv_papers
from backend.services.affiliation_service import get_author_affiliations, clear_affiliation_cache
from backend.services.concurrent_analysis_service import get_concurrent_service, run_performance_comparison
from backend.clients.ai_client import DoubaoClient
from backend.db import repo as db_repo

# 向后兼容的别名
import_arxiv_papers_to_db = import_arxiv_papers

# 📦 简单的内存缓存（生产环境可用Redis）
_search_cache = {}
_cache_expiry = {}
CACHE_TTL = 300  # 5分钟缓存

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置静态文件路由，允许访问js目录下的文件
@app.route('/js/<path:filename>')
def serve_js_files(filename):
    return send_from_directory('frontend/js', filename)

# 配置静态文件路由，允许访问css目录下的文件
@app.route('/css/<path:filename>')
def serve_css_files(filename):
    return send_from_directory('frontend/css', filename)

# 全局变量用于跟踪分析进度
analysis_progress = {}
analysis_lock = threading.Lock()

# 设置静态文件目录
@app.route('/')
def index():
    return send_from_directory('./frontend', 'index.html')

@app.route('/intro.html')
@app.route('/intro')
def intro():
    return send_from_directory('./frontend', 'intro.html')

@app.route('/health')
def health_check():
    """健康检查端点，用于Render部署验证"""
    return jsonify({
        'status': 'healthy',
        'service': 'arxiv-accelerator',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/search_articles', methods=['POST'])
def search_articles():
    import time
    
    try:
        total_start = time.time()
        
        data = request.get_json()
        selected_date = data.get('date')
        selected_category = data.get('category', 'cs.CV')

        if not selected_date:
            return jsonify({'error': '请选择日期'}), 400

        print(f"🚀 [搜索性能] 开始搜索 | date={selected_date} category={selected_category}")

        # 🚀 新策略：基于时间的智能缓存（而非完全跳过API）
        import_time = 0
        stats = {'processed': 0, 'total_upsert': 0}
        current_time = time.time()
        
        # 检查最近是否已经导入过（短时间缓存）
        import_cache_key = f"import_{selected_date}_{selected_category}"
        should_skip_import = False
        
        if import_cache_key in _cache_expiry:
            if current_time < _cache_expiry[import_cache_key]:
                # 30分钟内已导入过，跳过ArXiv API
                should_skip_import = True
                print(f"⚡ [搜索性能] 30分钟内已导入，跳过ArXiv API调用")
        
        # 初始化变量
        import_time = 0
        stats = {'processed': 0, 'total_upsert': 0}
        skip_db_read = False
        
        if not should_skip_import:
            # 🚀 新策略：智能检查是否真的需要导入
            smart_check_start = time.time()
            
            # 1) 先获取ArXiv API数据（轻量级，只获取ID列表）
            arxiv_ids = db_repo.get_arxiv_ids_from_api(selected_date, selected_category)
            api_check_time = time.time() - smart_check_start
            print(f"⏱️  [搜索性能] ArXiv API ID检查完成，耗时: {api_check_time:.2f}s | ArXiv返回 {len(arxiv_ids)} 条")
            
            if not arxiv_ids:
                print(f"📭 [搜索性能] ArXiv API无数据，跳过导入")
                import_time = 0
            else:
                # 🚀 新优化：一体化检查+读取，避免两次DB查询
                unified_start = time.time()
                result = db_repo.smart_check_and_read(selected_date, selected_category, arxiv_ids)
                unified_time = time.time() - unified_start
                
                existing_ids = result.get('existing_ids', [])
                cached_articles = result.get('articles', [])
                
                print(f"⏱️  [搜索性能] 一体化查询完成，耗时: {unified_time:.2f}s | 该分类已有 {len(existing_ids)} 条")
                
                missing_ids = set(arxiv_ids) - set(existing_ids)
                
                # 🔧 修复：检查分类关联的完整性
                expected_linked_count = len(existing_ids)  # 已存在的论文数量
                actual_linked_count = len(cached_articles)  # 已建立分类关联的论文数量
                
                if not missing_ids and expected_linked_count == actual_linked_count:
                    # 所有数据都已存在且分类关联完整，跳过导入
                    print(f"⚡ [搜索性能] 所有数据已存在且分类关联完整({actual_linked_count}/{expected_linked_count})，跳过导入")
                    import_time = 0
                    stats = {'processed': len(existing_ids), 'total_upsert': 0}
                    articles = cached_articles
                    db_time = 0.0
                    skip_db_read = True
                elif not missing_ids:
                    # 论文已存在但分类关联不完整，需要补建关联
                    print(f"🔗 [搜索性能] 论文已存在但分类关联不完整({actual_linked_count}/{expected_linked_count})，补建关联")
                    skip_db_read = False
                    try:
                        import_start = time.time()
                        stats = import_arxiv_papers_to_db(selected_date, selected_category, limit=None, skip_if_exists=True)
                        import_time = time.time() - import_start
                        print(f"⏱️  [搜索性能] 补建关联完成，耗时: {import_time:.2f}s | processed={stats.get('processed', 0)} links={stats.get('total_link', 0)}")
                    except Exception as e:
                        import_time = time.time() - import_start if 'import_start' in locals() else 0
                        print(f"❌ [搜索性能] 补建关联失败，耗时: {import_time:.2f}s | 错误: {e}")
                        skip_db_read = False
                elif missing_ids:
                    # 导入缺失的数据
                    print(f"📥 [搜索性能] 发现 {len(missing_ids)} 条新数据，开始增量导入")
                    skip_db_read = False
                    try:
                        import_start = time.time()
                        stats = import_arxiv_papers_to_db(selected_date, selected_category, limit=None, skip_if_exists=True)
                        import_time = time.time() - import_start
                        print(f"⏱️  [搜索性能] 增量导入完成，耗时: {import_time:.2f}s | processed={stats.get('processed', 0)} upserted={stats.get('total_upsert', 0)}")
                    except Exception as e:
                        import_time = time.time() - import_start if 'import_start' in locals() else 0
                        print(f"❌ [搜索性能] 导入失败，耗时: {import_time:.2f}s | 错误: {e}")
                        skip_db_read = False
                
                # 设置导入缓存（30分钟）
                _cache_expiry[import_cache_key] = current_time + 1800

        # 2) 从数据库读取并返回给前端（保持原协议字段）
        # 🚀 缓存策略：检查缓存
        cache_key = f"{selected_date}_{selected_category}"
        
        if cache_key in _search_cache and cache_key in _cache_expiry:
            if current_time < _cache_expiry[cache_key]:
                print(f"⚡ [搜索性能] 缓存命中，跳过DB查询 | key={cache_key}")
                cached_data = _search_cache[cache_key]
                return jsonify({
                    'success': True,
                    'articles': cached_data['articles'],
                    'total': cached_data['total'],
                    'date': selected_date,
                    'category': selected_category,
                    'performance': {
                        'total_time': round(time.time() - total_start, 2),
                        'import_time': import_time,
                        'db_read_time': 0.0,  # 缓存命中
                        'cache_hit': True
                    },
                    'debug': cached_data.get('debug')
                })
        
        # 缓存未命中，查询数据库（除非已经有一体化查询的结果）
        try:
            if 'skip_db_read' in locals() and skip_db_read:
                # 使用一体化查询的结果，无需再次查询
                print(f"⚡ [搜索性能] 使用一体化查询结果，跳过额外DB查询")
                # articles 和 db_time 已在上面设置
            else:
                # 正常DB查询
                db_start = time.time()
                print(f"🔍 [搜索性能] 开始DB查询 | key={cache_key}")
                articles = db_repo.list_papers_by_date_category(selected_date, selected_category)
                db_time = time.time() - db_start
            # 额外调试日志：对比导入统计与DB返回数量
            imported = stats.get('processed') if isinstance(locals().get('stats'), dict) else None
            upserted = stats.get('total_upsert') if isinstance(locals().get('stats'), dict) else None
            print(f"⏱️  [搜索性能] DB读取完成，耗时: {db_time:.2f}s | 获取 {len(articles)} 条记录")
            print(f"DB读取 {len(articles)} 条 | date={selected_date} category={selected_category} | 导入processed={imported} upserted={upserted}")
            if imported is not None and len(articles) != imported:
                sample_ids = [a.get('id') for a in articles[:5]]
                print(f"数量不一致: processed={imported} vs db={len(articles)}。可能原因：1) PostgREST 分页导致截断（已改用 range() 强制扩大）；2) 日期窗口差异；3) 分类关联缺失。样本arxiv_id={sample_ids}")
            # 如果数量异常，向前端携带日志，便于可视化
            debug_log = {
                'processed': imported,
                'db_count': len(articles),
                'category': selected_category,
                'date': selected_date
            }
        except Exception as e:
            return jsonify({'error': f'从数据库读取失败: {e}'}), 500

        if len(articles) == 0:
            # 构建arXiv搜索URL供用户直接查看
            import datetime as dt
            import pytz
            target_date = dt.datetime.strptime(selected_date, "%Y-%m-%d").date()
            et_tz = pytz.timezone("US/Eastern")
            start_et = et_tz.localize(dt.datetime.combine(target_date - dt.timedelta(days=1), dt.time(20, 0)))
            end_et = et_tz.localize(dt.datetime.combine(target_date, dt.time(20, 0)))
            start_utc = start_et.astimezone(dt.timezone.utc)
            end_utc = end_et.astimezone(dt.timezone.utc)
            start_date_str = start_utc.strftime("%Y%m%d%H%M%S")
            end_date_str = end_utc.strftime("%Y%m%d%H%M%S")
            
            base = os.getenv("ARXIV_API_BASE", "https://export.arxiv.org/api/query")
            search_url = (
                f"{base}?"
                f"search_query=cat:{selected_category}+AND+submittedDate:[{start_date_str}+TO+{end_date_str}]&"
                "sortBy=submittedDate&sortOrder=descending&"
                "max_results=2000"
            )
            
            return jsonify({
                'error': f'当天没有新的{selected_category}论文被提交到arXiv，或数据尚未同步。请稍后重试。',
                'search_url': search_url
            }), 404

        # 🚀 更新缓存
        cache_data = {
            'articles': articles,
            'total': len(articles),
            'debug': debug_log if 'debug_log' in locals() else None
        }
        _search_cache[cache_key] = cache_data
        _cache_expiry[cache_key] = current_time + CACHE_TTL
        print(f"📦 [搜索性能] 缓存已更新 | key={cache_key} ttl={CACHE_TTL}s")

        total_time = time.time() - total_start
        print(f"🏁 [搜索性能] 总耗时: {total_time:.2f}s | 导入:{import_time:.2f}s + DB读取:{db_time:.2f}s")

        return jsonify({
            'success': True,
            'articles': articles,
            'total': len(articles),
            'date': selected_date,
            'category': selected_category,
            'performance': {
                'total_time': round(total_time, 2),
                'import_time': round(import_time, 2),
                'db_read_time': round(db_time, 2),
                'cache_hit': False
            },
            'debug': debug_log if 'debug_log' in locals() else None
        })

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

# def parse_markdown_file(filepath, category_filter=''):
#     """⚠️ 已废弃：解析markdown文件并提取文章信息（已改用数据库）"""

# @app.route('/api/analyze_articles', methods=['POST'])
# def analyze_articles():
#     """⚠️ 已废弃：基于Markdown文件的旧分析路由（已改用 /api/analyze_papers）"""

# def analyze_articles_data(articles):
#     """⚠️ 已废弃：简单关键词统计分析（已改用AI模型分析）"""

@app.route('/api/check_analysis_exists', methods=['POST'])
def check_analysis_exists():
    """检查数据库中分析完成的进度（按固定 prompt）。"""
    try:
        data = request.get_json()
        selected_date = data.get('date')
        selected_category = data.get('category', 'cs.CV')
        if not selected_date:
            return jsonify({'error': '请选择日期'}), 400

        # 固定 prompt：优先按名称 multi-modal-llm 找到 UUID
        prompt_id = db_repo.get_prompt_id_by_name('multi-modal-llm')
        if not prompt_id:
            return jsonify({'error': '缺少 prompt: multi-modal-llm'}), 500

        status = db_repo.get_analysis_status(selected_date, selected_category, prompt_id)
        resp = {
            'exists': status['completed'] > 0,
            'total': status['total'],
            'completed': status['completed'],
            'pending': status['pending'],
            'all_analyzed': status['completed'] >= status['total'] and status['total'] > 0
        }
        return jsonify(resp)
    except Exception as e:
        return jsonify({'error': f'检查进度失败: {str(e)}'}), 500

@app.route('/api/analyze_papers', methods=['POST'])
def analyze_papers():
    """启动论文分析（仅对未分析的 paper，补齐到指定数量）。"""
    try:
        data = request.get_json()
        selected_date = data.get('date')
        selected_category = data.get('category', 'cs.CV')
        range_type = data.get('range_type', 'full')

        if not selected_date:
            return jsonify({'error': '请选择日期'}), 400

        # prompt: multi-modal-llm
        prompt_id = db_repo.get_prompt_id_by_name('multi-modal-llm')
        if not prompt_id:
            return jsonify({'error': '缺少 prompt: multi-modal-llm'}), 500

        # 任务互斥：如已存在同日同类任务，直接返回当前进度
        task_id = f"{selected_date}-{selected_category}"
        with analysis_lock:
            if analysis_progress.get(task_id, {}).get('status') in ('starting','processing'):
                return jsonify({'success': True, 'task_id': task_id, 'message': '已有任务在运行，返回其进度'}), 200

        # 计算目标数量与补齐需求
        target_map = {'top5': 5, 'top10': 10, 'top20': 20}
        target_n = target_map.get(range_type)

        status = db_repo.get_analysis_status(selected_date, selected_category, prompt_id)
        if target_n is not None:
            if status['completed'] >= target_n:
                return jsonify({'success': True, 'task_id': task_id, 'message': '已达到目标数量，无需再次分析'}), 200
            need = target_n - status['completed']
        else:
            # full：对全部 pending
            need = status['pending']

        if need <= 0:
            return jsonify({'success': True, 'task_id': task_id, 'message': '无需分析'}), 200

        # 仅筛选未分析的论文，遵循顺序与搜索一致
        pending = db_repo.list_unanalyzed_papers(selected_date, selected_category, prompt_id, limit=need)
        if not pending:
            return jsonify({'success': True, 'task_id': task_id, 'message': '无待分析论文'}), 200

        # 启动后台分析任务（DB源），不再读取 markdown
        thread = threading.Thread(
            target=run_db_analysis_task,
            args=(task_id, pending, selected_date, selected_category, prompt_id)
        )
        thread.daemon = True
        thread.start()

        return jsonify({'success': True, 'task_id': task_id, 'message': f'启动分析，共 {len(pending)} 篇'})
    except Exception as e:
        return jsonify({'error': f'启动分析失败: {str(e)}'}), 500

@app.route('/api/analyze_papers_concurrent', methods=['POST'])
def analyze_papers_concurrent():
    """启动并发论文分析（5路并发）"""
    try:
        data = request.get_json()
        selected_date = data.get('date')
        selected_category = data.get('category', 'cs.CV')
        range_type = data.get('range_type', 'full')
        workers = data.get('workers', 5)  # 允许前端指定并发数

        if not selected_date:
            return jsonify({'error': '请选择日期'}), 400

        # prompt: multi-modal-llm
        prompt_id = db_repo.get_prompt_id_by_name('multi-modal-llm')
        if not prompt_id:
            return jsonify({'error': '缺少 prompt: multi-modal-llm'}), 500

        # 任务互斥：如已存在同日同类任务，直接返回当前进度
        task_id = f"{selected_date}-{selected_category}-concurrent"
        with analysis_lock:
            if analysis_progress.get(task_id, {}).get('status') in ('starting','processing'):
                return jsonify({'success': True, 'task_id': task_id, 'message': '已有并发任务在运行，返回其进度'}), 200

        # 计算目标数量与补齐需求
        target_map = {'top5': 5, 'top10': 10, 'top20': 20}
        target_n = target_map.get(range_type)

        status = db_repo.get_analysis_status(selected_date, selected_category, prompt_id)
        if target_n is not None:
            if status['completed'] >= target_n:
                return jsonify({'success': True, 'task_id': task_id, 'message': '已达到目标数量，无需再次分析'}), 200
            need = target_n - status['completed']
        else:
            # full：对全部 pending
            need = status['pending']

        if need <= 0:
            return jsonify({'success': True, 'task_id': task_id, 'message': '无需分析'}), 200

        # 仅筛选未分析的论文，遵循顺序与搜索一致
        pending = db_repo.list_unanalyzed_papers(selected_date, selected_category, prompt_id, limit=need)
        if not pending:
            return jsonify({'success': True, 'task_id': task_id, 'message': '无待分析论文'}), 200

        # 启动后台并发分析任务
        thread = threading.Thread(
            target=run_concurrent_analysis_task,
            args=(task_id, pending, selected_date, selected_category, prompt_id, workers)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True, 
            'task_id': task_id, 
            'message': f'并发分析任务已启动 ({workers}路并发)',
            'workers': workers,
            'total_papers': len(pending)
        }), 200
    except Exception as e:
        return jsonify({'error': f'启动并发分析失败: {str(e)}'}), 500

@app.route('/api/performance_comparison', methods=['POST'])
def performance_comparison():
    """运行性能对比测试（1路 vs 5路并发）"""
    try:
        data = request.get_json()
        selected_date = data.get('date')
        selected_category = data.get('category', 'cs.CV')
        test_count = data.get('test_count', 10)  # 默认测试10篇

        if not selected_date:
            return jsonify({'error': '请选择日期'}), 400

        # prompt: multi-modal-llm
        prompt_id = db_repo.get_prompt_id_by_name('multi-modal-llm')
        if not prompt_id:
            return jsonify({'error': '缺少 prompt: multi-modal-llm'}), 500

        # 获取待分析论文
        pending = db_repo.list_unanalyzed_papers(selected_date, selected_category, prompt_id, limit=test_count)
        if len(pending) < test_count:
            return jsonify({'error': f'可用论文数量不足，需要{test_count}篇，实际{len(pending)}篇'}), 400

        # 读取system prompt
        try:
            system_prompt = db_repo.get_system_prompt()
        except Exception as e:
            return jsonify({'error': f'获取系统提示词失败: {str(e)}'}), 500

        # 运行性能对比
        task_id = f"{selected_date}-{selected_category}-comparison"
        comparison_result = run_performance_comparison(
            task_id, pending, prompt_id, system_prompt, analysis_progress, test_count
        )

        return jsonify({
            'success': True,
            'comparison_result': comparison_result,
            'message': f'性能对比完成，测试了{test_count}篇论文'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'性能对比测试失败: {str(e)}'}), 500

# def auto_commit_analysis_file(output_file, task_id):
#     """
#     ⚠️  已废弃：自动提交分析结果文件到 GitHub
#     现在分析结果直接存储在数据库中，不再生成Markdown文件
#     """

# def run_analysis_task(task_id, input_file, selected_date, selected_category, test_count):
#     """后台运行分析任务
#     ⚠️  已废弃：功能：基于Markdown文件的旧分析任务
#     """

def run_db_analysis_task(task_id, pending_papers, selected_date, selected_category, prompt_id):
    """基于数据库待分析集合的后台任务。仅对未分析论文调用模型并写入DB。"""
    import sys
    try:
        with analysis_lock:
            analysis_progress[task_id] = {
                'current': 0,
                'total': len(pending_papers),
                'status': 'processing',
                'paper': None,
                'analysis_result': None
            }

        # 读取system prompt
        system_prompt = db_repo.get_system_prompt()

        # 初始化豆包客户端
        print(f"📡 初始化豆包客户端... 🔍 Task ID: {task_id}")
        client = DoubaoClient()
        print(f"✅ 豆包客户端初始化成功 - DB 源分析")

        success_count = 0
        error_count = 0

        for i, m in enumerate(pending_papers):
            paper = {
                'paper_id': m['paper_id'],
                'title': m.get('title',''),
                'abstract': m.get('abstract',''),
                'authors': m.get('authors',''),
                'link': m.get('link',''),
                'author_affiliation': m.get('author_affiliation','')
            }
            try:
                with analysis_lock:
                    analysis_progress[task_id]['current'] = i + 1
                    analysis_progress[task_id]['paper'] = paper
                    analysis_progress[task_id]['analysis_result'] = None

                start_time = time.time()
                result = analyze_paper(client, system_prompt, paper['title'], paper['abstract'])

                # 序列化结果并写库（幂等：唯一键保证）
                try:
                    import json as _json
                    ar = _json.loads(result)
                except Exception:
                    ar = { 'raw': result }

                db_repo.insert_analysis_result(
                    paper_id=paper['paper_id'],
                    prompt_id=prompt_id,
                    analysis_json=ar,
                    created_by=None,
                )

                # 若通过筛选且 paper 中机构信息为空，自动补充作者机构并写回 papers.author_affiliation
                try:
                    pass_filter = bool(ar.get('pass_filter'))
                    has_aff = bool(paper.get('author_affiliation'))
                    if pass_filter and not has_aff:
                        # 更新进度状态，告知前端正在获取机构信息
                        with analysis_lock:
                            analysis_progress[task_id]['status'] = 'fetching_affiliations'
                            analysis_progress[task_id]['paper'] = {
                                **paper,
                                'status': '正在获取作者机构...'
                            }
                        
                        # get_author_affiliations 已在文件顶部导入
                        
                        # 定义进度回调函数
                        def update_progress(message):
                            with analysis_lock:
                                analysis_progress[task_id]['paper'] = {
                                    **paper,
                                    'status': message
                                }
                        
                        affiliations = get_author_affiliations(paper['link'], progress_callback=update_progress)
                        if affiliations:
                            import json as _json
                            aff_json = _json.dumps(affiliations, ensure_ascii=False)
                            db_repo.update_paper_author_affiliation(paper['paper_id'], aff_json)
                        
                        # 恢复处理状态
                        with analysis_lock:
                            analysis_progress[task_id]['status'] = 'processing'
                            analysis_progress[task_id]['paper'] = paper
                except Exception as _aff_e:
                    print(f"获取/写入作者机构失败: {_aff_e}")
                    # 确保状态恢复
                    with analysis_lock:
                        analysis_progress[task_id]['status'] = 'processing'
                        analysis_progress[task_id]['paper'] = paper

                success_count += 1
                elapsed = time.time() - start_time
                print(f"✅ DB分析 {i+1}/{len(pending_papers)} 完成，耗时: {elapsed:.2f}s")

                with analysis_lock:
                    analysis_progress[task_id]['analysis_result'] = result
                    analysis_progress[task_id]['success_count'] = success_count
                    analysis_progress[task_id]['error_count'] = error_count
            except Exception as e:
                error_count += 1
                print(f"❌ DB分析异常: {e}")
                with analysis_lock:
                    analysis_progress[task_id]['error_count'] = error_count
                continue

        with analysis_lock:
            analysis_progress[task_id]['status'] = 'completed'
            analysis_progress[task_id]['final_success_count'] = success_count
            analysis_progress[task_id]['final_error_count'] = error_count
    except Exception as e:
        print(f"❌ run_db_analysis_task 失败: {e}")
        with analysis_lock:
            analysis_progress[task_id]['status'] = 'error'
            analysis_progress[task_id]['error'] = str(e)

def run_concurrent_analysis_task(task_id, pending_papers, selected_date, selected_category, prompt_id, workers=5):
    """运行并发分析任务"""
    import sys
    try:
        # 初始化进度跟踪
        with analysis_lock:
            analysis_progress[task_id] = {
                'current': 0,
                'total': len(pending_papers),
                'status': 'starting',
                'paper': None,
                'analysis_result': None,
                'workers': workers,
                'start_time': time.time()
            }

        # 读取system prompt
        system_prompt = db_repo.get_system_prompt()

        print(f"🚀 [并发分析] 启动任务 {task_id}，{workers}路并发，总计 {len(pending_papers)} 篇论文")

        # 获取并发分析服务
        concurrent_service = get_concurrent_service(workers=workers)
        
        # 定义进度更新回调
        def update_progress_callback(task_id, completed, total):
            # 这个回调在并发服务中已经更新了进度，这里可以做额外的日志
            pass

        # 执行并发分析
        result_stats = concurrent_service.analyze_papers_concurrent(
            task_id, pending_papers, prompt_id, system_prompt, 
            analysis_progress, update_progress_callback
        )

        # 更新最终状态
        with analysis_lock:
            analysis_progress[task_id].update({
                'status': 'completed',
                'final_stats': result_stats,
                'end_time': time.time()
            })

        print(f"🎉 [并发分析] 任务 {task_id} 完成！"
              f"成功:{result_stats['success_count']}, 失败:{result_stats['error_count']}, "
              f"总耗时:{result_stats['total_elapsed_time']:.1f}s")

    except Exception as e:
        print(f"❌ [并发分析] 任务 {task_id} 失败: {e}")
        with analysis_lock:
            analysis_progress[task_id]['status'] = 'error'
            analysis_progress[task_id]['error'] = str(e)
@app.route('/api/analysis_progress')
def analysis_progress_stream():
    """Server-Sent Events流，用于实时获取分析进度"""
    # 在请求上下文中获取参数
    date = request.args.get('date')
    category = request.args.get('category', 'cs.CV')
    task_type = request.args.get('type', 'serial')  # serial or concurrent
    if task_type == 'concurrent':
        task_id = f"{date}-{category}-concurrent"
    else:
        task_id = f"{date}-{category}"
    
    def generate(task_id):
        import sys
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
            
            # 减少调试信息的频率，只在状态或进度变化时记录到stderr
            if status != last_status or current != last_current:
                print(f"SSE Debug - task_id: {task_id}, status: {status}, current: {current}, loop: {loop_count}", file=sys.stderr)
            
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
                    'analysis_result': progress.get('analysis_result'),
                    'workers': progress.get('workers', 1),
                    'success_count': progress.get('success_count', 0),
                    'error_count': progress.get('error_count', 0),
                    'processing_papers': progress.get('processing_papers', []),
                    'last_completed_paper': progress.get('last_completed_paper')
                }
                
                print(f"SSE Sending data - current: {current}, status: {status}, has_result: {bool(data['analysis_result'])}", file=sys.stderr)
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
                print(f"SSE stream completed for task_id: {task_id}", file=sys.stderr)
                break
            elif status == 'error':
                error_data = {
                    'error': progress.get('error', '未知错误')
                }
                yield f"event: error\ndata: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                print(f"SSE stream error for task_id: {task_id}", file=sys.stderr)
                break
            
            time.sleep(1)  # 每秒检查一次
        
        # 如果循环超时，发送超时错误
        if loop_count >= max_loops:
            timeout_data = {'error': 'SSE stream timeout'}
            yield f"event: error\ndata: {json.dumps(timeout_data, ensure_ascii=False)}\n\n"
            print(f"SSE stream timeout for task_id: {task_id}", file=sys.stderr)
    
    return Response(generate(task_id), mimetype='text/event-stream')

@app.route('/api/fetch_affiliations', methods=['POST'])
def fetch_affiliations_api():
    try:
        data = request.get_json()
        paper_id = data.get('paper_id')
        link = data.get('link')
        if not paper_id or not link:
            return jsonify({'error': '缺少paper_id或link'}), 400
        
        print(f"[API] 开始获取作者机构: paper_id={paper_id}, link={link}")
        
        # get_author_affiliations 已在文件顶部导入
        aff = get_author_affiliations(link, use_cache=False)  # 强制不使用缓存
        
        if aff and len(aff) > 0:
            import json as _json
            aff_json = _json.dumps(aff, ensure_ascii=False)
            db_repo.update_paper_author_affiliation(int(paper_id), aff_json)
            print(f"[API] ✅ 成功获取并写入数据库: {len(aff)} 个机构")
            return jsonify({'success': True, 'affiliations': aff})
        else:
            print(f"[API] ⚠️ 未获取到机构信息")
            return jsonify({'success': False, 'error': '未获取到机构信息', 'affiliations': []}), 200
    except Exception as e:
        error_msg = str(e)
        print(f"[API] ❌ 获取机构失败: {error_msg}")
        
        # 对于文件过大等错误，返回具体错误信息
        if "过大" in error_msg or "限制" in error_msg:
            return jsonify({'success': False, 'error': f'文件过大，无法处理: {error_msg}', 'affiliations': []}), 200
        else:
            return jsonify({'error': error_msg}), 500

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
        
        # 直接从DB返回分析结果（优先且默认）
        try:
            prompt_id = db_repo.get_prompt_id_by_name("multi-modal-llm") or db_repo.get_prompt_id_by_name("system_default")
            if not prompt_id:
                return jsonify({'error': '缺少 prompt: multi-modal-llm'}), 500
            limit = 5 if selected_range == 'top5' else 10 if selected_range == 'top10' else 20 if selected_range == 'top20' else None
            time_filter = data.get('time_filter')  # 支持时间筛选参数
            articles = db_repo.get_analysis_results(date=selected_date, category=selected_category, prompt_id=prompt_id, limit=limit, time_filter=time_filter)
            if len(articles) > 0:
                return jsonify({
                    'success': True,
                    'articles': articles,
                    'total': len(articles),
                    'date': selected_date,
                    'category': selected_category,
                    'range_type': selected_range
                })
        except Exception as e:
            print(f"从DB读取分析结果失败: {e}")

        return jsonify({'success': True, 'articles': [], 'total': 0, 'date': selected_date, 'category': selected_category, 'range_type': selected_range})
        
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

# def parse_analysis_fail_file(filepath):
#     """⚠️ 已废弃：解析分析失败markdown文件（已改用数据库）"""

# def parse_analysis_markdown_file(filepath):
#     """⚠️ 已废弃：解析分析结果markdown文件（已改用数据库）"""

@app.route('/api/available_dates', methods=['GET'])
def get_available_dates():
    """获取可用的日期列表"""
    try:
        dates = db_repo.list_available_dates()
        return jsonify({'dates': dates})
        
    except Exception as e:
        return jsonify({'error': f'获取日期列表失败: {str(e)}'}), 500

@app.route('/api/clear_cache', methods=['POST'])
def clear_cache():
    """清理服务器端缓存（用于测试）"""
    global _search_cache, _cache_expiry
    
    data = request.get_json() or {}
    cache_type = data.get('type', 'all')
    
    if cache_type in ['all', 'search']:
        _search_cache.clear()
        search_keys = [k for k in _cache_expiry.keys() if not k.startswith('import_')]
        for key in search_keys:
            _cache_expiry.pop(key, None)
        print("🗑️  已清理搜索缓存")
    
    if cache_type in ['all', 'import']:
        import_keys = [k for k in _cache_expiry.keys() if k.startswith('import_')]
        for key in import_keys:
            _cache_expiry.pop(key, None)
        print("🗑️  已清理导入缓存")
    
    try:
        clear_affiliation_cache()
        print("🗑️  已清理机构信息缓存")
    except:
        pass
    
    return jsonify({
        'success': True, 
        'message': f'已清理{cache_type}缓存',
        'remaining_cache_keys': list(_cache_expiry.keys())
    })





if __name__ == '__main__':
    import sys
    
    # 强制刷新标准输出，确保在Render中能看到日志
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    
    # 正确处理Render的PORT环境变量
    port = int(os.getenv('PORT', 8080))  # Render注入PORT环境变量，本地默认8080
    host = '0.0.0.0'  # 必须绑定到所有接口，不能用localhost
    
    # 清空机构信息缓存
    try:
        clear_affiliation_cache()
    except:
        pass
    
    print("启动Arxiv文章初筛小助手服务器...")
    print(f"环境PORT变量: {os.getenv('PORT', 'None (使用默认8080)')}")
    print(f"实际使用端口: {port}")
    print(f"绑定地址: {host}")
    print(f"Python版本: {sys.version}")
    print(f"当前工作目录: {os.getcwd()}")
    
    # 在生产环境中禁用debug模式，但保持日志输出
    is_production = os.getenv('RENDER') is not None
    if is_production:
        print("🌐 检测到Render生产环境，优化日志配置")
        print(f"访问地址: https://你的render域名")
        app.run(debug=False, host=host, port=port)
    else:
        print("🖥️  本地开发环境")
        print(f"访问地址: http://localhost:{port}")
        app.run(debug=True, host=host, port=port) 