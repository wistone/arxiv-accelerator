/**
 * URL状态管理功能
 */

/**
 * 解析当前URL的参数
 * @returns {Object} 包含action, date, category, limit等参数的对象
 */
function parseUrlParams() {
    const urlParams = new URLSearchParams(window.location.search);
    return {
        action: urlParams.get('action'),
        date: urlParams.get('date'),
        category: urlParams.get('category'),
        limit: urlParams.get('limit')
    };
}

/**
 * 更新URL状态，不刷新页面
 * @param {string} action - 动作类型: 'search' 或 'analysis'
 * @param {string} date - 日期
 * @param {string} category - 分类
 * @param {string} limit - 分析限制 (可选): 'top5', 'top10', 'top20', 'all'
 */
function updateUrlState(action, date, category, limit = null) {
    const params = new URLSearchParams();
    
    if (action) params.set('action', action);
    if (date) params.set('date', date);
    if (category) params.set('category', category);
    if (limit) params.set('limit', limit);
    
    const newUrl = `${window.location.pathname}?${params.toString()}`;
    
    // 使用pushState更新URL，不刷新页面
    window.history.pushState({ action, date, category, limit }, '', newUrl);
    
    console.log(`🔗 URL状态已更新: ${action} - ${date} - ${category}${limit ? ` - ${limit}` : ''}`);
}

/**
 * 根据URL参数自动执行相应操作
 * @param {Object} params - URL参数对象
 */
async function executeFromUrlParams(params) {
    const { action, date, category, limit } = params;
    
    if (!action || !date) {
        console.log('📋 URL中没有有效的操作参数，使用默认状态');
        return;
    }
    
    console.log(`🚀 根据URL参数执行操作: ${action}`, params);
    
    // 验证日期格式
    if (date && !isValidDate(date)) {
        showError('⚠️ 无效的日期格式，请使用YYYY-MM-DD格式');
        return;
    }
    
    // 验证分类
    const validCategories = ['cs.CV', 'cs.LG', 'cs.AI'];
    if (category && !validCategories.includes(category)) {
        showError('⚠️ 无效的分类，请选择cs.CV、cs.LG或cs.AI');
        return;
    }
    
    // 设置表单值
    if (date) {
        const dateSelect = document.getElementById('dateSelect');
        dateSelect.value = date;
    }
    
    if (category) {
        const categorySelect = document.getElementById('categorySelect');
        categorySelect.value = category;
    }
    
    // 根据action执行相应操作
    if (action === 'search') {
        await searchArticles();
        // searchArticles 函数内部会调用 setSearchMode()
    } else if (action === 'analysis') {
        // 从 URL 直接访问时，只显示数据库中的结果，不触发新的分析
        console.log('📖 从 URL 访问分析结果，仅加载数据库中的结果');
        
        // 先搜索论文列表
        if (!window.AppState.hasSearched) {
            await searchArticles();
        }
        
        // 如果limit参数缺失，需要特殊处理
        let rangeType = limit;
        if (!limit) {
            // 没有limit参数，需要查找最大可用范围
            console.log('⚠️ URL中缺少limit参数，将查找最大可用范围');
            rangeType = 'full';  // 先尝试full
            window.AppState.missingLimitParam = true;  // 标记缺少limit参数
        }
        
        await loadAnalysisResultsFromDatabase(date, category, rangeType);
    }
}

/**
 * 验证日期格式
 * @param {string} dateString - 日期字符串
 * @returns {boolean} 是否有效
 */
function isValidDate(dateString) {
    const regex = /^\d{4}-\d{2}-\d{2}$/;
    if (!regex.test(dateString)) {
        return false;
    }
    const date = new Date(dateString);
    return date instanceof Date && !isNaN(date);
}

/**
 * 直接从数据库加载分析结果（不触发新分析）
 * @param {string} date - 日期
 * @param {string} category - 分类
 * @param {string} rangeType - 范围类型
 */
async function loadAnalysisResultsFromDatabase(date, category, rangeType) {
    try {
        console.log(`💾 加载数据库中的分析结果: ${date} - ${category} - ${rangeType}`);
        
        const overlay = document.getElementById('overlayLoading');
        if (overlay) overlay.style.display = 'flex';
        
        // 验证limit值是否有效
        const validLimits = ['top5', 'top10', 'top20', 'full'];
        if (!validLimits.includes(rangeType)) {
            showError(`⚠️ 无效的分析范围: ${rangeType}，请选择 top5, top10, top20 或 full`);
            await searchArticles();
            return;
        }
        
        // 检查是否缺少limit参数
        const isMissingLimit = window.AppState.missingLimitParam;
        if (isMissingLimit) {
            // 清除标记
            window.AppState.missingLimitParam = false;
        }
        
        const response = await fetch('/api/get_analysis_results', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date: date,
                category: category,
                range_type: rangeType
            })
        });

        const data = await response.json();

        if (response.ok) {
            if (data.articles && data.articles.length > 0) {
                // 检查是否请求的范围超出实际分析的范围
                const requestedCount = rangeType === 'top5' ? 5 : 
                                     rangeType === 'top10' ? 10 : 
                                     rangeType === 'top20' ? 20 : 999;
                const actualCount = data.articles.length;
                
                // 清除之前的批次按钮
                if (typeof clearPreviousBatchButtons !== 'undefined') {
                    clearPreviousBatchButtons();
                }
                
                // 显示分析结果
                displayAnalysisResults(data.articles);
                
                // 如果缺少limit参数，显示提示信息
                if (isMissingLimit) {
                    // 确定实际的范围类型
                    let actualRangeType = 'full';
                    if (actualCount <= 5) {
                        actualRangeType = 'top5';
                    } else if (actualCount <= 10) {
                        actualRangeType = 'top10';
                    } else if (actualCount <= 20) {
                        actualRangeType = 'top20';
                    }
                    
                    showError(`⚠️ URL中缺少limit参数，已自动加载最大可用范围 ${actualRangeType}（${actualCount} 篇）`);
                    // 更新URL为实际的范围
                    updateUrlState('analysis', date, category, actualRangeType);
                }
                // 如果请求的范围大于实际范围，显示警告
                else if (requestedCount > actualCount && rangeType !== 'full') {
                    // 确定实际的范围类型
                    let actualRangeType = 'full';
                    if (actualCount <= 5) {
                        actualRangeType = 'top5';
                    } else if (actualCount <= 10) {
                        actualRangeType = 'top10';
                    } else if (actualCount <= 20) {
                        actualRangeType = 'top20';
                    }
                    
                    showError(`⚠️ 您请求的是 ${rangeType} 的分析结果，但目前只有 ${actualRangeType} 的结果（${actualCount} 篇）`);
                    // 更新URL为实际的范围
                    updateUrlState('analysis', date, category, actualRangeType);
                } else {
                    showSuccess(`已加载 ${data.articles.length} 篇论文的分析结果`);
                    // 保持URL状态
                    updateUrlState('analysis', date, category, rangeType);
                }
            } else {
                // 没有分析结果，提示用户
                showError(`⚠️ 没有找到 ${date} - ${category} - ${rangeType} 的分析结果，请先点击"分析"按钮进行分析`);
                // 仅显示搜索结果
                await searchArticles();
            }
        } else {
            showError(data.error || '加载分析结果失败');
            // 回退到搜索结果
            await searchArticles();
        }
    } catch (error) {
        showError('加载分析结果时出现网络错误');
        console.error('加载分析结果错误:', error);
        // 回退到搜索结果
        await searchArticles();
    } finally {
        const overlay = document.getElementById('overlayLoading');
        if (overlay) overlay.style.display = 'none';
    }
}

/**
 * 处理浏览器前进/后退事件
 */
function handlePopState(event) {
    console.log('🔙 处理浏览器前进/后退事件');
    
    if (event.state) {
        // 有状态信息，直接使用
        executeFromUrlParams(event.state);
    } else {
        // 解析当前URL参数
        const params = parseUrlParams();
        executeFromUrlParams(params);
    }
}