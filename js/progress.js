/**
 * 进度管理和SSE连接相关函数
 */

function updateProgress(data) {
    const { current, total, paper, analysis_result, status, success_count, error_count } = data;
    
    console.log('updateProgress called with:', data);
    
    // 处理连接状态
    if (status === 'connecting') {
        document.getElementById('progressText').textContent = '正在连接分析服务...';
        return;
    }

    // 更新进度条
    const progress = total > 0 ? (current / total) * 100 : 0;
    document.getElementById('progressBarFill').style.width = progress + '%';
    
    // 构建进度文本，包含成功/错误统计
    let progressText = `正在处理第 ${current} / ${total} 篇论文 (${progress.toFixed(1)}%)`;
    if (success_count !== undefined || error_count !== undefined) {
        const successCount = success_count || 0;
        const errorCount = error_count || 0;
        progressText += ` | 成功: ${successCount}, 错误: ${errorCount}`;
    }
    document.getElementById('progressText').textContent = progressText;
    
    // 更新当前论文信息
    if (paper) {
        // 显示论文标题
        document.getElementById('currentTitle').textContent = `第${current}篇: ${paper.title}`;
        
        // 显示作者
        document.getElementById('currentAuthors').textContent = paper.authors;
        
        // 显示摘要（限制长度以便阅读）
        const abstract = paper.abstract || '';
        const shortAbstract = abstract.length > 300 ? abstract.substring(0, 300) + '...' : abstract;
        document.getElementById('currentAbstract').textContent = shortAbstract;
        
        // 显示分析结果
        if (analysis_result) {
            try {
                const result = JSON.parse(analysis_result);
                // 格式化分析结果以便阅读
                let formattedResult = '';
                if (result.pass_filter !== undefined) {
                    formattedResult += `通过筛选: ${result.pass_filter ? '是' : '否'}\n`;
                }
                if (result.raw_score !== undefined) {
                    formattedResult += `原始分数: ${result.raw_score}\n`;
                }
                if (result.norm_score !== undefined) {
                    formattedResult += `标准化分数: ${result.norm_score}\n`;
                }
                if (result.reason) {
                    formattedResult += `原因: ${result.reason}\n`;
                }
                if (result.exclude_reason) {
                    formattedResult += `排除原因: ${result.exclude_reason}`;
                }
                
                document.getElementById('currentAnalysis').textContent = formattedResult || JSON.stringify(result, null, 2);
            } catch (e) {
                document.getElementById('currentAnalysis').textContent = analysis_result;
            }
        } else {
            // 检查是否是特殊状态（如获取机构信息）
            if (status === 'fetching_affiliations' && paper.status) {
                document.getElementById('currentAnalysis').textContent = paper.status; // 显示 "正在获取作者机构..."
            } else {
                document.getElementById('currentAnalysis').textContent = '正在分析...';
            }
        }
    }
}

function startSSEConnection(selectedDate, selectedCategory, testCount, rangeType) {
    // 清理之前的连接
    if (window.AppState.currentEventSource) {
        window.AppState.currentEventSource.close();
    }

    console.log('🔌 启动SSE连接...');
    
    // 保存当前分析的范围类型
    window.AppState.currentAnalysisRange = rangeType || 'full';
    
    // 使用Server-Sent Events获取实时进度
    window.AppState.currentEventSource = new EventSource(`/api/analysis_progress?date=${selectedDate}&category=${selectedCategory}&test_count=${testCount || ''}`);
    
    window.AppState.currentEventSource.onmessage = function(event) {
        console.log('SSE received:', event.data);
        const data = JSON.parse(event.data);
        console.log('SSE parsed data:', data);
        updateProgress(data);
        window.AppState.lastProgressUpdate = Date.now();
    };

    window.AppState.currentEventSource.onerror = function(event) {
        console.error('SSE连接错误:', event);
        console.log('🔄 SSE连接中断，等待重新连接...');
        
        // 更新进度显示，但不立即启动故障转移
        const progressText = document.getElementById('progressText');
        if (progressText && !progressText.textContent.includes('连接中断')) {
            progressText.textContent += ' | 连接中断，重连中...';
        }
        
        // 不立即关闭连接，让浏览器自动重连
        // 故障转移机制会在后台独立运行
    };

    window.AppState.currentEventSource.addEventListener('complete', function(event) {
        const data = JSON.parse(event.data);
        console.log('✅ 分析完成事件:', data);
        onAnalysisComplete(data);
        stopAllConnections();
    });

    window.AppState.currentEventSource.addEventListener('error', function(event) {
        console.error('SSE错误事件:', event);
        const data = JSON.parse(event.data);
        showError('分析出错: ' + (data.error || '未知错误'));
        stopAllConnections();
    });
}

function startProgressFallbackCheck(selectedDate, selectedCategory) {
    // 清理之前的定时器
    if (window.AppState.progressCheckInterval) {
        clearInterval(window.AppState.progressCheckInterval);
    }

    console.log('🔄 启动故障转移进度检查机制...');
    
    // 每15秒检查一次进度（备用机制），减少频繁检查
    window.AppState.progressCheckInterval = setInterval(async () => {
        try {
            // 检查是否长时间没有收到更新（超过60秒）
            const timeSinceLastUpdate = Date.now() - window.AppState.lastProgressUpdate;
            if (timeSinceLastUpdate > 60000) {
                console.log('⚠️  长时间无进度更新，使用故障转移检查...');
                await checkAnalysisStatus(selectedDate, selectedCategory);
            }
        } catch (error) {
            console.error('故障转移进度检查失败:', error);
        }
    }, 15000);  // 每15秒检查一次
}

async function checkAnalysisStatus(selectedDate, selectedCategory) {
    try {
        // 使用专门的状态检查接口，而不是结果获取接口
        const response = await fetch('/api/check_analysis_exists', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                date: selectedDate, 
                category: selectedCategory
            })
        });

        if (response.ok) {
            const data = await response.json();
            console.log('📊 故障转移检查状态:', data);
            
            // 只有当所有论文都分析完成时才认为完成
            if (data.all_analyzed && data.total > 0) {
                console.log('✅ 故障转移检查发现分析已完成!');
                
                // 分析已完成，直接跳转到结果页面
                const completionData = {
                    summary: `分析完成！共处理 ${data.total} 篇论文`,
                    completed_range_type: window.AppState.currentAnalysisRange || 'full'
                };
                
                onAnalysisComplete(completionData);
                stopAllConnections();
            } else {
                // 分析还在进行中
                console.log(`📊 故障转移检查：分析仍在进行中... (${data.completed}/${data.total})`);
                
                // 更新显示时间信息和进度
                const elapsed = Math.floor((Date.now() - window.AppState.analysisStartTime) / 1000);
                const minutes = Math.floor(elapsed / 60);
                const seconds = elapsed % 60;
                
                const progressText = document.getElementById('progressText');
                if (progressText) {
                    const baseText = `分析进行中 ${data.completed}/${data.total} 篇论文`;
                    progressText.textContent = `${baseText} | 已运行: ${minutes}分${seconds}秒`;
                }
                
                // 更新进度条
                const progress = data.total > 0 ? (data.completed / data.total) * 100 : 0;
                const progressBarFill = document.getElementById('progressBarFill');
                if (progressBarFill) {
                    progressBarFill.style.width = progress + '%';
                }
            }
        } else {
            console.log('📊 故障转移检查失败，继续等待...');
        }
    } catch (error) {
        console.error('故障转移状态检查失败:', error);
    }
}

function stopAllConnections() {
    // 停止SSE连接
    if (window.AppState.currentEventSource) {
        console.log('🔌 关闭SSE连接');
        window.AppState.currentEventSource.close();
        window.AppState.currentEventSource = null;
    }
    
    // 停止故障转移检查
    if (window.AppState.progressCheckInterval) {
        console.log('🔄 关闭故障转移检查');
        clearInterval(window.AppState.progressCheckInterval);
        window.AppState.progressCheckInterval = null;
    }
}

async function onAnalysisComplete(data) {
    // 显示完成信息
    document.getElementById('progressText').textContent = '分析完成！正在加载结果...';
    document.getElementById('analysisSummary').style.display = 'block';
    document.getElementById('summaryText').textContent = data.summary || '分析已完成，正在加载结果...';
    
    // 立即关闭弹窗并加载新表格
    closeModal();
    // 使用完成的分析范围类型来加载结果
    const completedRangeType = data.completed_range_type || window.AppState.currentAnalysisRange || 'full';
    await loadAnalysisResults(completedRangeType);
}