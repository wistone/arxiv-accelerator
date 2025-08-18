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
                displayAnalysisResults(data.articles);
                
                // 创建筛选按钮配置
                const buttonConfig = {
                    text: '筛选当日18:00后的补充论文',
                    onclick: () => filterAfter18Papers(data.articles, data.total)
                };
                
                showSuccess(`分析完成！共处理 ${data.total} 篇论文`, buttonConfig);
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

// 筛选18:00后的补充论文
function filterAfter18Papers(allArticles, totalCount) {
    if (!allArticles || allArticles.length === 0) {
        showError('没有论文数据可供筛选');
        return;
    }
    
    // 筛选出update_time在18:00:00至23:59:59之间的论文
    const after18Articles = allArticles.filter(article => {
        if (!article.update_time) return false;
        
        // 解析时间字符串 (格式应该是 HH:MM:SS)
        const timeStr = article.update_time;
        const timeMatch = timeStr.match(/^(\d{2}):(\d{2}):(\d{2})$/);
        
        if (!timeMatch) return false;
        
        const hours = parseInt(timeMatch[1]);
        const minutes = parseInt(timeMatch[2]);
        const seconds = parseInt(timeMatch[3]);
        
        // 检查是否在18:00:00至23:59:59之间
        return hours >= 18 && hours <= 23;
    });
    
    // 显示筛选后的结果
    displayAnalysisResults(after18Articles);
    
    // 更新成功消息，添加"显示当天所有论文"按钮
    const buttonConfig = {
        text: '显示当天所有论文',
        onclick: () => showAllDayPapers(allArticles, totalCount)
    };
    
    showSuccess(`筛选完成！共找到 ${after18Articles.length} 篇18:00后的补充论文（全天共${totalCount}篇）`, buttonConfig);
}

// 显示当天所有论文
function showAllDayPapers(allArticles, totalCount) {
    if (!allArticles || allArticles.length === 0) {
        showError('没有论文数据可供显示');
        return;
    }
    
    // 显示所有论文
    displayAnalysisResults(allArticles);
    
    // 恢复"筛选当日18:00后的补充论文"按钮
    const buttonConfig = {
        text: '筛选当日18:00后的补充论文',
        onclick: () => filterAfter18Papers(allArticles, totalCount)
    };
    
    showSuccess(`分析完成！共处理 ${totalCount} 篇论文`, buttonConfig);
}