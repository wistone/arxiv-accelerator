/**
 * 表格显示和排序相关函数
 */

function displayAnalysisResults(articles) {
    // 清理所有消息
    hideAllMessages();
    
    // 保存当前分析结果
    window.AppState.currentAnalysisArticles = articles;
    
    // 切换到分析模式（宽屏显示）
    setAnalysisMode();
    
    const tableBody = document.getElementById('tableBody');
    tableBody.innerHTML = '';

    // 更新表头为分析结果格式，添加排序功能
    const tableHead = document.querySelector('#arxivTable thead tr');
    tableHead.innerHTML = `
        <th class="number-cell">序号</th>
        <th class="filter-cell">筛选结果</th>
        <th class="score-cell sortable" onclick="sortTable('raw_score')">
            总分
            <span class="sort-indicator" id="raw_score_indicator">↕️</span>
        </th>
        <th class="details-cell">详细分析</th>
        <th>标题</th>
        <th class="authors-cell">作者</th>
        <th class="abstract-cell">摘要</th>
    `;

    // 重置排序状态
    window.AppState.sortColumn = '';
    window.AppState.sortDirection = 'asc';
    
    // 使用排序后的显示函数来显示数据
    displaySortedResults(articles);
    
    document.getElementById('tableContainer').style.display = 'block';
}

function displayAnalysisFailure(failInfo) {
    // 清理所有消息
    hideAllMessages();
    
    // 保存当前失败信息
    window.AppState.currentAnalysisArticles = [];
    
    // 切换到分析模式（宽屏显示）
    setAnalysisMode();
    
    const tableBody = document.getElementById('tableBody');
    tableBody.innerHTML = '';

    // 更新表头为失败分析格式
    const tableHead = document.querySelector('#arxivTable thead tr');
    tableHead.innerHTML = `
        <th class="number-cell">序号</th>
        <th class="filter-cell">错误信息</th>
        <th class="details-cell">失败详情</th>
        <th>标题</th>
        <th class="authors-cell">作者</th>
        <th class="abstract-cell">摘要</th>
    `;

    // 显示失败摘要信息
    const summaryRow = document.createElement('tr');
    summaryRow.style.backgroundColor = '#fff3cd';
    summaryRow.style.borderLeft = '4px solid #ffc107';
    summaryRow.innerHTML = `
        <td colspan="6" style="padding: 20px; text-align: center;">
            <div style="font-size: 18px; font-weight: bold; color: #856404; margin-bottom: 10px;">
                ❌ 论文分析失败
            </div>
            <div style="color: #856404; margin-bottom: 10px;">
                <strong>失败时间:</strong> ${failInfo.fail_time || '未知'} | 
                <strong>总计论文:</strong> ${failInfo.total_papers || 0} 篇 | 
                <strong>失败数:</strong> ${failInfo.error_count || 0} 篇
            </div>
            <div style="color: #856404; font-size: 14px;">
                所有论文的AI分析都失败了，可能原因：API调用失败、网络连接问题、AI模型服务异常或配置错误
            </div>
            <div style="margin-top: 15px;">
                <button onclick="retryAnalysis()" style="background: #ffc107; color: #856404; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold;">
                    🔄 重新分析
                </button>
            </div>
        </td>
    `;
    tableBody.appendChild(summaryRow);

    // 显示失败的论文列表
    if (failInfo.papers && failInfo.papers.length > 0) {
        failInfo.papers.forEach((paper, index) => {
            const row = document.createElement('tr');
            row.style.backgroundColor = '#f8d7da';
            
            row.innerHTML = `
                <td class="number-cell">${paper.no || index + 1}</td>
                <td class="filter-cell">
                    <span class="filter-result rejected">${paper.error_msg || 'API调用失败'}</span>
                </td>
                <td class="details-cell">
                    <div style="color: #721c24; font-size: 12px;">
                        分析尝试3次均失败<br/>
                        建议检查API配置
                    </div>
                </td>
                <td class="title-cell">
                    <div class="title-content">${paper.title || '未知标题'}</div>
                    ${paper.link ? `<div class="title-link"><a href="${paper.link}" target="_blank">查看原文</a></div>` : ''}
                </td>
                <td class="authors-cell">
                    <div class="authors-content">${paper.authors || '未知作者'}</div>
                </td>
                <td class="abstract-cell">
                    <div class="abstract-content">${(paper.abstract || '无摘要').substring(0, 200)}${(paper.abstract || '').length > 200 ? '...' : ''}</div>
                </td>
            `;
            
            tableBody.appendChild(row);
        });
    }
    
    document.getElementById('tableContainer').style.display = 'block';
}

// 排序函数
function sortTable(column) {
    if (!window.AppState.currentAnalysisArticles || window.AppState.currentAnalysisArticles.length === 0) {
        return;
    }

    // 如果点击的是同一列，切换排序方向
    if (window.AppState.sortColumn === column) {
        window.AppState.sortDirection = window.AppState.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        // 如果点击的是新列，设置为升序
        window.AppState.sortColumn = column;
        window.AppState.sortDirection = 'asc';
    }

    // 更新排序指示器
    updateSortIndicators(column, window.AppState.sortDirection);

    // 排序数据
    const sortedArticles = [...window.AppState.currentAnalysisArticles].sort((a, b) => {
        let aValue, bValue;

        // 解析分析结果获取分数
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

        // 根据排序方向返回比较结果
        if (window.AppState.sortDirection === 'asc') {
            return aValue - bValue;
        } else {
            return bValue - aValue;
        }
    });

    // 重新显示排序后的数据
    displaySortedResults(sortedArticles);
}

// 更新排序指示器
function updateSortIndicators(activeColumn, direction) {
    // 清除所有指示器，恢复默认状态
    const indicators = document.querySelectorAll('.sort-indicator');
    indicators.forEach(indicator => {
        indicator.textContent = '↕️';
        indicator.classList.remove('active');
    });

    // 设置当前列的指示器
    const activeIndicator = document.getElementById(`${activeColumn}_indicator`);
    if (activeIndicator) {
        activeIndicator.textContent = direction === 'asc' ? ' ↑' : ' ↓';
        activeIndicator.classList.add('active');
    }
}

// 显示排序后的结果
function displaySortedResults(articles) {
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
                            <span class="raw-json-toggle" onclick="toggleRawJson('raw-${article.number}')">查看原始JSON ▼</span>
                            <div class="raw-json" id="raw-${article.number}" style="display: none;">
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
                            <span class="raw-json-toggle" onclick="toggleRawJson('raw-${article.number}')">查看原始JSON ▼</span>
                            <div class="raw-json" id="raw-${article.number}" style="display: none;">
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

        row.innerHTML = `
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
                    <a href="${article.link}" target="_blank">查看链接</a>
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
}

function toggleAbstract(elementId) {
    const abstractContent = document.getElementById(elementId);
    if (abstractContent) {
        abstractContent.classList.toggle('expanded');
    }
}

function toggleRawJson(elementId) {
    const rawJsonElement = document.getElementById(elementId);
    const toggleElement = document.querySelector(`[onclick="toggleRawJson('${elementId}')"]`);
    
    if (rawJsonElement && toggleElement) {
        if (rawJsonElement.style.display === 'none') {
            rawJsonElement.style.display = 'block';
            toggleElement.textContent = '隐藏原始JSON ▲';
        } else {
            rawJsonElement.style.display = 'none';
            toggleElement.textContent = '查看原始JSON ▼';
        }
    }
}

function toggleAuthors(elementId) {
    const authorsContent = document.getElementById(elementId);
    if (authorsContent) {
        authorsContent.classList.toggle('expanded');
    }
}