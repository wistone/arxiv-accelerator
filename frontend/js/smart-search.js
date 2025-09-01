/**
 * 智能搜索功能模块
 * 处理基于arXiv ID文本的智能搜索
 */

// 智能搜索状态管理
const smartSearchState = {
    isSearching: false,
    currentResults: null
};

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
            
            // 更新URL状态，使搜索结果可分享
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
        button.textContent = '🔍 开始搜索';
        hideLoading();
    }
}

/**
 * 处理智能搜索成功结果
 */
function handleSmartSearchSuccess(result) {
    const performance = result.performance || {};
    
    console.log('handleSmartSearchSuccess called with:', result);
    
    // 保存结果到状态
    smartSearchState.currentResults = result;
    
    // 直接显示文章表格 - 与search_articles完全相同的方式
    if (result.articles && result.articles.length > 0) {
        displaySmartSearchArticles(result);
        
        // 显示分享按钮
        const shareBtn = document.getElementById('shareSmartSearchBtn');
        if (shareBtn) {
            shareBtn.style.display = 'inline-block';
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
    console.log('displaySmartSearchArticles called with result:', result);
    
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
            成功加载智能搜索数据，共 ${result.total} 篇文章
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
    
    // 清除缓存的文章数据
    delete window.smartSearchArticles;
}

/**
 * 清空智能搜索结果
 */
function clearSmartSearchResults() {
    const input = document.getElementById('smartSearchInput');
    
    input.value = '';
    smartSearchState.currentResults = null;
    
    // 清空主要内容区域
    const contentDiv = document.getElementById('content');
    if (contentDiv) {
        contentDiv.innerHTML = '';
    }
    
    // 隐藏分享按钮
    const shareBtn = document.getElementById('shareSmartSearchBtn');
    if (shareBtn) {
        shareBtn.style.display = 'none';
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
 * 分享智能搜索结果
 */
function shareSmartSearch() {
    try {
        const currentUrl = window.location.href;
        
        // 复制到剪贴板
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(currentUrl).then(() => {
                showAlert('🎉 搜索结果链接已复制到剪贴板！', 'success');
            }).catch(err => {
                console.error('复制到剪贴板失败:', err);
                fallbackCopyToClipboard(currentUrl);
            });
        } else {
            // 降级方案
            fallbackCopyToClipboard(currentUrl);
        }
        
    } catch (error) {
        console.error('分享功能错误:', error);
        showAlert('分享失败，请手动复制URL', 'warning');
    }
}

/**
 * 降级复制到剪贴板方案
 */
function fallbackCopyToClipboard(text) {
    try {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        const result = document.execCommand('copy');
        textArea.remove();
        
        if (result) {
            showAlert('🎉 搜索结果链接已复制到剪贴板！', 'success');
        } else {
            // 显示URL让用户手动复制
            showUrlDialog(text);
        }
    } catch (err) {
        console.error('降级复制方案失败:', err);
        showUrlDialog(text);
    }
}

/**
 * 显示URL对话框供用户手动复制
 */
function showUrlDialog(url) {
    // 创建模态对话框
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 10000;
    `;
    
    modal.innerHTML = `
        <div style="
            background: white;
            padding: 20px;
            border-radius: 8px;
            max-width: 600px;
            width: 90%;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        ">
            <h3 style="margin: 0 0 15px 0; color: #333;">🔗 分享链接</h3>
            <p style="margin: 0 0 15px 0; color: #666;">请手动复制以下链接：</p>
            <textarea readonly style="
                width: 100%;
                height: 80px;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-family: monospace;
                font-size: 12px;
                resize: none;
                box-sizing: border-box;
            ">${url}</textarea>
            <div style="text-align: right; margin-top: 15px;">
                <button onclick="this.closest('.modal-container').remove()" style="
                    padding: 8px 16px;
                    background: #007bff;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                ">关闭</button>
            </div>
        </div>
    `;
    
    modal.className = 'modal-container';
    document.body.appendChild(modal);
    
    // 自动选中文本
    const textarea = modal.querySelector('textarea');
    textarea.focus();
    textarea.select();
    
    // 点击背景关闭
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
}