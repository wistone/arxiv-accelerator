/**
 * 分析相关函数
 */

// 改进后的分析文章函数，先重置选项再检查
async function analyzeArticlesImproved() {
    if (!window.AppState.hasSearched || window.AppState.currentArticles.length === 0) {
        showError('请先搜索文章列表');
        return;
    }

    // 先重置分析选项为默认状态
    resetAnalysisOptions();
    
    // 然后调用原来的分析逻辑
    await analyzeArticles();
}

async function analyzeArticles() {
    if (!window.AppState.hasSearched || window.AppState.currentArticles.length === 0) {
        showError('请先搜索文章列表');
        return;
    }
    
    // 清除之前的批次按钮（开始新的分析session）
    clearPreviousBatchButtons();

    const selectedDate = document.getElementById('dateSelect').value;
    const selectedCategory = document.getElementById('categorySelect').value;
    
    // 首先检查数据库中的分析进度
    try {
        setButtonLoading('analyzeBtn', true, '检查中...');
        const response = await fetch('/api/check_analysis_exists', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date: selectedDate,
                category: selectedCategory
            })
        });

        const data = await response.json();

        if (response.ok) {
            // 渲染“已分析 n/total”
            const analysisStatus = document.getElementById('analysisStatus');
            if (analysisStatus) {
                analysisStatus.innerHTML = `已完成分析 ${data.completed} 篇文章 / 共 ${data.total} 篇文章`;
            }

            // 更新“开始分析”按钮状态
            const startBtn = document.getElementById('startAnalysisBtn') || document.getElementById('analyzeBtn');
            if (startBtn) startBtn.disabled = !!data.all_analyzed;
            const analyzeBtn = document.getElementById('analyzeBtn');
            if (analyzeBtn) analyzeBtn.disabled = false; // 打开弹窗后允许再次点击

            // 动态裁剪下拉选项：若 completed 已超过某范围，则移除较小范围
            const testCountSelect = document.getElementById('testCount');
            if (testCountSelect) {
                const optionsMap = [
                    {value: '5', threshold: 5},
                    {value: '10', threshold: 10},
                    {value: '20', threshold: 20}
                ];
                optionsMap.forEach(({value, threshold}) => {
                    const opt = Array.from(testCountSelect.options).find(o => o.value === value);
                    if (opt) {
                        if (data.completed >= threshold) {
                            // 已经达到/超过该范围，则隐藏该项
                            opt.disabled = true;
                            opt.style.display = 'none';
                        } else {
                            opt.disabled = false;
                            opt.style.display = '';
                        }
                    }
                });
                // 如果 5/10/20 都不可用，则仅保留“全部分析”
                const smallOptionsHidden = ['5','10','20'].every(v => {
                    const opt = Array.from(testCountSelect.options).find(o => o.value === v);
                    return opt && opt.disabled;
                });
                if (smallOptionsHidden) {
                    testCountSelect.value = '';
                } else {
                    // 选择第一个可用的小范围，避免误触全量
                    const firstAvail = ['5','10','20'].find(v => {
                        const opt = Array.from(testCountSelect.options).find(o => o.value === v);
                        return opt && !opt.disabled;
                    });
                    if (firstAvail) testCountSelect.value = firstAvail;
                }
            }

            // 显示弹窗与选项
            document.getElementById('analysisModal').style.display = 'block';
            document.getElementById('testOptions').style.display = 'block';
            document.getElementById('progressContainer').style.display = 'none';
            document.getElementById('currentPaper').style.display = 'none';
            document.getElementById('analysisSummary').style.display = 'none';

            // 提供“加载并展示”入口
            ensureShowExistingButton(data);
            return;
        }
    } catch (error) {
        console.log('检查分析进度时出错，继续进行新分析:', error);
    }
    finally {
        setButtonLoading('analyzeBtn', false);
    }

    // 如果不存在分析文件，显示分析弹窗
    document.getElementById('analysisModal').style.display = 'block';
    
    // 重置弹窗状态
    document.getElementById('testOptions').style.display = 'block';
    document.getElementById('progressContainer').style.display = 'none';
    document.getElementById('currentPaper').style.display = 'none';
    document.getElementById('analysisSummary').style.display = 'none';
    
    // 清空状态提示
    document.getElementById('analysisStatus').innerHTML = '';
}

function showAnalysisOptions(data) {
    // 显示分析选项弹窗
    document.getElementById('analysisModal').style.display = 'block';
    
    // 重置弹窗状态
    document.getElementById('testOptions').style.display = 'block';
    document.getElementById('progressContainer').style.display = 'none';
    document.getElementById('currentPaper').style.display = 'none';
    document.getElementById('analysisSummary').style.display = 'none';
    
    // 更新分析选项
    updateAnalysisOptions(data);
}

function updateAnalysisOptions(data) {
    const testCountSelect = document.getElementById('testCount');
    const analysisStatus = document.getElementById('analysisStatus');
    
    // 清空选项
    testCountSelect.innerHTML = '';
    
    if (data.available_options && data.available_options.length > 0) {
        // 根据可用选项更新下拉菜单
        data.available_options.forEach(option => {
            const optionElement = document.createElement('option');
            optionElement.value = option === 'full' ? '' : 
                               option === 'top5' ? '5' :
                               option === 'top10' ? '10' :
                               option === 'top20' ? '20' : '';
            optionElement.textContent = option === 'full' ? '全部分析' :
                                     option === 'top5' ? '仅前5篇' :
                                     option === 'top10' ? '仅前10篇' :
                                     option === 'top20' ? '仅前20篇' : '';
            testCountSelect.appendChild(optionElement);
        });
        
        // 显示状态信息
        let statusText = '📋 发现已有分析结果：\n';
        data.existing_files.forEach(file => {
            statusText += `• ${file.range_desc} (${file.filename})\n`;
        });
        statusText += '\n💡 提示：您可以选择加载现有结果或重新生成更大范围的分析。';
        analysisStatus.innerHTML = statusText.replace(/\n/g, '<br>');
    } else {
        // 如果没有可用选项，显示默认选项
        testCountSelect.innerHTML = `
            <option value="">全部分析</option>
            <option value="5">仅前5篇</option>
            <option value="10">仅前10篇</option>
            <option value="20">仅前20篇</option>
        `;
        analysisStatus.innerHTML = '';
    }
}

async function startAnalysis() {
    const selectedDate = document.getElementById('dateSelect').value;
    const selectedCategory = document.getElementById('categorySelect').value;
    const testCount = document.getElementById('testCount').value;
    
    // 确定选择的分析范围类型
    const selectedRange = testCount === '5' ? 'top5' :
                       testCount === '10' ? 'top10' :
                       testCount === '20' ? 'top20' : 'full';

    // 直接开始分析（后端会跳过已分析并按补齐逻辑选择待分析数）
    const testCountInt = testCount === '' ? null : parseInt(testCount);
    await startNewAnalysis(selectedDate, selectedCategory, selectedRange, testCountInt);
    
    // 更新URL状态，使用正确的limit参数
    updateUrlState('analysis', selectedDate, selectedCategory, selectedRange);
}

async function startNewAnalysis(selectedDate, selectedCategory, selectedRange, testCount) {
    // 隐藏测试选项，显示进度条
    document.getElementById('testOptions').style.display = 'none';
    document.getElementById('progressContainer').style.display = 'block';
    document.getElementById('currentPaper').style.display = 'block';
    
    window.AppState.analysisStartTime = Date.now();
    window.AppState.lastProgressUpdate = Date.now();
    
    try {
        setButtonLoading('startAnalysisBtn', true, '启动中...');
        const overlay = document.getElementById('overlayLoading');
        if (overlay) overlay.style.display = 'flex';
        const response = await fetch('/api/analyze_papers_concurrent', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date: selectedDate,
                category: selectedCategory,
                range_type: selectedRange,
                workers: 5  // 默认使用5路并发
            })
        });

        if (!response.ok) {
            throw new Error('分析请求失败');
        }

        // 开始SSE连接和故障转移检查机制
        startSSEConnection(selectedDate, selectedCategory, testCount, selectedRange);
        startProgressFallbackCheck(selectedDate, selectedCategory);

    } catch (error) {
        showError('分析启动失败: ' + error.message);
        console.error('分析错误:', error);
    } finally {
        setButtonLoading('startAnalysisBtn', false);
        const overlay = document.getElementById('overlayLoading');
        if (overlay) overlay.style.display = 'none';
    }
}

function ensureShowExistingButton(statusData) {
    const btn = document.getElementById('showExistingBtn');
    if (!btn) return; // 如果页面没有该按钮，忽略
    // 当已分析数量>0时展示按钮
    if (statusData && statusData.completed > 0) {
        btn.style.display = 'inline-block';
        btn.onclick = async () => {
            // 根据实际完成的数量确定范围类型
            let rangeType = 'full';
            if (statusData.completed <= 5) {
                rangeType = 'top5';
            } else if (statusData.completed <= 10) {
                rangeType = 'top10';
            } else if (statusData.completed <= 20) {
                rangeType = 'top20';
            }
            await loadAnalysisResults(rangeType);
            closeModal();
        };
    } else {
        btn.style.display = 'none';
    }
}

async function loadAnalysisResults(rangeTypeToLoad = 'full') {
    const selectedDate = document.getElementById('dateSelect').value;
    const selectedCategory = document.getElementById('categorySelect').value;
    
    // 清除之前的批次按钮（加载新的分析结果）
    clearPreviousBatchButtons();
    
    try {
        setButtonLoading('showExistingBtn', true, '加载中...');
        const overlay = document.getElementById('overlayLoading');
        if (overlay) overlay.style.display = 'flex';
        const response = await fetch('/api/get_analysis_results', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date: selectedDate,
                category: selectedCategory,
                range_type: rangeTypeToLoad  // 使用传入的分析范围类型
            })
        });

        const data = await response.json();

        if (response.ok) {
            // 检查是否是分析失败的结果
            if (data.is_analysis_failed) {
                displayAnalysisFailure(data.fail_info);
                showError(`分析失败：${data.fail_info.total_papers} 篇论文的AI分析都失败了`);
            } else {
                // 并行加载批次信息和显示分析结果
                await showAnalysisResultsWithBatchesOptimized(data.articles, data.total, selectedDate, selectedCategory);
            }
            
            // 更新URL状态 - 修正limit参数
            const limitParam = rangeTypeToLoad === 'full' ? 'full' : rangeTypeToLoad;
            updateUrlState('analysis', selectedDate, selectedCategory, limitParam);
        } else {
            showError(data.error || '加载分析结果失败');
        }
    } catch (error) {
        showError('加载分析结果时出现网络错误');
        console.error('加载分析结果错误:', error);
    } finally {
        setButtonLoading('showExistingBtn', false);
        const overlay = document.getElementById('overlayLoading');
        if (overlay) overlay.style.display = 'none';
    }
}

function retryAnalysis() {
    // 获取当前的日期和分类
    const selectedDate = document.getElementById('dateSelect').value;
    const selectedCategory = document.getElementById('categorySelect').value;
    
    if (!selectedDate) {
        showError('请先选择日期');
        return;
    }
    
    // 重新打开分析模态框
    document.getElementById('analysisModal').style.display = 'block';
    showAnalysisOptions({articles: window.AppState.currentArticles});
}

// 优化版本：并行加载分析结果和批次信息
async function showAnalysisResultsWithBatchesOptimized(articles, totalCount, date, category) {
    try {
        // 启动批次信息获取和批次验证的并行操作
        const batchInfoPromise = fetch('/api/get_ingest_batches', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date: date,
                category: category
            })
        });

        // 先显示分析结果，不等待批次信息
        displayAnalysisResults(articles);

        // 等待批次信息
        const batchResponse = await batchInfoPromise;
        
        if (batchResponse.ok) {
            const batchData = await batchResponse.json();
            const batchInfo = batchData.batch_info;
            
            if (batchInfo && batchInfo.batches && batchInfo.batches.length > 1) {
                // 有多个批次，快速检查并创建按钮
                await createBatchFilterButtonsOptimized(articles, totalCount, batchInfo, date, category);
            } else {
                // 只有一个批次或无批次信息，显示普通成功消息
                showSuccess(`分析完成！共处理 ${totalCount} 篇论文`);
            }
        } else {
            // 获取批次信息失败，显示普通成功消息
            showSuccess(`分析完成！共处理 ${totalCount} 篇论文`);
        }
    } catch (error) {
        console.error('优化版批次信息获取失败:', error);
        showSuccess(`分析完成！共处理 ${totalCount} 篇论文`);
    }
}

// 显示分析结果并获取批次信息
async function showAnalysisResultsWithBatches(articles, totalCount, date, category) {
    try {
        // 获取批次信息
        const response = await fetch('/api/get_ingest_batches', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date: date,
                category: category
            })
        });

        if (response.ok) {
            const data = await response.json();
            const batchInfo = data.batch_info;
            
            if (batchInfo && batchInfo.batches && batchInfo.batches.length > 1) {
                // 有多个批次，显示批次筛选按钮
                createBatchFilterButtons(articles, totalCount, batchInfo);
            } else {
                // 只有一个批次或无批次信息，显示普通成功消息
                showSuccess(`分析完成！共处理 ${totalCount} 篇论文`);
            }
        } else {
            // 获取批次信息失败，显示普通成功消息
            showSuccess(`分析完成！共处理 ${totalCount} 篇论文`);
        }
    } catch (error) {
        console.error('获取批次信息失败:', error);
        showSuccess(`分析完成！共处理 ${totalCount} 篇论文`);
    }
}

// 优化版本：快速批次按钮创建，使用并行请求
async function createBatchFilterButtonsOptimized(allArticles, totalCount, batchInfo, date, category) {
    // 存储全局变量供按钮回调使用
    window.AppState.currentBatchInfo = batchInfo;
    window.AppState.currentAllArticles = allArticles;
    
    // 并行检查所有批次是否有分析结果
    const batchCheckPromises = batchInfo.batches.map(async (batch) => {
        try {
            const response = await fetch('/api/get_analysis_results', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    date: date,
                    category: category,
                    range_type: 'full',
                    batch_filter: batch.paper_ids
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.articles && data.articles.length > 0) {
                    return {
                        ...batch,
                        analysis_count: data.articles.length
                    };
                }
            }
            return null; // 没有分析结果的批次返回null
        } catch (error) {
            console.error(`检查批次${batch.batch_id}分析结果失败:`, error);
            return null;
        }
    });
    
    // 等待所有批次检查完成
    const batchResults = await Promise.all(batchCheckPromises);
    const batchesWithResults = batchResults.filter(batch => batch !== null);
    
    // 如果没有批次有分析结果，或只有一个批次，不显示批次按钮
    if (batchesWithResults.length <= 1) {
        showSuccess(`分析完成！共处理 ${totalCount} 篇论文`);
        return;
    }
    
    // 更新batchInfo，只保留有结果的批次
    const filteredBatchInfo = {
        ...batchInfo,
        batches: batchesWithResults,
        batch_count: batchesWithResults.length
    };
    window.AppState.currentBatchInfo = filteredBatchInfo;
    
    // 创建按钮容器
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'batch-filter-container';
    buttonContainer.style.marginTop = '10px';
    
    // 添加"显示全部"按钮
    const showAllBtn = document.createElement('button');
    showAllBtn.textContent = '显示全部';
    showAllBtn.className = 'batch-filter-btn active';
    showAllBtn.onclick = () => showBatchArticles('all', allArticles, totalCount, filteredBatchInfo);
    buttonContainer.appendChild(showAllBtn);
    
    // 只添加有分析结果的批次按钮
    batchesWithResults.forEach(batch => {
        const batchBtn = document.createElement('button');
        batchBtn.textContent = `批次${batch.batch_id} (${batch.batch_label})`;
        batchBtn.className = 'batch-filter-btn';
        batchBtn.onclick = () => showBatchArticles(batch.batch_id, allArticles, totalCount, filteredBatchInfo);
        buttonContainer.appendChild(batchBtn);
    });
    
    // 创建带按钮的成功消息
    const successDiv = document.getElementById('success');
    successDiv.innerHTML = '';
    
    const messageSpan = document.createElement('span');
    messageSpan.textContent = `分析完成！共处理 ${totalCount} 篇论文`;
    successDiv.appendChild(messageSpan);
    successDiv.appendChild(buttonContainer);
    successDiv.style.display = 'block';
}

// 创建批次筛选按钮
async function createBatchFilterButtons(allArticles, totalCount, batchInfo) {
    // 存储全局变量供按钮回调使用
    window.AppState.currentBatchInfo = batchInfo;
    window.AppState.currentAllArticles = allArticles;
    
    // 检查每个批次是否有分析结果
    const selectedDate = document.getElementById('dateSelect').value;
    const selectedCategory = document.getElementById('categorySelect').value;
    const batchesWithResults = [];
    
    for (const batch of batchInfo.batches) {
        try {
            const response = await fetch('/api/get_analysis_results', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    date: selectedDate,
                    category: selectedCategory,
                    range_type: 'full',
                    batch_filter: batch.paper_ids
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.articles && data.articles.length > 0) {
                    // 只保留有分析结果的批次
                    batchesWithResults.push({
                        ...batch,
                        analysis_count: data.articles.length
                    });
                }
            }
        } catch (error) {
            console.error(`检查批次${batch.batch_id}分析结果失败:`, error);
        }
    }
    
    // 如果没有批次有分析结果，或只有一个批次，不显示批次按钮
    if (batchesWithResults.length <= 1) {
        const successDiv = document.getElementById('success');
        successDiv.innerHTML = '';
        const messageSpan = document.createElement('span');
        messageSpan.textContent = `分析完成！共处理 ${totalCount} 篇论文`;
        successDiv.appendChild(messageSpan);
        successDiv.style.display = 'block';
        return;
    }
    
    // 更新batchInfo，只保留有结果的批次
    const filteredBatchInfo = {
        ...batchInfo,
        batches: batchesWithResults,
        batch_count: batchesWithResults.length
    };
    window.AppState.currentBatchInfo = filteredBatchInfo;
    
    // 创建按钮容器
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'batch-filter-container';
    buttonContainer.style.marginTop = '10px';
    
    // 添加"显示全部"按钮
    const showAllBtn = document.createElement('button');
    showAllBtn.textContent = '显示全部';
    showAllBtn.className = 'batch-filter-btn active';
    showAllBtn.onclick = () => showBatchArticles('all', allArticles, totalCount, filteredBatchInfo);
    buttonContainer.appendChild(showAllBtn);
    
    // 只添加有分析结果的批次按钮
    batchesWithResults.forEach(batch => {
        const batchBtn = document.createElement('button');
        batchBtn.textContent = `批次${batch.batch_id} (${batch.batch_label})`;
        batchBtn.className = 'batch-filter-btn';
        batchBtn.onclick = () => showBatchArticles(batch.batch_id, allArticles, totalCount, filteredBatchInfo);
        buttonContainer.appendChild(batchBtn);
    });
    
    // 创建带按钮的成功消息
    const successDiv = document.getElementById('success');
    successDiv.innerHTML = '';
    
    const messageSpan = document.createElement('span');
    messageSpan.textContent = `分析完成！共处理 ${totalCount} 篇论文`;
    successDiv.appendChild(messageSpan);
    successDiv.appendChild(buttonContainer);
    successDiv.style.display = 'block';
}

// 显示指定批次的论文
async function showBatchArticles(batchId, allArticles, totalCount, batchInfo) {
    if (batchId === 'all') {
        // 显示加载状态
        showBatchLoadingIndicator('all', true);
        
        // 显示所有文章（不清理消息）
        displayAnalysisResultsWithoutClearingMessages(allArticles);
        updateBatchButtonStates('all');
        
        // 保持按钮显示，只更新消息文本
        const successDiv = document.getElementById('success');
        const messageSpan = successDiv.querySelector('span');
        if (messageSpan) {
            messageSpan.textContent = `已加载全部 ${totalCount} 篇论文`;
        }
        
        // 恢复按钮状态
        showBatchLoadingIndicator('all', false);
        return;
    }
    
    // 找到指定批次
    const batch = batchInfo.batches.find(b => b.batch_id === batchId);
    if (!batch) {
        showError('找不到指定批次');
        return;
    }
    
    try {
        // 显示加载状态
        showBatchLoadingIndicator(batchId, true);
        
        // 请求该批次的分析结果
        const selectedDate = document.getElementById('dateSelect').value;
        const selectedCategory = document.getElementById('categorySelect').value;
        
        const response = await fetch('/api/get_analysis_results', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date: selectedDate,
                category: selectedCategory,
                range_type: 'full',
                batch_filter: batch.paper_ids
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            displayAnalysisResultsWithoutClearingMessages(data.articles);
            updateBatchButtonStates(batchId);
            
            // 保持按钮显示，只更新消息文本
            const successDiv = document.getElementById('success');
            const messageSpan = successDiv.querySelector('span');
            if (messageSpan) {
                messageSpan.textContent = `已加载批次${batchId}，共${data.articles.length}篇论文（${batch.batch_label}）`;
            }
        } else {
            showError('获取批次论文失败');
        }
    } catch (error) {
        console.error('获取批次论文失败:', error);
        showError('获取批次论文时出现网络错误');
    } finally {
        // 恢复按钮状态
        showBatchLoadingIndicator(batchId, false);
    }
}

// 更新批次按钮状态
function updateBatchButtonStates(activeBatchId) {
    const buttons = document.querySelectorAll('.batch-filter-btn');
    buttons.forEach(btn => {
        btn.classList.remove('active');
        if ((activeBatchId === 'all' && btn.textContent === '显示全部') ||
            (activeBatchId !== 'all' && btn.textContent.includes(`批次${activeBatchId}`))) {
            btn.classList.add('active');
        }
    });
}

// 清除之前的批次按钮
function clearPreviousBatchButtons() {
    const successDiv = document.getElementById('success');
    if (successDiv) {
        const batchContainer = successDiv.querySelector('.batch-filter-container');
        if (batchContainer) {
            batchContainer.remove();
            console.log('🧹 已清除之前的批次按钮');
        }
        
        // 清除批次相关的全局状态
        if (window.AppState) {
            delete window.AppState.currentBatchInfo;
            delete window.AppState.currentAllArticles;
        }
    }
}

// 添加加载状态提示
function showBatchLoadingIndicator(batchId, isLoading = true) {
    const buttons = document.querySelectorAll('.batch-filter-btn');
    buttons.forEach(btn => {
        if ((batchId === 'all' && btn.textContent === '显示全部') ||
            (batchId !== 'all' && btn.textContent.includes(`批次${batchId}`))) {
            if (isLoading) {
                btn.style.opacity = '0.6';
                btn.style.cursor = 'wait';
                btn.disabled = true;
            } else {
                btn.style.opacity = '1';
                btn.style.cursor = 'pointer';
                btn.disabled = false;
            }
        }
    });
}