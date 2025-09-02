/**
 * 进度管理和SSE连接相关函数
 */

function updateProgress(data) {
    const { current, total, paper, analysis_result, status, success_count, error_count, workers, processing_papers, last_completed_paper } = data;
    
    
    // 处理连接状态
    if (status === 'connecting') {
        document.getElementById('progressText').textContent = '正在连接分析服务...';
        return;
    }
    
    // 处理分析开始状态，清空之前的显示信息
    if (status === 'starting' && current === 0) {
        document.getElementById('currentTitle').textContent = '准备开始分析...';
        document.getElementById('currentAnalysis').textContent = '等待分析开始...';
        const authorsElement = document.getElementById('currentAuthors');
        const abstractElement = document.getElementById('currentAbstract');
        if (authorsElement) authorsElement.textContent = '';
        if (abstractElement) abstractElement.textContent = '';
        return;
    }

    // 更新进度条
    const progress = total > 0 ? (current / total) * 100 : 0;
    document.getElementById('progressBarFill').style.width = progress + '%';
    
    // 构建进度文本，包含并发信息和成功/错误统计
    let progressText = `正在处理第 ${current} / ${total} 篇论文 (${progress.toFixed(1)}%)`;
    
    // 显示并发信息
    if (workers && workers > 1) {
        progressText += ` | ${workers}路并发`;
        
        // 显示正在处理的论文数量
        if (processing_papers && processing_papers.length > 0) {
            progressText += ` | 正在处理: ${processing_papers.length}篇`;
        }
    }
    
    // 显示成功/错误统计
    if (success_count !== undefined || error_count !== undefined) {
        const successCount = success_count || 0;
        const errorCount = error_count || 0;
        progressText += ` | 成功: ${successCount}, 错误: ${errorCount}`;
    }
    
    document.getElementById('progressText').textContent = progressText;
    
    // 更新当前论文信息
    // 优先显示最新完成的论文，否则显示当前处理的论文
    const displayPaper = last_completed_paper || paper;
    
    // 如果没有当前论文数据(paper)，且只有历史完成数据(last_completed_paper)，则不显示
    // 这避免了显示上一次分析的残留信息
    const shouldHideOldData = !paper && last_completed_paper;
    
    if (displayPaper && !shouldHideOldData) {
        // 构建标题，区分是最新完成还是正在处理
        let titlePrefix = '';
        if (last_completed_paper) {
            titlePrefix = `最新完成第${current}篇`;
            if (last_completed_paper.success) {
                titlePrefix += ` ✅`;
            } else {
                titlePrefix += ` ❌`;
            }
        } else {
            titlePrefix = `第${current}篇`;
        }
        
        // 显示论文标题
        document.getElementById('currentTitle').textContent = `${titlePrefix}: ${displayPaper.title}`;
        
        // 隐藏作者和摘要信息（在并发模式下不显示）- 安全检查元素是否存在
        const authorsElement = document.getElementById('currentAuthors');
        const abstractElement = document.getElementById('currentAbstract');
        if (authorsElement) {
            authorsElement.textContent = '并发分析模式 - 专注于速度';
        }
        if (abstractElement) {
            abstractElement.textContent = '查看完整信息请在分析完成后查看结果表格';
        }
        
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
    } else {
        // 没有要显示的论文数据时，显示等待状态
        document.getElementById('currentTitle').textContent = '等待分析数据...';
        document.getElementById('currentAnalysis').textContent = '准备中...';
        const authorsElement = document.getElementById('currentAuthors');
        const abstractElement = document.getElementById('currentAbstract');
        if (authorsElement) authorsElement.textContent = '等待分析开始';
        if (abstractElement) abstractElement.textContent = '等待分析开始';
    }
}

function startSSEConnection(selectedDate, selectedCategory, testCount, rangeType, taskId = null) {
    // 清理之前的连接
    if (window.AppState.currentEventSource) {
        window.AppState.currentEventSource.close();
    }

    // 清空上一次分析的UI状态
    if (typeof clearPreviousAnalysisResults === 'function') {
        clearPreviousAnalysisResults();
    }
    
    // 保存当前分析的范围类型
    window.AppState.currentAnalysisRange = rangeType || 'full';
    
    // 使用Server-Sent Events获取实时进度 (并发分析类型)
    let url;
    if (taskId) {
        // 智能搜索分析：使用自定义task_id
        url = `/api/analysis_progress?task_id=${taskId}&type=concurrent`;
    } else {
        // 普通分析：使用日期分类参数
        url = `/api/analysis_progress?date=${selectedDate}&category=${selectedCategory}&test_count=${testCount || ''}&type=concurrent`;
    }
    window.AppState.currentEventSource = new EventSource(url);
    
    window.AppState.currentEventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        updateProgress(data);
        window.AppState.lastProgressUpdate = Date.now();
    };

    window.AppState.currentEventSource.onerror = function(event) {
        console.error('SSE连接错误:', event);
        
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
    
    // 每15秒检查一次进度（备用机制），减少频繁检查
    window.AppState.progressCheckInterval = setInterval(async () => {
        try {
            // 检查是否长时间没有收到更新（超过60秒）
            const timeSinceLastUpdate = Date.now() - window.AppState.lastProgressUpdate;
            if (timeSinceLastUpdate > 60000) {
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
            
            // 只有当所有论文都分析完成时才认为完成
            if (data.all_analyzed && data.total > 0) {
                // 分析已完成，直接跳转到结果页面
                const completionData = {
                    summary: `分析完成！共处理 ${data.total} 篇论文`,
                    completed_range_type: window.AppState.currentAnalysisRange || 'full'
                };
                
                onAnalysisComplete(completionData);
                stopAllConnections();
            } else {
                // 分析还在进行中
                
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
        }
    } catch (error) {
        console.error('故障转移状态检查失败:', error);
    }
}

function stopAllConnections() {
    // 停止SSE连接
    if (window.AppState.currentEventSource) {
        window.AppState.currentEventSource.close();
        window.AppState.currentEventSource = null;
    }
    
    // 停止故障转移检查
    if (window.AppState.progressCheckInterval) {
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
    
    // 检查是否为智能搜索分析
    if (smartSearchState && smartSearchState.currentAnalysisTask) {
        await loadSmartSearchAnalysisResults();
    } else {
        // 使用完成的分析范围类型来加载结果
        const completedRangeType = data.completed_range_type || window.AppState.currentAnalysisRange || 'full';
        await loadAnalysisResults(completedRangeType);
    }
}