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
        // 如果是分析操作，需要先确保已经搜索过
        if (!window.AppState.hasSearched) {
            await searchArticles();
        }
        
        // 设置分析参数
        if (limit) {
            const testCountMap = {
                'top5': '5',
                'top10': '10', 
                'top20': '20',
                'all': ''
            };
            const testCount = testCountMap[limit] || '';
            document.getElementById('testCount').value = testCount;
        }
        
        // 启动分析 - startAnalysis 会最终调用 displayAnalysisResults，其中会调用 setAnalysisMode()
        await startAnalysis();
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