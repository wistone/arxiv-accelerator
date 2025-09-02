/**
 * 智能搜索功能模块
 * 处理基于arXiv ID文本的智能搜索
 */

// 智能搜索状态管理
const smartSearchState = {
    isSearching: false,
    currentResults: null,
    isAnalyzing: false,
    currentAnalysisTask: null,
    analysisProgress: null
};

// 确保全局可访问
window.smartSearchState = smartSearchState;

/**
 * 开始智能搜索
 */
async function startSmartSearch() {
    const input = document.getElementById('smartSearchInput');
    const button = document.querySelector('.smart-search-section .btn');
    
    const inputText = input.value.trim();
    
    if (!inputText) {
        showAlert('请输入包含arXiv ID的文本内容', 'warning');
        return;
    }
    
    // 防止重复提交
    if (smartSearchState.isSearching) {
        return;
    }
    
    try {
        // 设置搜索状态
        smartSearchState.isSearching = true;
        button.disabled = true;
        button.textContent = '搜索中...';
        
        // 显示加载状态
        showLoading();
        
        // 清除之前的日期筛选器
        clearPreviousDateFilter();
        
        // 发送请求到后端
        const response = await fetch('/api/smart_search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text_content: inputText
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        // 处理响应
        if (result.success === true) {
            handleSmartSearchSuccess(result);
            
            // 更新URL状态
            if (typeof updateSmartSearchUrlState !== 'undefined') {
                updateSmartSearchUrlState(inputText, 'all');
            }
        } else {
            handleSmartSearchError(result.message || '搜索失败');
        }
        
    } catch (error) {
        console.error('智能搜索错误:', error);
        handleSmartSearchError(error.message || '网络请求失败，请稍后重试');
    } finally {
        // 恢复按钮状态
        smartSearchState.isSearching = false;
        button.disabled = false;
        button.textContent = '🔍 搜索文章列表';
        hideLoading();
    }
}

/**
 * 处理智能搜索成功结果
 */
function handleSmartSearchSuccess(result) {
    const performance = result.performance || {};
    
    // 保存结果到状态
    smartSearchState.currentResults = result;
    
    // 直接显示文章表格 - 与search_articles完全相同的方式
    if (result.articles && result.articles.length > 0) {
        displaySmartSearchArticles(result);
        
        // 显示并启用分析按钮，让用户可以查看分析状态
        const analyzeBtn = document.getElementById('smartAnalyzeBtn');
        if (analyzeBtn) {
            analyzeBtn.style.display = 'inline-block';
            analyzeBtn.disabled = false; // 启用按钮，让用户可以点击查看分析选项
        }
    }
    
    // 生成类似search_articles的成功消息
    let successMessage = `智能搜索完成！成功加载 ${result.total} 篇文章`;
    if (performance.not_exist_count > 0) {
        const notFoundList = result.not_exist_ids ? result.not_exist_ids.slice(0, 3).join(', ') : '';
        const moreCount = result.not_exist_ids ? Math.max(0, result.not_exist_ids.length - 3) : 0;
        successMessage += `，${performance.not_exist_count} 篇文章找不到，arXiv ID如下: ${notFoundList}`;
        if (moreCount > 0) {
            successMessage += ` 等${moreCount}篇...`;
        }
    }
    
    // 显示成功提示 - 使用与search.js相同的showSuccess函数
    if (typeof showSuccess === 'function') {
        showSuccess(successMessage);
    } else {
        showAlert(successMessage, 'success');
    }
}

/**
 * 处理智能搜索错误
 */
function handleSmartSearchError(errorMessage) {
    // 使用与search.js相同的错误显示方式
    if (typeof showError === 'function') {
        showError('智能搜索失败：' + errorMessage);
    } else {
        showAlert('智能搜索失败：' + errorMessage, 'error');
    }
}

/**
 * 显示智能搜索文章列表（包含日期列和筛选功能）
 */
function displaySmartSearchArticles(result) {
    // 为文章添加序号
    const articlesWithNumbers = result.articles.map((article, index) => ({
        ...article,
        number: index + 1
    }));
    
    // 显示智能搜索专用的表格（包含日期列）
    displaySmartSearchTable(articlesWithNumbers);
    
    // 添加日期筛选功能
    addDateFilterForSmartSearch(articlesWithNumbers);
    
    // 更新统计信息
    const statsDiv = document.getElementById('stats');
    const totalArticlesSpan = document.getElementById('totalArticles');
    if (statsDiv && totalArticlesSpan) {
        totalArticlesSpan.textContent = result.total;
        statsDiv.style.display = 'block';
    }
}

/**
 * 显示智能搜索专用的表格（包含日期列）
 */
function displaySmartSearchTable(articles, skipHeaderInit = false) {
    const tableBody = document.getElementById('tableBody');
    tableBody.innerHTML = '';

    // 只在首次加载时更新表头（避免筛选时重新初始化）
    if (!skipHeaderInit) {
        const tableHead = document.querySelector('#arxivTable thead tr');
        tableHead.innerHTML = `
        <th class="number-cell">序号</th>
        <th class="date-cell date-filterable" onclick="toggleDateFilter(event)">
            日期 
            <span class="filter-arrow">▼</span>
            <div class="date-filter-dropdown" id="dateFilterDropdown" style="display: none;">
                <div class="filter-options">
                    <label class="filter-option">
                        <input type="checkbox" value="all" checked> 全部日期
                    </label>
                    <div class="filter-divider"></div>
                    <div id="dateFilterOptions">
                        <!-- 日期选项将动态插入 -->
                    </div>
                </div>
                <div class="filter-actions">
                    <button class="btn-small apply-filter" onclick="applyColumnDateFilter(event)">确定</button>
                    <button class="btn-small cancel-filter" onclick="cancelColumnDateFilter(event)">取消</button>
                </div>
            </div>
        </th>
        <th>标题</th>
        <th class="authors-cell">作者</th>
        <th class="abstract-cell">摘要</th>
    `;
    }

    articles.forEach(article => {
        const row = document.createElement('tr');
        
        // 格式化日期显示
        const displayDate = article.update_date || '未知';
        
        row.innerHTML = `
            <td class="number-cell">${article.number}</td>
            <td class="date-cell" data-date="${article.update_date}">
                <div class="date-content">${displayDate}</div>
            </td>
            <td class="title-cell">
                <div class="title-content">${article.title}</div>
                <div class="title-link">
                    <a href="${convertToPdfLink(article.link)}" target="_blank">查看链接</a>
                </div>
            </td>
            <td class="authors-cell">
                <div class="authors-content" id="authors-${article.number}">
                    ${article.authors}
                </div>
                ${article.authors.length > 100 ? `<span class="authors-toggle" onclick="toggleAuthors('authors-${article.number}')">展开/收起</span>` : ''}
            </td>
            <td class="abstract-cell">
                <div class="abstract-content" id="abstract-${article.number}">
                    ${article.abstract}
                </div>
                <span class="abstract-toggle" onclick="toggleAbstract('abstract-${article.number}')">
                    展开/收起
                </span>
            </td>
        `;
        tableBody.appendChild(row);
    });

    document.getElementById('tableContainer').style.display = 'block';
}

/**
 * 为智能搜索添加日期筛选功能（仅Excel风格列头筛选）
 */
function addDateFilterForSmartSearch(articles) {
    // 保存原始文章数据以供筛选使用
    window.smartSearchArticles = articles;
    
    // 初始化Excel风格的日期筛选下拉菜单
    initializeDateFilterDropdown(articles);
}

// 注意：以下旧版筛选函数已被Excel风格的列头筛选取代，保留作为备用
// 主要筛选功能现在通过点击列头的下拉菜单实现

/**
 * 手动创建文章表格（fallback方法）
 */
function displayArticlesTableManually(result) {
    const contentDiv = document.getElementById('content');
    if (!contentDiv) return;
    
    // 创建成功提示条
    const successBanner = `
        <div class="alert alert-success" style="background-color: #d1edcc; border: 1px solid #c3e6cb; color: #155724; padding: 12px; border-radius: 8px; margin-bottom: 20px;">
            智能搜索完成！成功加载共 ${result.total} 篇文章
        </div>
    `;
    
    // 创建统计信息
    const statsHtml = `
        <div id="stats" class="stats" style="display: block;">
            <div class="stat-item">
                <span>📄 文章总数:</span>
                <span class="stat-value">${result.total}</span>
            </div>
        </div>
    `;
    
    // 创建表格
    let tableHtml = `
        <div id="tableContainer" class="table-container" style="display: block;">
            <table class="arxiv-table" id="arxivTable">
                <thead>
                    <tr>
                        <th class="number-cell">序号</th>
                        <th class="id-cell">ID</th>
                        <th>标题</th>
                        <th>作者</th>
                        <th>摘要</th>
                        <th>链接</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    result.articles.forEach((article, index) => {
        const abstractText = article.abstract ? article.abstract.substring(0, 200) + '...' : '无摘要';
        const authorsText = article.authors || '未知作者';
        
        tableHtml += `
            <tr>
                <td class="number-cell">${index + 1}</td>
                <td class="id-cell">
                    <a href="https://arxiv.org/abs/${article.arxiv_id}" target="_blank" class="arxiv-link">
                        ${article.arxiv_id}
                    </a>
                </td>
                <td class="title-cell">
                    <a href="${article.link}" target="_blank" class="paper-title">
                        ${article.title}
                    </a>
                </td>
                <td class="authors-cell">${authorsText}</td>
                <td class="abstract-cell">${abstractText}</td>
                <td class="links-cell">
                    <a href="${article.link}" target="_blank" class="btn-link">查看论文</a>
                </td>
            </tr>
        `;
    });
    
    tableHtml += `
                </tbody>
            </table>
        </div>
    `;
    
    // 组合所有内容
    contentDiv.innerHTML = successBanner + statsHtml + tableHtml;
}

/**
 * 清除之前的日期筛选器
 */
function clearPreviousDateFilter() {
    // 隐藏Excel风格的筛选下拉菜单
    hideAllFilterDropdowns();
    
    // 清除普通搜索的批次按钮显示区域
    const batchContainers = document.querySelectorAll('.batch-filter-container');
    batchContainers.forEach(container => {
        container.remove();
        console.log('🧹 已清除批次按钮容器');
    });
    
    // 也清除可能的ID容器
    const batchContainer = document.getElementById('batchContainer');
    if (batchContainer) {
        batchContainer.style.display = 'none';
        batchContainer.innerHTML = '';
    }
    
    // 清除论文总数显示
    const paperCountElement = document.getElementById('paperCount');
    if (paperCountElement) {
        paperCountElement.style.display = 'none';
        paperCountElement.innerHTML = '';
    }
    
    // 清除缓存的文章数据
    delete window.smartSearchArticles;
    
    // 清除主表格内容
    const tableBody = document.getElementById('tableBody');
    if (tableBody) {
        tableBody.innerHTML = '';
    }
    
    // 清除成功消息显示
    const successMessage = document.querySelector('.success-message');
    if (successMessage) {
        successMessage.style.display = 'none';
    }
    
    // 禁用普通搜索的分析按钮
    const analyzeBtn = document.getElementById('analyzeBtn');
    if (analyzeBtn) {
        analyzeBtn.disabled = true;
        analyzeBtn.textContent = '📊 分析';
    }
    
    // 重置AppState中的普通搜索状态
    if (window.AppState) {
        window.AppState.hasSearched = false;
        window.AppState.currentArticles = [];
        // 清除批次相关状态
        delete window.AppState.currentBatchInfo;
    }
}

/**
 * 清空智能搜索结果
 */
function clearSmartSearchResults() {
    const input = document.getElementById('smartSearchInput');
    
    input.value = '';
    smartSearchState.currentResults = null;
    smartSearchState.isAnalyzing = false;
    smartSearchState.currentAnalysisTask = null;
    smartSearchState.analysisProgress = null;
    
    // 清空主要内容区域
    const contentDiv = document.getElementById('content');
    if (contentDiv) {
        contentDiv.innerHTML = '';
    }
    
    // 隐藏分析按钮
    const analyzeBtn = document.getElementById('smartAnalyzeBtn');
    if (analyzeBtn) {
        analyzeBtn.style.display = 'none';
        analyzeBtn.disabled = true;
    }
    
    // 清除日期筛选器
    clearPreviousDateFilter();
}

/**
 * 显示提示信息
 */
function showAlert(message, type = 'info') {
    // 复用现有的提示系统
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        color: white;
        font-weight: 600;
        z-index: 10000;
        max-width: 400px;
        word-wrap: break-word;
    `;
    
    // 根据类型设置颜色
    switch (type) {
        case 'success':
            alertDiv.style.backgroundColor = '#28a745';
            break;
        case 'error':
            alertDiv.style.backgroundColor = '#dc3545';
            break;
        case 'warning':
            alertDiv.style.backgroundColor = '#ffc107';
            alertDiv.style.color = '#000';
            break;
        default:
            alertDiv.style.backgroundColor = '#667eea';
    }
    
    document.body.appendChild(alertDiv);
    
    // 3秒后自动移除
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.parentNode.removeChild(alertDiv);
        }
    }, 3000);
}

/**
 * ==============================
 * Excel风格的日期筛选功能
 * ==============================
 */

/**
 * 初始化Excel风格的日期筛选下拉菜单
 */
function initializeDateFilterDropdown(articles) {
    // 获取所有唯一日期
    const uniqueDates = [...new Set(articles.map(article => article.update_date).filter(date => date))].sort().reverse();
    
    // 填充日期选项到下拉菜单
    const dateOptionsDiv = document.getElementById('dateFilterOptions');
    if (dateOptionsDiv && uniqueDates.length > 0) {
        dateOptionsDiv.innerHTML = uniqueDates.map(date => `
            <label class="filter-option">
                <input type="checkbox" value="${date}" checked> ${date}
            </label>
        `).join('');
    }
}

/**
 * 切换日期筛选下拉菜单的显示/隐藏
 */
function toggleDateFilter(event) {
    event.stopPropagation(); // 阻止事件冒泡
    
    const dropdown = document.getElementById('dateFilterDropdown');
    const isVisible = dropdown.style.display !== 'none';
    
    // 隐藏所有其他可能打开的筛选下拉菜单
    hideAllFilterDropdowns();
    
    if (!isVisible) {
        dropdown.style.display = 'block';
        // 添加点击外部关闭的事件监听
        setTimeout(() => {
            document.addEventListener('click', closeDateFilterOnOutsideClick);
        }, 0);
    }
}

/**
 * 隐藏所有筛选下拉菜单
 */
function hideAllFilterDropdowns() {
    const dropdowns = document.querySelectorAll('.date-filter-dropdown');
    dropdowns.forEach(dropdown => {
        dropdown.style.display = 'none';
    });
    
    // 移除外部点击监听
    document.removeEventListener('click', closeDateFilterOnOutsideClick);
}

/**
 * 点击外部关闭日期筛选菜单
 */
function closeDateFilterOnOutsideClick(event) {
    const dropdown = document.getElementById('dateFilterDropdown');
    const dateHeader = event.target.closest('.date-filterable');
    
    if (!dropdown.contains(event.target) && !dateHeader) {
        hideAllFilterDropdowns();
    }
}

/**
 * 应用列头的日期筛选
 */
function applyColumnDateFilter(event) {
    event.stopPropagation();
    
    if (!window.smartSearchArticles) {
        return;
    }
    
    // 获取选中的日期
    const checkboxes = document.querySelectorAll('#dateFilterOptions input[type="checkbox"]');
    const allCheckbox = document.querySelector('#dateFilterDropdown input[value="all"]');
    
    let selectedDates = [];
    let showAll = allCheckbox.checked;
    
    if (!showAll) {
        checkboxes.forEach(cb => {
            if (cb.checked) {
                selectedDates.push(cb.value);
            }
        });
    }
    
    // 筛选文章
    let filteredArticles;
    if (showAll || selectedDates.length === 0) {
        filteredArticles = window.smartSearchArticles;
    } else {
        filteredArticles = window.smartSearchArticles.filter(article => 
            selectedDates.includes(article.update_date)
        );
    }
    
    // 重新显示筛选后的文章（保持日期筛选器不变）
    displaySmartSearchTable(filteredArticles, true);
    
    // 更新统计信息
    const totalArticlesSpan = document.getElementById('totalArticles');
    if (totalArticlesSpan) {
        totalArticlesSpan.textContent = filteredArticles.length;
    }
    
    // 隐藏下拉菜单
    hideAllFilterDropdowns();
    
    // 更新筛选箭头状态
    updateFilterArrowState(selectedDates.length === 0 || showAll);
    
    // 更新URL状态，包含筛选信息
    if (typeof updateSmartSearchUrlState !== 'undefined') {
        const searchInput = document.getElementById('smartSearchInput');
        if (searchInput && searchInput.value.trim()) {
            const filterState = showAll ? 'all' : selectedDates.join(',');
            updateSmartSearchUrlState(searchInput.value.trim(), filterState);
        }
    }
}

/**
 * 取消列头的日期筛选
 */
function cancelColumnDateFilter(event) {
    event.stopPropagation();
    
    if (!window.smartSearchArticles) {
        return;
    }
    
    // 重置所有复选框为选中状态
    const checkboxes = document.querySelectorAll('#dateFilterDropdown input[type="checkbox"]');
    checkboxes.forEach(cb => {
        cb.checked = true;
    });
    
    // 显示所有文章
    displaySmartSearchTable(window.smartSearchArticles, true);
    
    // 更新统计信息
    const totalArticlesSpan = document.getElementById('totalArticles');
    if (totalArticlesSpan) {
        totalArticlesSpan.textContent = window.smartSearchArticles.length;
    }
    
    // 隐藏下拉菜单
    hideAllFilterDropdowns();
    
    // 重置筛选箭头状态
    updateFilterArrowState(true);
    
    // 更新URL状态为显示全部
    if (typeof updateSmartSearchUrlState !== 'undefined') {
        const searchInput = document.getElementById('smartSearchInput');
        if (searchInput && searchInput.value.trim()) {
            updateSmartSearchUrlState(searchInput.value.trim(), 'all');
        }
    }
}

/**
 * 更新筛选箭头的状态（显示是否有筛选）
 */
function updateFilterArrowState(isShowingAll) {
    const arrow = document.querySelector('.date-filterable .filter-arrow');
    if (arrow) {
        if (isShowingAll) {
            arrow.textContent = '▼';
            arrow.style.color = '#666';
        } else {
            arrow.textContent = '🔽';
            arrow.style.color = '#667eea';
        }
    }
}

/**
 * 处理"全部日期"复选框的改变事件
 */
document.addEventListener('change', function(event) {
    if (event.target.matches('#dateFilterDropdown input[value="all"]')) {
        const isChecked = event.target.checked;
        const otherCheckboxes = document.querySelectorAll('#dateFilterOptions input[type="checkbox"]');
        
        // 如果选中"全部日期"，取消选中其他选项
        if (isChecked) {
            otherCheckboxes.forEach(cb => cb.checked = false);
        }
    } else if (event.target.matches('#dateFilterOptions input[type="checkbox"]')) {
        // 如果选中具体日期，取消选中"全部日期"
        const allCheckbox = document.querySelector('#dateFilterDropdown input[value="all"]');
        if (allCheckbox) {
            allCheckbox.checked = false;
        }
    }
});

/**
 * 分析智能搜索结果
 */
async function analyzeSmartSearchResults() {
    if (!smartSearchState.currentResults || !smartSearchState.currentResults.articles || smartSearchState.currentResults.articles.length === 0) {
        showAlert('请先进行智能搜索获取文章列表', 'warning');
        return;
    }
    
    // 检查是否正在搜索或分析
    if (smartSearchState.isSearching || smartSearchState.isAnalyzing) {
        showAlert('请等待当前操作完成', 'warning');
        return;
    }
    
    // 提取paper_ids
    const paperIds = smartSearchState.currentResults.articles.map(article => article.paper_id).filter(id => id);
    
    if (paperIds.length === 0) {
        showAlert('无法获取论文ID，请重新搜索', 'error');
        return;
    }
    
    
    // 检查已有分析结果
    try {
        // 设置分析状态
        smartSearchState.isAnalyzing = true;
        
        const analyzeBtn = document.getElementById('smartAnalyzeBtn');
        if (analyzeBtn) {
            analyzeBtn.disabled = true;
            analyzeBtn.textContent = '检查中...';
        }
        
        const response = await fetch('/api/check_analysis_exists_by_ids', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                paper_ids: paperIds
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // 显示分析状态
            const analysisStatus = document.getElementById('analysisStatus');
            if (analysisStatus) {
                analysisStatus.innerHTML = `已完成分析 ${data.completed} 篇文章 / 共 ${data.total} 篇文章`;
            }
            
            // 动态更新下拉选项
            updateSmartSearchAnalysisOptions(data);
            
            // 显示分析模态框，但隐藏进度相关区域
            document.getElementById('analysisModal').style.display = 'block';
            document.getElementById('testOptions').style.display = 'block';
            
            // 隐藏进度相关元素，只有开始分析后才显示
            document.getElementById('progressContainer').style.display = 'none';
            document.getElementById('currentPaper').style.display = 'none';
            const analysisSummary = document.getElementById('analysisSummary');
            if (analysisSummary) {
                analysisSummary.style.display = 'none';
            }
            
            // 修改模态框中"开始分析"按钮的onclick事件为智能搜索分析函数
            let startBtn = document.getElementById('startAnalysisBtn');
            const showExistingBtn = document.getElementById('showExistingBtn');
            
            if (startBtn) {
                startBtn.setAttribute('onclick', 'startSmartSearchAnalysis()');
            }
            
            // 启用主分析按钮，让用户可以查看分析状态或开始分析
            const mainAnalyzeBtn = document.getElementById('smartAnalyzeBtn');
            if (mainAnalyzeBtn) {
                mainAnalyzeBtn.disabled = data.total <= 0;
            }

            // 控制按钮状态：当全部分析完成时，禁用"开始分析"，启用"加载已有分析"
            if (data.completed >= data.total && data.total > 0 && data.completed > 0) {
                // 全部分析完成且有分析结果
                if (startBtn) {
                    startBtn.disabled = true;
                    startBtn.textContent = '分析已完成';
                }
                if (showExistingBtn) {
                    showExistingBtn.style.display = 'inline-block';
                    showExistingBtn.style.visibility = 'visible';
                    showExistingBtn.disabled = false;
                    showExistingBtn.textContent = '加载已有分析';
                    showExistingBtn.setAttribute('onclick', 'loadSmartSearchAnalysisResults(); closeModal();');
                }
            } else {
                // 还有未分析的论文或没有分析结果
                if (startBtn) {
                    if (data.total > data.completed && data.total > 0) {
                        startBtn.disabled = false;
                        startBtn.textContent = '开始分析';
                    } else {
                        startBtn.disabled = true;
                        startBtn.textContent = '无需分析';
                    }
                }
                if (showExistingBtn) {
                    if (data.completed > 0) {
                        // 有部分已分析，显示并启用"加载已有分析"按钮
                        showExistingBtn.style.display = 'inline-block';
                        showExistingBtn.style.visibility = 'visible';
                        showExistingBtn.disabled = false;
                        showExistingBtn.textContent = '加载已有分析';
                        showExistingBtn.setAttribute('onclick', 'loadSmartSearchAnalysisResults(); closeModal();');
                    } else {
                        // 没有已分析的，隐藏按钮
                        showExistingBtn.style.display = 'none';
                        showExistingBtn.style.visibility = 'hidden';
                        showExistingBtn.disabled = true;
                    }
                }
            }
            
        } else {
            throw new Error(data.error || '检查分析状态失败');
        }
        
    } catch (error) {
        console.error('检查智能搜索分析状态失败:', error);
        showAlert('检查分析状态失败: ' + error.message, 'error');
        
        // 发生错误时仍然启用主分析按钮，让用户可以重试
        const mainAnalyzeBtn = document.getElementById('smartAnalyzeBtn');
        if (mainAnalyzeBtn) {
            mainAnalyzeBtn.disabled = false;
        }
    } finally {
        // 重置分析状态
        smartSearchState.isAnalyzing = false;
        
        const analyzeBtn = document.getElementById('smartAnalyzeBtn');
        if (analyzeBtn) {
            // 不要在这里重新启用按钮，因为状态检查逻辑已经处理了按钮状态
            analyzeBtn.textContent = '📊 分析';
        }
    }
}

/**
 * 更新智能搜索分析选项
 */
function updateSmartSearchAnalysisOptions(data) {
    const testCountSelect = document.getElementById('testCount');
    if (!testCountSelect) return;
    
    // 清空选项
    testCountSelect.innerHTML = '';
    
    if (data.available_options && data.available_options.length > 0) {
        // 根据后端提供的可用选项动态生成下拉菜单
        data.available_options.forEach(option => {
            const optionElement = document.createElement('option');
            optionElement.value = option === 'full' ? '' : 
                               option === 'top5' ? '5' :
                               option === 'top10' ? '10' :
                               option === 'top20' ? '20' : '';
            optionElement.textContent = option === 'full' ? '全部分析' :
                                      option === 'top5' ? '仅前5篇' :
                                      option === 'top10' ? '仅前10篇' :
                                      option === 'top20' ? '仅前20篇' : option;
            testCountSelect.appendChild(optionElement);
        });
        
        // 设置默认选择第一个可用选项
        testCountSelect.value = data.available_options[0] === 'full' ? '' : 
                               data.available_options[0] === 'top5' ? '5' :
                               data.available_options[0] === 'top10' ? '10' :
                               data.available_options[0] === 'top20' ? '20' : '';
    } else {
        // 如果没有可用选项，显示默认的全部分析选项
        const optionElement = document.createElement('option');
        optionElement.value = '';
        optionElement.textContent = '全部分析';
        testCountSelect.appendChild(optionElement);
    }
    
    console.log('📊 [智能搜索] 可用分析选项:', data.available_options, '总计:', data.total, '已完成:', data.completed);
}

/**
 * 开始智能搜索分析
 */
async function startSmartSearchAnalysis() {
    // 检查状态
    if (smartSearchState.isAnalyzing) {
        showAlert('分析已在进行中，请等待完成', 'warning');
        return;
    }
    
    const testCount = document.getElementById('testCount').value;
    const paperIds = smartSearchState.currentResults.articles.map(article => article.paper_id).filter(id => id);
    
    // 确定分析范围
    const selectedRange = testCount === '5' ? 'top5' :
                         testCount === '10' ? 'top10' :
                         testCount === '20' ? 'top20' : 'full';
    
    const testCountInt = testCount === '' ? null : parseInt(testCount);
    
    // 更新URL状态以反映智能搜索分析状态
    const smartSearchInput = document.getElementById('smartSearchInput');
    if (smartSearchInput && smartSearchInput.value.trim()) {
        // 获取当前筛选状态（如果有的话）
        let currentFilter = 'all';
        try {
            const checkedDates = Array.from(document.querySelectorAll('#dateFilterOptions input[type="checkbox"]:checked')).map(cb => cb.value).filter(v => v !== 'all');
            if (checkedDates.length > 0) {
                currentFilter = checkedDates.join(',');
            }
        } catch (e) {
            // 如果筛选元素不存在，保持默认值
        }
        
        updateSmartSearchAnalysisUrlState(smartSearchInput.value.trim(), selectedRange, currentFilter);
    }
    
    // 清空上一次分析结果状态
    clearPreviousAnalysisResults();
    
    // 隐藏测试选项，显示进度条
    document.getElementById('testOptions').style.display = 'none';
    document.getElementById('progressContainer').style.display = 'block';
    document.getElementById('currentPaper').style.display = 'block';
    
    window.AppState = window.AppState || {};
    window.AppState.analysisStartTime = Date.now();
    window.AppState.lastProgressUpdate = Date.now();
    
    try {
        // 设置分析状态
        smartSearchState.isAnalyzing = true;
        
        const analysisStartBtn = document.getElementById('startAnalysisBtn');
        if (analysisStartBtn) {
            analysisStartBtn.disabled = true;
            analysisStartBtn.textContent = '启动中...';
        }
        
        const overlay = document.getElementById('overlayLoading');
        if (overlay) overlay.style.display = 'flex';
        
        const response = await fetch('/api/analyze_papers_by_ids', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                paper_ids: paperIds,
                range_type: selectedRange,
                workers: 5
            })
        });
        
        if (!response.ok) {
            throw new Error('智能搜索分析请求失败');
        }
        
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        
        // 检查是否所有论文都已分析完成
        if (data.all_analyzed) {
            
            // 隐藏进度界面
            document.getElementById('progressContainer').style.display = 'none';
            document.getElementById('currentPaper').style.display = 'none';
            
            // 显示详细完成信息
            const analysisStatus = document.getElementById('analysisStatus');
            if (analysisStatus) {
                const msg = `所有论文已分析完成！共 ${data.total_papers} 篇论文（已分析${data.analyzed_count}篇，待分析${data.pending_count}篇）`;
                analysisStatus.innerHTML = msg;
            }
            
            // 直接加载结果
            setTimeout(async () => {
                closeModal();
                await loadSmartSearchAnalysisResults();
            }, 1500); // 给用户1.5秒时间看到详细消息
            
            return;
        }
        
        // 使用后端返回的真实task_id
        const taskId = data.task_id;
        
        // 存储当前分析任务ID
        smartSearchState.currentAnalysisTask = taskId;
        startSSEConnection('', '', testCountInt, selectedRange, taskId);
        startProgressFallbackCheck('', '', taskId);
        
        // 分析启动成功，重置UI状态但保持任务跟踪
        smartSearchState.isAnalyzing = false; // 分析任务已启动，重置中间状态
        const resetBtn = document.getElementById('startAnalysisBtn');
        if (resetBtn) {
            resetBtn.disabled = false;
            resetBtn.textContent = '开始分析';
        }
        const successOverlay = document.getElementById('overlayLoading');
        if (successOverlay) successOverlay.style.display = 'none';
        
    } catch (error) {
        console.error('启动智能搜索分析失败:', error);
        showAlert('启动分析失败: ' + error.message, 'error');
        
        // 只有发生错误时才重置分析状态
        smartSearchState.isAnalyzing = false;
        smartSearchState.currentAnalysisTask = null;
        
        const errorResetBtn = document.getElementById('startAnalysisBtn');
        if (errorResetBtn) {
            errorResetBtn.disabled = false;
            errorResetBtn.textContent = '开始分析';
        }
        const errorOverlay = document.getElementById('overlayLoading');
        if (errorOverlay) errorOverlay.style.display = 'none';
    }
}

/**
 * 加载智能搜索分析结果
 */
async function loadSmartSearchAnalysisResults() {
    if (!smartSearchState.currentResults || !smartSearchState.currentResults.articles) {
        return;
    }
    
    const paperIds = smartSearchState.currentResults.articles.map(article => article.paper_id).filter(id => id);
    
    if (paperIds.length === 0) {
        return;
    }
    
    try {
        showLoading();
        
        const response = await fetch('/api/get_analysis_results_by_ids', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                paper_ids: paperIds
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // 使用与普通分析一致的表格显示函数
        if (typeof displayAnalysisResults === 'function') {
            displayAnalysisResults(data.results);
        } else {
            // 如果displayAnalysisResults不存在，使用智能搜索专用函数
            displaySmartSearchAnalysisResults(data);
        }
        
        // 确定加载的分析范围
        const resultCount = data.results ? data.results.length : 0;
        let loadedRange = 'full';
        if (resultCount <= 5) {
            loadedRange = 'top5';
        } else if (resultCount <= 10) {
            loadedRange = 'top10';
        } else if (resultCount <= 20) {
            loadedRange = 'top20';
        }
        
        // 更新URL状态以反映加载的分析结果
        const smartSearchInput = document.getElementById('smartSearchInput');
        if (smartSearchInput && smartSearchInput.value.trim()) {
            // 获取当前筛选状态（如果有的话）
            let currentFilter = 'all';
            try {
                const checkedDates = Array.from(document.querySelectorAll('#dateFilterOptions input[type="checkbox"]:checked')).map(cb => cb.value).filter(v => v !== 'all');
                if (checkedDates.length > 0) {
                    currentFilter = checkedDates.join(',');
                }
            } catch (e) {
                // 如果筛选元素不存在，保持默认值
            }
            
            updateSmartSearchAnalysisUrlState(smartSearchInput.value.trim(), loadedRange, currentFilter);
        }
        
        // 清理状态
        smartSearchState.currentAnalysisTask = null;
        
    } catch (error) {
        console.error('❌ [智能搜索] 加载分析结果失败:', error);
        showError('加载智能搜索分析结果失败: ' + error.message);
    } finally {
        hideLoading();
    }
}

/**
 * 显示智能搜索分析结果表格（与普通分析保持一致的8列格式）
 */
function displaySmartSearchAnalysisResults(data) {
    // 保存当前分析结果到全局状态
    window.AppState = window.AppState || {};
    window.AppState.currentAnalysisArticles = data.results.map((result, index) => ({
        ...result,
        number: index + 1
    }));
    
    // 切换到分析模式（宽屏显示）
    setAnalysisMode();
    
    // 显示成功消息
    showSuccess(`智能搜索分析完成！共分析 ${data.results.length} 篇论文`);
    
    // 更新统计信息
    const passedCount = data.results.filter(r => r.pass_filter).length;
    const rejectedCount = data.results.length - passedCount;
    
    const statsDiv = document.getElementById('stats');
    const totalArticlesSpan = document.getElementById('totalArticles');
    if (statsDiv && totalArticlesSpan) {
        // 扩展统计信息以包含分析结果
        statsDiv.innerHTML = `
            <div class="stat-item">
                <span>📄 分析总数:</span>
                <span class="stat-value">${data.results.length}</span>
            </div>
            <div class="stat-item">
                <span>✅ 通过筛选:</span>
                <span class="stat-value">${passedCount}</span>
            </div>
            <div class="stat-item">
                <span>❌ 未通过筛选:</span>
                <span class="stat-value">${rejectedCount}</span>
            </div>
        `;
        statsDiv.style.display = 'block';
    }
    
    // 设置标准的8列分析表格表头
    const tableBody = document.getElementById('tableBody');
    tableBody.innerHTML = '';

    const tableHead = document.querySelector('#arxivTable thead tr');
    let headerHTML = `
        <th class="number-cell">序号</th>
        <th class="filter-cell">筛选结果</th>
        <th class="score-cell sortable" onclick="sortSmartSearchTable('raw_score')">总分<span class="sort-indicator" id="raw_score_indicator">↕️</span></th>
        <th class="details-cell">详细分析</th>
        <th class="title-cell">标题</th>
        <th class="authors-cell">作者</th>
        <th class="affiliations-cell">作者机构</th>
        <th class="abstract-cell">摘要</th>
    `;
    
    tableHead.innerHTML = headerHTML;

    // 重置排序状态
    window.AppState.sortColumn = '';
    window.AppState.sortDirection = 'asc';
    
    // 显示智能搜索分析结果
    displaySmartSearchSortedResults(data.results);
    
    document.getElementById('tableContainer').style.display = 'block';
}

/**
 * 智能搜索排序表格
 */
function sortSmartSearchTable(column) {
    if (!window.AppState.currentAnalysisArticles || window.AppState.currentAnalysisArticles.length === 0) {
        return;
    }

    // 切换排序方向
    if (window.AppState.sortColumn === column) {
        window.AppState.sortDirection = window.AppState.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        window.AppState.sortColumn = column;
        window.AppState.sortDirection = 'asc';
    }

    // 更新排序指示器
    updateSortIndicators(column, window.AppState.sortDirection);

    // 排序数据
    const sortedArticles = [...window.AppState.currentAnalysisArticles].sort((a, b) => {
        let aValue, bValue;

        try {
            const aAnalysis = JSON.parse(a.analysis_result || '{}');
            const bAnalysis = JSON.parse(b.analysis_result || '{}');
            
            if (column === 'raw_score') {
                aValue = aAnalysis.raw_score || 0;
                bValue = bAnalysis.raw_score || 0;
            } else {
                return 0;
            }
        } catch (e) {
            aValue = 0;
            bValue = 0;
        }

        if (window.AppState.sortDirection === 'asc') {
            return aValue - bValue;
        } else {
            return bValue - aValue;
        }
    });

    // 重新显示排序后的数据
    displaySmartSearchSortedResults(sortedArticles);
}

/**
 * 显示智能搜索排序后的结果
 */
function displaySmartSearchSortedResults(articles) {
    const tableBody = document.getElementById('tableBody');
    tableBody.innerHTML = '';

    articles.forEach((article, index) => {
        const row = document.createElement('tr');
        
        // 解析分析结果JSON
        let analysisObj = {};
        let passFilter = false;
        let rawScore = 0;
        let reason = '';
        let excludeReason = '';
        let detailsHtml = '';
        
        try {
            analysisObj = JSON.parse(article.analysis_result || '{}');
            passFilter = analysisObj.pass_filter || false;
            rawScore = analysisObj.raw_score || 0;
            reason = analysisObj.reason || '';
            excludeReason = analysisObj.exclude_reason || '';
            
            // 构建详细分析显示
            if (passFilter) {
                // 通过筛选的论文显示详细信息
                let coreFeatures = [];
                let plusFeatures = [];
                
                if (analysisObj.core_features) {
                    Object.entries(analysisObj.core_features).forEach(([key, value]) => {
                        if (value > 0) {
                            coreFeatures.push(`${key}: ${value}`);
                        }
                    });
                }
                
                if (analysisObj.plus_features) {
                    Object.entries(analysisObj.plus_features).forEach(([key, value]) => {
                        if (value > 0) {
                            plusFeatures.push(`${key}: ${value}`);
                        }
                    });
                }
                
                detailsHtml = `
                    <div class="analysis-details">
                        <div class="analysis-reason"><strong>评价理由:</strong> ${reason}</div>
                        ${coreFeatures.length > 0 ? `<div class="analysis-core"><strong>核心特征:</strong> ${coreFeatures.join(', ')}</div>` : ''}
                        ${plusFeatures.length > 0 ? `<div class="analysis-plus"><strong>加分特征:</strong> ${plusFeatures.join(', ')}</div>` : ''}
                        <div class="analysis-raw">
                            <span class="raw-json-toggle" onclick="toggleRawJson('smart-raw-${index}')">查看原始JSON ▼</span>
                            <div class="raw-json" id="smart-raw-${index}" style="display: none;">
                                <pre>${JSON.stringify(analysisObj, null, 2)}</pre>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                // 未通过筛选的论文显示排除原因
                detailsHtml = `
                    <div class="analysis-details">
                        <div class="analysis-reason"><strong>排除原因:</strong> ${excludeReason || reason}</div>
                        <div class="analysis-raw">
                            <span class="raw-json-toggle" onclick="toggleRawJson('smart-raw-${index}')">查看原始JSON ▼</span>
                            <div class="raw-json" id="smart-raw-${index}" style="display: none;">
                                <pre>${JSON.stringify(analysisObj, null, 2)}</pre>
                            </div>
                        </div>
                    </div>
                `;
            }
        } catch (e) {
            detailsHtml = `<div class="analysis-error">分析结果解析错误: ${article.analysis_result}</div>`;
        }

        // 设置行样式（通过筛选的论文高亮显示）
        if (passFilter) {
            row.classList.add('passed-filter');
        }

        // 构建行HTML
        let rowHTML = `
            <td class="number-cell">${index + 1}</td>
            <td class="filter-cell">
                <span class="filter-result ${passFilter ? 'passed' : 'rejected'}">
                    ${passFilter ? '✅' : '❌'}
                </span>
            </td>
            <td class="score-cell">
                <div class="score-display">
                    <span class="score-values">${rawScore}</span>
                </div>
            </td>
            <td class="details-cell">
                ${detailsHtml}
            </td>
            <td class="title-cell">
                <div class="title-content">${article.title}</div>
                <div class="title-link">
                    <a href="${convertToPdfLink(article.link)}" target="_blank">查看链接</a>
                </div>
            </td>
            <td class="authors-cell">
                <div class="authors-content" id="smart-authors-${index}">
                    ${article.authors}
                </div>
                ${article.authors && article.authors.length > 120 ? `<span class="authors-toggle" onclick="toggleAuthors('smart-authors-${index}')">展开/收起</span>` : ''}
            </td>
        `;
        
        // 机构列：使用与普通分析相同的渲染逻辑
        rowHTML += renderSmartSearchAffiliationsCell(article.author_affiliation, article, index);
        
        // 添加摘要列（始终最后）
        rowHTML += `
            <td class="abstract-cell">
                <div class="abstract-content" id="smart-abstract-${index}">
                    ${article.abstract}
                </div>
                <span class="abstract-toggle" onclick="toggleAbstract('smart-abstract-${index}')">
                    展开/收起
                </span>
            </td>
        `;
        
        row.innerHTML = rowHTML;
        tableBody.appendChild(row);
    });
}

/**
 * 智能搜索的机构信息渲染（与普通分析保持一致）
 */
function renderSmartSearchAffiliationsCell(affiliationData, article, index) {
    if (!affiliationData || affiliationData === "") {
        // 若筛选通过但机构为空，提供按钮
        try {
            const parsed = JSON.parse(article.analysis_result || '{}');
            if (parsed && parsed.pass_filter) {
                // 与"查看链接"一致的样式
                return `<td class="affiliations-cell">
                    <div class="title-link"><a href="javascript:void(0)" onclick="fetchSmartSearchAffiliations(${article.paper_id}, '${article.link}', ${index})">获取作者机构</a></div>
                </td>`;
            }
        } catch (e) {}
        return `<td class="affiliations-cell"><div class="affiliations-empty">暂无机构信息</div></td>`;
    }
    
    try {
        // 尝试解析JSON格式的机构数据
        let affiliations = [];
        if (typeof affiliationData === 'string') {
            if (affiliationData.startsWith('[') && affiliationData.endsWith(']')) {
                affiliations = JSON.parse(affiliationData);
            } else {
                // 如果不是JSON格式，将字符串按行分割
                affiliations = affiliationData.split('\n').filter(line => line.trim());
            }
        } else if (Array.isArray(affiliationData)) {
            affiliations = affiliationData;
        }
        
        if (affiliations.length === 0) {
            return `<td class="affiliations-cell"><div class="affiliations-empty">未找到机构信息</div></td>`;
        }
        
        // 构建机构列表HTML
        const affiliationsHTML = affiliations.map((affiliation, index) => 
            `<div class="affiliation-item" title="${affiliation}">
                <span class="affiliation-number">${index + 1}.</span>
                <span class="affiliation-text">${affiliation}</span>
            </div>`
        ).join('');
        
        return `<td class="affiliations-cell">
            <div class="affiliations-content">
                <div class="affiliations-count">${affiliations.length} 个机构</div>
                <div class="affiliations-list">
                    ${affiliationsHTML}
                </div>
            </div>
        </td>`;
        
    } catch (error) {
        console.error('解析智能搜索机构信息失败:', error);
        return `<td class="affiliations-cell"><div class="affiliations-error">机构信息格式错误</div></td>`;
    }
}

/**
 * 智能搜索获取作者机构
 */
async function fetchSmartSearchAffiliations(paperId, link, index) {
    const buttonSelector = `[onclick*="fetchSmartSearchAffiliations(${paperId}"]`;
    
    try {
        // 立即显示loading状态
        const buttonElement = document.querySelector(buttonSelector);
        if (buttonElement) {
            buttonElement.style.pointerEvents = 'none';
            buttonElement.textContent = '获取中...';
            buttonElement.style.color = '#999';
        }
        
        // 显示全局loading
        showOverlayLoading();
        
        const startTime = Date.now();
        
        const resp = await fetch('/api/fetch_affiliations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paper_id: paperId, link })
        });
        
        const data = await resp.json();
        const endTime = Date.now();
        const elapsedSeconds = Math.round((endTime - startTime)/1000);
        
        if (resp.ok) {
            if (data.success) {
                // 成功获取机构信息
                updateSmartSearchSingleRowAffiliation(index, data.affiliations);
                showSuccess(`已更新作者机构 (耗时 ${elapsedSeconds}s)`);
            } else {
                // API调用成功但未获取到机构信息
                updateSmartSearchSingleRowAffiliation(index, []); // 显示空机构信息
                showError(data.error || '未获取到机构信息');
            }
        } else {
            // HTTP错误
            showError(data.error || '获取作者机构失败');
        }
    } catch (e) {
        showError('网络错误，获取作者机构失败');
    } finally {
        // 恢复按钮状态
        const buttonElement = document.querySelector(buttonSelector);
        if (buttonElement) {
            buttonElement.style.pointerEvents = 'auto';
            buttonElement.style.color = '';
        }
        hideOverlayLoading();
    }
}

/**
 * 更新智能搜索单行的机构信息
 */
function updateSmartSearchSingleRowAffiliation(rowIndex, affiliations) {
    const tableBody = document.getElementById('tableBody');
    if (!tableBody) {
        console.error('找不到tableBody元素');
        return;
    }
    
    const rows = tableBody.querySelectorAll('tr');
    if (rowIndex >= rows.length) {
        console.error(`行索引${rowIndex}超出范围，共${rows.length}行`);
        return;
    }
    
    const targetRow = rows[rowIndex];
    const affiliationCell = targetRow.querySelector('.affiliations-cell');
    if (!affiliationCell) return;
    
    // 构建机构信息HTML
    if (affiliations && affiliations.length > 0) {
        const affiliationsHTML = affiliations.map((affiliation, index) => 
            `<div class="affiliation-item" title="${affiliation}">
                <span class="affiliation-number">${index + 1}.</span>
                <span class="affiliation-text">${affiliation}</span>
            </div>`
        ).join('');
        
        affiliationCell.innerHTML = `
            <div class="affiliations-content">
                <div class="affiliations-count">${affiliations.length} 个机构</div>
                <div class="affiliations-list">
                    ${affiliationsHTML}
                </div>
            </div>
        `;
    } else {
        // 空机构信息，但不再显示"获取作者机构"按钮
        affiliationCell.innerHTML = '<div class="affiliations-empty">未找到机构信息</div>';
    }
}

/**
 * 清空上一次分析结果的状态显示
 */
function clearPreviousAnalysisResults() {
    
    // 清空进度条
    const progressBarFill = document.getElementById('progressBarFill');
    if (progressBarFill) {
        progressBarFill.style.width = '0%';
    }
    
    // 清空进度文本
    const progressText = document.getElementById('progressText');
    if (progressText) {
        progressText.textContent = '准备开始分析...';
    }
    
    // 清空当前论文信息
    const currentTitle = document.getElementById('currentTitle');
    if (currentTitle) {
        currentTitle.textContent = '等待分析开始...';
    }
    
    const currentAuthors = document.getElementById('currentAuthors');
    if (currentAuthors) {
        currentAuthors.textContent = '';
    }
    
    const currentAbstract = document.getElementById('currentAbstract');
    if (currentAbstract) {
        currentAbstract.textContent = '';
    }
    
    const currentAnalysis = document.getElementById('currentAnalysis');
    if (currentAnalysis) {
        currentAnalysis.textContent = '';
    }
    
    // 清空分析汇总
    const analysisSummary = document.getElementById('analysisSummary');
    if (analysisSummary) {
        analysisSummary.style.display = 'none';
    }
    
    const summaryText = document.getElementById('summaryText');
    if (summaryText) {
        summaryText.textContent = '';
    }
}

// 确保智能搜索函数在全局作用域可用
window.fetchSmartSearchAffiliations = fetchSmartSearchAffiliations;
window.sortSmartSearchTable = sortSmartSearchTable;
window.clearPreviousAnalysisResults = clearPreviousAnalysisResults;