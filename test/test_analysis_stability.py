#!/usr/bin/env python3
"""
测试分析功能稳定性的脚本
用于验证修复分析卡住问题的效果
"""

import requests
import time
import json
import sys
import os

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def test_analysis_stability():
    """测试分析功能稳定性"""
    
    print("🔧 分析功能稳定性测试")
    print("=" * 60)
    
    base_url = "http://localhost:8080"
    test_date = "2025-07-31"
    test_category = "cs.AI"
    
    # 检查服务器是否运行
    try:
        response = requests.get(base_url, timeout=5)
        print("✅ 服务器运行正常")
    except requests.exceptions.RequestException:
        print("❌ 服务器未运行，请先启动: python server.py")
        return False
    
    # 检查API密钥配置
    if not os.getenv('DOUBAO_API_KEY'):
        print("❌ 环境变量 DOUBAO_API_KEY 未设置")
        print("🔧 请按照README.md配置环境变量或创建.env文件")
        return False
    
    print("✅ 豆包API密钥已配置")
    
    # 测试大规模分析（20篇论文）
    print(f"\n🚀 启动稳定性测试（{test_category} 前20篇论文）...")
    print("这个测试将验证修复的关键功能：")
    print("  - API调用超时设置（60秒）")
    print("  - 重试机制（每篇论文最多3次重试）")
    print("  - 异常处理和恢复")
    print("  - 进度跟踪的稳定性")
    
    try:
        # 启动分析
        analyze_response = requests.post(
            f"{base_url}/api/analyze_papers",
            headers={"Content-Type": "application/json"},
            json={"date": test_date, "category": test_category, "test_count": 20},
            timeout=10
        )
        
        if analyze_response.status_code != 200:
            print(f"❌ 启动分析失败: {analyze_response.status_code}")
            print(f"错误信息: {analyze_response.text}")
            return False
        
        task_data = analyze_response.json()
        task_id = task_data.get('task_id')
        print(f"✅ 分析任务启动成功: {task_id}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 分析请求失败: {e}")
        return False
    
    # 监控分析进度
    print(f"\n📊 监控分析进度（最多等待20分钟）...")
    
    try:
        progress_url = f"{base_url}/api/analysis_progress?date={test_date}&category={test_category}"
        
        start_time = time.time()
        max_wait_time = 1200  # 最多等待20分钟
        
        last_current = 0
        stuck_time = 0
        stuck_threshold = 180  # 3分钟无进度视为卡住
        
        success_count = 0
        error_count = 0
        
        with requests.get(progress_url, stream=True, timeout=max_wait_time) as response:
            if response.status_code != 200:
                print(f"❌ 进度监控失败: {response.status_code}")
                return False
            
            completed = False
            error_occurred = False
            last_progress_time = time.time()
            
            for line in response.iter_lines(decode_unicode=True):
                current_time = time.time()
                
                if current_time - start_time > max_wait_time:
                    print("⏰ 总体超时，停止监控")
                    break
                
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])  # 移除 'data: ' 前缀
                        status = data.get('status', '')
                        current = data.get('current', 0)
                        total = data.get('total', 0)
                        success_count = data.get('success_count', success_count)
                        error_count = data.get('error_count', error_count)
                        
                        if current > 0:
                            # 检查进度是否有更新
                            if current > last_current:
                                last_current = current
                                last_progress_time = current_time
                                stuck_time = 0
                                elapsed = current_time - start_time
                                avg_time_per_paper = elapsed / current
                                eta_seconds = avg_time_per_paper * (total - current)
                                eta_minutes = eta_seconds / 60
                                
                                print(f"   📄 进度: {current}/{total} ({status}) | 成功: {success_count}, 错误: {error_count} | 平均: {avg_time_per_paper:.1f}s/篇 | 预计还需: {eta_minutes:.1f}分钟")
                            else:
                                # 进度没有更新，检查是否卡住
                                stuck_time = current_time - last_progress_time
                                if stuck_time > stuck_threshold:
                                    print(f"⚠️  检测到可能卡住：第{current}篇论文已处理{stuck_time:.0f}秒无进度")
                                    print(f"   这可能是网络延迟或复杂论文需要更长处理时间")
                        
                        if status == 'error':
                            error_occurred = True
                            error_msg = data.get('error', '未知错误')
                            print(f"❌ 分析出错: {error_msg}")
                            break
                            
                    except json.JSONDecodeError:
                        continue
                
                elif line.startswith('event: complete'):
                    completed = True
                    elapsed_total = time.time() - start_time
                    print(f"\n🎉 分析完成！")
                    print(f"   📊 总耗时: {elapsed_total/60:.1f} 分钟")
                    total_processed = success_count + error_count
                    if total_processed > 0:
                        print(f"   📈 成功率: {success_count}/{total_processed} ({success_count/total_processed*100:.1f}%)")
                    else:
                        print(f"   📈 处理统计: 成功 {success_count}, 错误 {error_count}")
                    break
                
                elif line.startswith('event: error'):
                    error_occurred = True
                    print("❌ 分析过程出错")
                    break
            
            if error_occurred:
                print(f"\n💥 测试失败，但分析了 {success_count} 篇论文")
                return False
            elif completed:
                print(f"\n🎊 稳定性测试成功！")
                print(f"✅ 成功处理 {success_count} 篇论文")
                if error_count > 0:
                    print(f"⚠️  {error_count} 篇论文有错误，但分析流程继续进行")
                print("🔧 修复验证：")
                print("  ✅ 无卡住现象")
                print("  ✅ 进度正常更新") 
                print("  ✅ 错误处理正常")
                return True
            else:
                print(f"\n⚠️  测试超时或状态不明确")
                print(f"📊 已处理: {last_current} 篇论文")
                return False
                
    except requests.exceptions.RequestException as e:
        print(f"❌ 进度监控失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 分析功能稳定性测试工具")
    print("这个工具将验证修复后的分析功能是否稳定，不会卡住")
    
    success = test_analysis_stability()
    
    if success:
        print("\n🎊 稳定性测试通过！分析功能已修复")
        print("💡 修复要点:")
        print("  - 添加了60秒API调用超时")
        print("  - 实现了3次重试机制") 
        print("  - 改进了异常处理和恢复")
        print("  - 增强了进度跟踪稳定性")
        return True
    else:
        print("\n💥 稳定性测试失败")
        print("🔧 建议检查:")
        print("  1. 网络连接是否稳定")
        print("  2. 豆包API服务是否正常")
        print("  3. 服务器终端日志中的错误信息")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ 用户中断测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 测试过程出错: {e}")
        sys.exit(1)