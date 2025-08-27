#!/usr/bin/env python3
"""
内存管理工具 - 智能内存优化和监控

专为Render免费环境优化，避免内存超限导致的重启
"""

import gc
import sys
import time
import threading
from typing import Dict, Any, Optional
import psutil
import weakref


class MemoryManager:
    """智能内存管理器"""
    
    def __init__(self, max_memory_mb: int = 400):
        """
        初始化内存管理器
        
        Args:
            max_memory_mb: 最大内存限制(MB)，Render免费版约512MB
        """
        self.max_memory_mb = max_memory_mb
        self.warning_threshold = max_memory_mb * 0.8  # 80%警告
        self.critical_threshold = max_memory_mb * 0.95  # 95%紧急清理
        self.lock = threading.Lock()
        self.monitored_objects = {}
        
    def get_memory_usage(self) -> Dict[str, float]:
        """获取当前内存使用情况"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # 物理内存
            'vms_mb': memory_info.vms / 1024 / 1024,  # 虚拟内存
            'percent': process.memory_percent(),
            'available_mb': psutil.virtual_memory().available / 1024 / 1024
        }
    
    def check_memory_pressure(self) -> str:
        """检查内存压力状态"""
        usage = self.get_memory_usage()
        current_mb = usage['rss_mb']
        
        if current_mb > self.critical_threshold:
            return 'critical'
        elif current_mb > self.warning_threshold:
            return 'warning'
        else:
            return 'normal'
    
    def force_cleanup(self, level: str = 'normal'):
        """强制内存清理"""
        with self.lock:
            print(f"🧹 [内存管理] 开始{level}级别清理...")
            before = self.get_memory_usage()
            
            if level in ['warning', 'critical']:
                # 清理全局缓存
                self._cleanup_global_caches()
                
            if level == 'critical':
                # 紧急清理：强制垃圾回收
                for i in range(3):
                    collected = gc.collect()
                    print(f"🗑️ [内存管理] 垃圾回收第{i+1}次: 清理{collected}个对象")
            
            after = self.get_memory_usage()
            freed = before['rss_mb'] - after['rss_mb']
            print(f"💾 [内存管理] 清理完成，释放: {freed:.1f}MB，当前: {after['rss_mb']:.1f}MB")
            
            return freed
    
    def _cleanup_global_caches(self):
        """清理全局缓存"""
        try:
            # 清理分析进度缓存
            import backend.server as server_module
            if hasattr(server_module, 'analysis_progress'):
                old_count = len(server_module.analysis_progress)
                # 只保留最近的任务
                current_time = time.time()
                cutoff_time = current_time - 3600  # 1小时
                
                items_to_remove = []
                for task_id, progress in server_module.analysis_progress.items():
                    start_time = progress.get('start_time', 0)
                    if start_time < cutoff_time or progress.get('status') == 'completed':
                        items_to_remove.append(task_id)
                
                for task_id in items_to_remove:
                    del server_module.analysis_progress[task_id]
                
                print(f"🧹 [缓存清理] analysis_progress: {old_count} -> {len(server_module.analysis_progress)}")
            
            # 清理搜索缓存
            if hasattr(server_module, '_search_cache'):
                server_module._search_cache.clear()
                print(f"🧹 [缓存清理] search_cache已清空")
                
            # 清理机构缓存  
            from backend.services.affiliation_service import clear_affiliation_cache
            clear_affiliation_cache()
            
        except Exception as e:
            print(f"⚠️ [缓存清理] 部分清理失败: {e}")


class LimitedCache:
    """限制大小的缓存"""
    
    def __init__(self, max_size: int = 100):
        """
        Args:
            max_size: 最大缓存项数
        """
        self.max_size = max_size
        self.cache = {}
        self.access_times = {}
        self.lock = threading.Lock()
    
    def get(self, key):
        """获取缓存项"""
        with self.lock:
            if key in self.cache:
                self.access_times[key] = time.time()
                return self.cache[key]
            return None
    
    def put(self, key, value):
        """设置缓存项"""
        with self.lock:
            if len(self.cache) >= self.max_size and key not in self.cache:
                # LRU清理
                oldest_key = min(self.access_times.keys(), 
                               key=lambda k: self.access_times[k])
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
            
            self.cache[key] = value
            self.access_times[key] = time.time()
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()


class StreamBuffer:
    """流式缓冲区 - 替代全量内存存储"""
    
    def __init__(self, max_size: int = 10 * 1024 * 1024):  # 10MB限制
        """
        Args:
            max_size: 最大缓冲区大小(字节)
        """
        self.max_size = max_size
        self.buffer = bytearray()
        self.overflow_file = None
        self.using_file = False
    
    def write(self, data: bytes):
        """写入数据"""
        if not self.using_file and len(self.buffer) + len(data) > self.max_size:
            # 内存不足，切换到临时文件
            import tempfile
            self.overflow_file = tempfile.NamedTemporaryFile(mode='w+b', delete=True)
            self.overflow_file.write(self.buffer)
            self.overflow_file.write(data)
            self.buffer = bytearray()  # 清理内存
            self.using_file = True
            print(f"⚠️ [流式缓冲] 数据过大，切换到临时文件存储")
        elif self.using_file:
            self.overflow_file.write(data)
        else:
            self.buffer.extend(data)
    
    def get_content(self) -> bytes:
        """获取完整内容"""
        if self.using_file:
            self.overflow_file.seek(0)
            content = self.overflow_file.read()
            return content
        else:
            return bytes(self.buffer)
    
    def __del__(self):
        """清理资源"""
        if self.overflow_file:
            self.overflow_file.close()


# 全局内存管理器实例
memory_manager = MemoryManager()


def monitor_memory(func):
    """内存监控装饰器"""
    def wrapper(*args, **kwargs):
        before = memory_manager.get_memory_usage()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            after = memory_manager.get_memory_usage()
            memory_used = after['rss_mb'] - before['rss_mb']
            
            if memory_used > 50:  # 使用超过50MB时警告
                print(f"⚠️ [内存监控] {func.__name__} 使用了 {memory_used:.1f}MB 内存")
            
            # 自动清理检查
            pressure = memory_manager.check_memory_pressure()
            if pressure == 'critical':
                print(f"🚨 [内存监控] 内存压力过高，执行紧急清理")
                memory_manager.force_cleanup('critical')
            elif pressure == 'warning':
                print(f"⚠️ [内存监控] 内存使用偏高，执行预防性清理")
                memory_manager.force_cleanup('warning')
    
    return wrapper