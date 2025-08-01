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
    
    // 首先检查是否已存在分析结果文件
    try {
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

        if (response.ok && data.exists) {
            // 如果分析文件已存在，显示选择弹窗
            showAnalysisOptions(data);
            return;
        }
    } catch (error) {
        console.log('检查分析文件时出错，继续进行新分析:', error);
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
    
    // 先尝试加载现有结果
    try {
        const response = await fetch('/api/get_analysis_results', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date: selectedDate,
                category: selectedCategory,
                range_type: selectedRange
            })
        });

        if (response.ok) {
            const data = await response.json();
            closeModal();
            
            // 检查是否是分析失败的结果
            if (data.is_analysis_failed) {
                displayAnalysisFailure(data.fail_info);
                showError(`分析失败：${data.fail_info.total_papers} 篇论文的AI分析都失败了`);
            } else {
                displayAnalysisResults(data.articles);
                showSuccess(`成功加载 ${selectedRange} 分析结果，共 ${data.total} 篇论文`);
            }
            
            // 更新URL状态
            updateUrlState('analysis', selectedDate, selectedCategory, selectedRange);
            return;
        }
    } catch (error) {
        console.log('加载现有结果失败，开始重新生成:', error);
    }
    
    // 如果加载失败，开始重新生成
    const testCountInt = testCount === '' ? null : parseInt(testCount);
    await startNewAnalysis(selectedDate, selectedCategory, testCountInt);
}

async function startNewAnalysis(selectedDate, selectedCategory, testCount) {
    // 隐藏测试选项，显示进度条
    document.getElementById('testOptions').style.display = 'none';
    document.getElementById('progressContainer').style.display = 'block';
    document.getElementById('currentPaper').style.display = 'block';
    
    window.AppState.analysisStartTime = Date.now();
    window.AppState.lastProgressUpdate = Date.now();
    
    try {
        const response = await fetch('/api/analyze_papers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date: selectedDate,
                category: selectedCategory,
                test_count: testCount
            })
        });

        if (!response.ok) {
            throw new Error('分析请求失败');
        }

        // 开始SSE连接和备用检查机制
        startSSEConnection(selectedDate, selectedCategory, testCount);
        startProgressBackupCheck(selectedDate, selectedCategory);

    } catch (error) {
        showError('分析启动失败: ' + error.message);
        console.error('分析错误:', error);
    }
}

async function loadAnalysisResults(rangeTypeToLoad = 'full') {
    const selectedDate = document.getElementById('dateSelect').value;
    const selectedCategory = document.getElementById('categorySelect').value;
    
    try {
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
                showSuccess(`分析完成！共处理 ${data.total} 篇论文`);
            }
            
            // 更新URL状态
            updateUrlState('analysis', selectedDate, selectedCategory, rangeTypeToLoad);
        } else {
            showError(data.error || '加载分析结果失败');
        }
    } catch (error) {
        showError('加载分析结果时出现网络错误');
        console.error('加载分析结果错误:', error);
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