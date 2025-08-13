#!/usr/bin/env python3
"""
并发论文分析服务

提供多线程并发的论文分析功能，显著提升分析速度
"""

import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Callable

from backend.services.analysis_service import analyze_paper
from backend.services.affiliation_service import get_author_affiliations
from backend.clients.ai_client import DoubaoClient
from backend.db import repo as db_repo


class ConcurrentAnalysisService:
    """并发分析服务"""
    
    def __init__(self, max_workers: int = 5):
        """
        初始化并发分析服务
        
        Args:
            max_workers: 最大并发工作线程数
        """
        self.max_workers = max_workers
        self.progress_lock = threading.Lock()
        
    def analyze_papers_concurrent(
        self,
        task_id: str,
        pending_papers: List[Dict],
        prompt_id: str,
        system_prompt: str,
        progress_tracker: Dict[str, Any],
        update_progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        并发分析论文列表
        
        Args:
            task_id: 任务ID
            pending_papers: 待分析论文列表
            prompt_id: 提示词ID
            system_prompt: 系统提示词
            progress_tracker: 进度跟踪器
            update_progress_callback: 进度更新回调函数
            
        Returns:
            Dict: 分析结果统计
        """
        total_papers = len(pending_papers)
        completed_count = 0
        success_count = 0
        error_count = 0
        
        # 初始化进度
        with self.progress_lock:
            progress_tracker[task_id].update({
                'total': total_papers,
                'current': 0,
                'status': 'processing',
                'concurrent_workers': self.max_workers,
                'completed_papers': [],
                'processing_papers': []
            })
        
        print(f"🚀 [并发分析] 启动 {self.max_workers} 路并发分析，总计 {total_papers} 篇论文")
        
        def analyze_single_paper(paper_data: Dict) -> Dict[str, Any]:
            """分析单篇论文的工作函数"""
            thread_id = threading.current_thread().ident
            paper_id = paper_data['paper_id']
            start_time = time.time()
            
            # 更新正在处理的论文列表
            with self.progress_lock:
                progress_tracker[task_id]['processing_papers'].append({
                    'paper_id': paper_id,
                    'title': paper_data.get('title', '')[:50] + '...',
                    'thread_id': thread_id,
                    'start_time': start_time
                })
            
            try:
                # 创建独立的AI客户端实例（线程安全）
                client = DoubaoClient()
                
                # 1. 执行论文分析
                print(f"🔍 [线程-{thread_id}] 开始分析论文: {paper_data.get('title', '')[:30]}...")
                
                result = analyze_paper(
                    client, 
                    system_prompt, 
                    paper_data.get('title', ''), 
                    paper_data.get('abstract', '')
                )
                
                # 解析分析结果
                try:
                    analysis_result = json.loads(result)
                except Exception:
                    analysis_result = {'raw': result}
                
                # 2. 保存分析结果到数据库
                db_repo.insert_analysis_result(
                    paper_id=paper_id,
                    prompt_id=prompt_id,
                    analysis_json=analysis_result,
                    created_by=None,
                )
                
                # 3. 如果通过筛选且缺少机构信息，获取作者机构
                pass_filter = bool(analysis_result.get('pass_filter', False))
                has_affiliation = bool(paper_data.get('author_affiliation'))
                
                if pass_filter and not has_affiliation and paper_data.get('link'):
                    print(f"🏛️ [线程-{thread_id}] 论文通过筛选，开始获取机构信息...")
                    
                    try:
                        # 定义进度回调
                        def affiliation_progress(message):
                            # 这里可以更新具体论文的机构获取进度
                            pass
                        
                        affiliations = get_author_affiliations(
                            paper_data['link'], 
                            progress_callback=affiliation_progress
                        )
                        
                        if affiliations:
                            aff_json = json.dumps(affiliations, ensure_ascii=False)
                            db_repo.update_paper_author_affiliation(paper_id, aff_json)
                            print(f"✅ [线程-{thread_id}] 机构信息更新完成: {len(affiliations)} 个机构")
                        
                    except Exception as aff_error:
                        print(f"⚠️ [线程-{thread_id}] 机构信息获取失败: {aff_error}")
                
                elapsed_time = time.time() - start_time
                print(f"✅ [线程-{thread_id}] 论文分析完成，耗时: {elapsed_time:.2f}s")
                
                return {
                    'paper_id': paper_id,
                    'success': True,
                    'result': analysis_result,
                    'elapsed_time': elapsed_time,
                    'thread_id': thread_id,
                    'pass_filter': pass_filter,
                    'has_affiliation': not has_affiliation and pass_filter,
                    # 只保留标题用于显示
                    'title': paper_data.get('title', '')
                }
                
            except Exception as e:
                elapsed_time = time.time() - start_time
                print(f"❌ [线程-{thread_id}] 论文分析失败: {e}, 耗时: {elapsed_time:.2f}s")
                
                return {
                    'paper_id': paper_id,
                    'success': False,
                    'error': str(e),
                    'elapsed_time': elapsed_time,
                    'thread_id': thread_id,
                    # 只保留标题用于显示
                    'title': paper_data.get('title', '')
                }
            
            finally:
                # 从正在处理列表中移除
                with self.progress_lock:
                    progress_tracker[task_id]['processing_papers'] = [
                        p for p in progress_tracker[task_id]['processing_papers'] 
                        if p['paper_id'] != paper_id
                    ]
        
        # 使用线程池执行并发分析
        overall_start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_paper = {
                executor.submit(analyze_single_paper, paper): paper 
                for paper in pending_papers
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_paper):
                paper = future_to_paper[future]
                completed_count += 1
                
                try:
                    result = future.result()
                    
                    if result['success']:
                        success_count += 1
                    else:
                        error_count += 1
                    
                    # 更新进度
                    with self.progress_lock:
                        progress_tracker[task_id].update({
                            'current': completed_count,
                            'success_count': success_count,
                            'error_count': error_count,
                            'last_completed_paper': {
                                'title': paper.get('title', '')[:50],
                                'success': result['success'],
                                'elapsed_time': result['elapsed_time'],
                                'thread_id': result.get('thread_id')
                            }
                        })
                        
                        # 添加到已完成列表
                        progress_tracker[task_id]['completed_papers'].append(result)
                    
                    # 调用进度更新回调
                    if update_progress_callback:
                        update_progress_callback(task_id, completed_count, total_papers)
                        
                    print(f"📊 [并发分析] 进度: {completed_count}/{total_papers} "
                          f"(成功:{success_count}, 失败:{error_count})")
                    
                except Exception as e:
                    error_count += 1
                    print(f"❌ [并发分析] 任务结果处理失败: {e}")
        
        # 分析完成
        total_elapsed_time = time.time() - overall_start_time
        
        final_stats = {
            'total_papers': total_papers,
            'success_count': success_count,
            'error_count': error_count,
            'total_elapsed_time': total_elapsed_time,
            'average_time_per_paper': total_elapsed_time / total_papers if total_papers > 0 else 0,
            'concurrent_workers': self.max_workers
        }
        
        with self.progress_lock:
            progress_tracker[task_id].update({
                'status': 'completed',
                'final_stats': final_stats
            })
        
        print(f"🎉 [并发分析] 全部完成！总耗时: {total_elapsed_time:.2f}s, "
              f"平均每篇: {final_stats['average_time_per_paper']:.2f}s, "
              f"成功:{success_count}, 失败:{error_count}")
        
        return final_stats


# 全局实例
_concurrent_service_1 = ConcurrentAnalysisService(max_workers=1)  # 串行对照组
_concurrent_service_5 = ConcurrentAnalysisService(max_workers=5)  # 5路并发


def get_concurrent_service(workers: int = 5) -> ConcurrentAnalysisService:
    """获取并发分析服务实例"""
    if workers == 1:
        return _concurrent_service_1
    elif workers == 5:
        return _concurrent_service_5
    else:
        return ConcurrentAnalysisService(max_workers=workers)


def run_performance_comparison(
    task_id: str,
    pending_papers: List[Dict],
    prompt_id: str,
    system_prompt: str,
    progress_tracker: Dict[str, Any],
    test_count: int = 10
) -> Dict[str, Any]:
    """
    运行性能对比测试
    
    Args:
        task_id: 任务ID  
        pending_papers: 待分析论文列表
        prompt_id: 提示词ID
        system_prompt: 系统提示词
        progress_tracker: 进度跟踪器
        test_count: 测试论文数量
        
    Returns:
        Dict: 性能对比结果
    """
    test_papers = pending_papers[:test_count]
    
    print(f"🧪 [性能对比] 开始测试 {test_count} 篇论文的性能对比...")
    
    # 1路串行测试
    print("📊 [性能对比] 开始1路串行测试...")
    serial_start = time.time()
    
    serial_service = get_concurrent_service(workers=1)
    serial_task_id = f"{task_id}_serial"
    progress_tracker[serial_task_id] = {}
    
    serial_result = serial_service.analyze_papers_concurrent(
        serial_task_id, test_papers, prompt_id, system_prompt, progress_tracker
    )
    serial_time = time.time() - serial_start
    
    # 5路并发测试  
    print("📊 [性能对比] 开始5路并发测试...")
    concurrent_start = time.time()
    
    concurrent_service = get_concurrent_service(workers=5)
    concurrent_task_id = f"{task_id}_concurrent"
    progress_tracker[concurrent_task_id] = {}
    
    concurrent_result = concurrent_service.analyze_papers_concurrent(
        concurrent_task_id, test_papers, prompt_id, system_prompt, progress_tracker
    )
    concurrent_time = time.time() - concurrent_start
    
    # 计算性能提升
    speedup_ratio = serial_time / concurrent_time if concurrent_time > 0 else 0
    time_saved = serial_time - concurrent_time
    
    comparison_result = {
        'test_papers_count': test_count,
        'serial_result': {
            'total_time': serial_time,
            'success_count': serial_result['success_count'],
            'error_count': serial_result['error_count'],
            'avg_time_per_paper': serial_time / test_count
        },
        'concurrent_result': {
            'total_time': concurrent_time,
            'success_count': concurrent_result['success_count'], 
            'error_count': concurrent_result['error_count'],
            'avg_time_per_paper': concurrent_time / test_count,
            'workers': 5
        },
        'performance_gain': {
            'speedup_ratio': speedup_ratio,
            'time_saved_seconds': time_saved,
            'time_saved_percentage': (time_saved / serial_time * 100) if serial_time > 0 else 0
        }
    }
    
    print(f"🎯 [性能对比] 结果总结:")
    print(f"   📈 1路串行: {serial_time:.1f}s, 平均每篇: {serial_time/test_count:.1f}s")
    print(f"   🚀 5路并发: {concurrent_time:.1f}s, 平均每篇: {concurrent_time/test_count:.1f}s")
    print(f"   ⚡ 性能提升: {speedup_ratio:.1f}x, 节省时间: {time_saved:.1f}s ({time_saved/serial_time*100:.1f}%)")
    
    return comparison_result
