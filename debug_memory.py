#!/usr/bin/env python3
"""
内存优化调试脚本
用于测试内存泄露修复效果

使用方法: python debug_memory.py
"""

import os
import time
import sys
import threading
from backend.utils.memory_manager import memory_manager
from backend.services.concurrent_analysis_service import get_concurrent_service
from backend.db import repo as db_repo

def test_memory_optimization():
    """测试内存优化效果"""
    print("🔬 [调试] 开始内存优化测试...")
    
    # 1. 显示初始内存状态
    initial_memory = memory_manager.get_memory_usage()
    print(f"📊 [初始状态] 内存使用: {initial_memory['rss_mb']:.1f}MB ({initial_memory['percent']:.1f}%)")
    
    # 2. 模拟用户指定的调试场景
    selected_date = "2025-08-25"
    selected_category = "cs.CV"
    workers = 5
    
    print(f"🎯 [调试参数] 日期={selected_date}, 分类={selected_category}, 并发数={workers}")
    
    try:
        # 获取待分析论文
        prompt_id = db_repo.get_prompt_id_by_name('multi-modal-llm')
        if not prompt_id:
            print("❌ [错误] 缺少 multi-modal-llm prompt")
            return
            
        # 获取少量论文进行测试 (避免长时间运行)
        pending = db_repo.list_unanalyzed_papers(selected_date, selected_category, prompt_id, limit=3)
        
        if not pending:
            print(f"📭 [信息] 当天没有待分析的{selected_category}论文")
            # 改用已分析的论文来测试内存管理
            all_papers = db_repo.list_papers_by_date_category(selected_date, selected_category)
            if len(all_papers) >= 3:
                pending = all_papers[:3]  # 取前3篇用于测试
                print(f"🔄 [测试] 使用已存在的论文进行内存管理测试")
            else:
                print(f"⚠️ [警告] 数据不足，跳过测试")
                return
        
        print(f"📝 [测试数据] 将测试 {len(pending)} 篇论文")
        
        # 3. 运行内存监控的并发分析测试
        print("🚀 [开始测试] 启动内存监控的并发分析...")
        
        # 创建测试用的进度跟踪器
        progress_tracker = {}
        task_id = f"{selected_date}-{selected_category}-memory-test"
        
        # 监控内存使用
        def memory_monitor():
            for i in range(30):  # 监控30秒
                usage = memory_manager.get_memory_usage()
                pressure = memory_manager.check_memory_pressure()
                print(f"📊 [内存监控] {i+1}s: {usage['rss_mb']:.1f}MB ({usage['percent']:.1f}%) - {pressure}")
                
                if pressure in ['warning', 'critical']:
                    print(f"⚠️ [内存监控] 检测到{pressure}级别的内存压力!")
                    freed = memory_manager.force_cleanup(pressure)
                    print(f"🧹 [内存监控] 自动清理释放了 {freed:.1f}MB")
                
                time.sleep(1)
        
        # 启动内存监控线程
        monitor_thread = threading.Thread(target=memory_monitor, daemon=True)
        monitor_thread.start()
        
        # 运行优化后的并发分析服务
        concurrent_service = get_concurrent_service(workers=workers)
        system_prompt = db_repo.get_system_prompt()
        
        # 获取测试前内存状态
        before_test = memory_manager.get_memory_usage()
        
        # 只运行很短时间以测试内存管理
        test_start = time.time()
        
        # 由于我们主要测试内存管理而不是实际分析，这里做一个简化的测试
        print(f"🧪 [内存测试] 模拟PDF下载和缓存操作...")
        
        # 测试PDF下载内存管理
        for i, paper in enumerate(pending[:2]):  # 只测试2篇
            print(f"📄 [测试 {i+1}/2] 论文: {paper.get('title', 'Unknown')[:50]}...")
            
            # 模拟PDF下载（不实际下载，只测试内存监控）
            from backend.utils.memory_manager import StreamBuffer
            buffer = StreamBuffer()
            
            # 模拟大数据写入
            for chunk in range(500):  # 模拟500个chunk
                fake_data = b"x" * 32768  # 32KB 假数据
                buffer.write(fake_data)
                
                if chunk % 100 == 0:
                    usage = memory_manager.get_memory_usage()
                    print(f"   📊 Chunk {chunk}: {usage['rss_mb']:.1f}MB")
            
            # 清理测试数据
            del buffer
            
            # 检查内存状态
            usage = memory_manager.get_memory_usage()
            pressure = memory_manager.check_memory_pressure()
            print(f"   ✅ 测试完成: {usage['rss_mb']:.1f}MB ({pressure})")
            
        test_end = time.time()
        
        # 4. 显示测试结果
        after_test = memory_manager.get_memory_usage()
        
        print("\n" + "="*50)
        print("📈 [内存优化测试结果]")
        print(f"初始内存: {initial_memory['rss_mb']:.1f}MB")
        print(f"测试前: {before_test['rss_mb']:.1f}MB") 
        print(f"测试后: {after_test['rss_mb']:.1f}MB")
        print(f"内存增长: {after_test['rss_mb'] - before_test['rss_mb']:.1f}MB")
        print(f"测试时长: {test_end - test_start:.1f}s")
        print("="*50)
        
        # 5. 执行最终清理
        print("🧹 [最终清理] 执行完整内存清理...")
        freed = memory_manager.force_cleanup('critical')
        
        final_memory = memory_manager.get_memory_usage()
        print(f"🎯 [最终状态] 内存使用: {final_memory['rss_mb']:.1f}MB ({final_memory['percent']:.1f}%)")
        print(f"✅ [优化效果] 清理释放: {freed:.1f}MB")
        
    except Exception as e:
        print(f"❌ [测试失败] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        test_memory_optimization()
    except KeyboardInterrupt:
        print("\n⚠️ [中断] 测试被用户中断")
    except Exception as e:
        print(f"❌ [致命错误] {e}")
        import traceback
        traceback.print_exc()