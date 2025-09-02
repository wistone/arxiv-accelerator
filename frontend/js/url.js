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
        limit: urlParams.get('limit'),
        // 智能搜索参数
        content: urlParams.get('content'),
        filter: urlParams.get('filter')
    };
}

/**
 * 更新URL状态，不刷新页面
 * @param {string} action - 动作类型: 'search', 'analysis', 'smart_search', 或 'smart_search_analysis'
 * @param {string} date - 日期
 * @param {string} category - 分类
 * @param {string} limit - 分析限制 (可选): 'top5', 'top10', 'top20', 'all'
 * @param {string} content - 智能搜索内容 (可选)
 * @param {string} filter - 日期筛选状态 (可选)
 */
function updateUrlState(action, date = null, category = null, limit = null, content = null, filter = null) {
    const params = new URLSearchParams();
    
    if (action) params.set('action', action);
    if (date) params.set('date', date);
    if (category) params.set('category', category);
    if (limit) params.set('limit', limit);
    
    // 智能搜索参数
    if (content) {
        // Base64编码内容以避免URL特殊字符问题
        const encodedContent = btoa(unescape(encodeURIComponent(content)));
        params.set('content', encodedContent);
    }
    if (filter) params.set('filter', filter);
    
    const newUrl = `${window.location.pathname}?${params.toString()}`;
    
    // 使用pushState更新URL，不刷新页面
    const state = { action, date, category, limit, content, filter };
    window.history.pushState(state, '', newUrl);
    
    const logMsg = (action === 'smart_search' || action === 'smart_search_analysis')
        ? `🔗 URL状态已更新: ${action} - 内容长度: ${content?.length || 0}${filter ? ` - 筛选: ${filter}` : ''}${limit ? ` - ${limit}` : ''}`
        : `🔗 URL状态已更新: ${action} - ${date} - ${category}${limit ? ` - ${limit}` : ''}`;
    console.log(logMsg);
}

/**
 * 根据URL参数自动执行相应操作
 * @param {Object} params - URL参数对象
 */
async function executeFromUrlParams(params) {
    const { action, date, category, limit } = params;
    
    console.log('🔗 executeFromUrlParams被调用，参数:', params);
    
    if (!action) {
        console.log('📋 URL中没有action参数，使用默认状态');
        return;
    }
    
    // 对于智能搜索和智能搜索分析，不需要date参数
    if (action !== 'smart_search' && action !== 'smart_search_analysis' && !date) {
        console.log('📋 URL中没有有效的操作参数（缺少date），使用默认状态');
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
    } else if (action === 'smart_search') {
        console.log('🔍 检测到智能搜索action，准备执行');
        // 执行智能搜索
        await executeSmartSearchFromUrl(params);
    } else if (action === 'smart_search_analysis') {
        console.log('📊 检测到智能搜索分析action，准备执行');
        // 执行智能搜索分析
        await executeSmartSearchAnalysisFromUrl(params);
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

/**
 * 从URL执行智能搜索
 * @param {Object} params - URL参数对象
 */
async function executeSmartSearchFromUrl(params) {
    const { content, filter } = params;
    
    
    if (!content) {
        console.log('📋 URL中没有智能搜索内容');
        return;
    }
    
    
    // 等待DOM完全加载
    await new Promise(resolve => {
        if (document.readyState === 'complete') {
            resolve();
        } else {
            window.addEventListener('load', resolve);
        }
    });
    
    try {
        // 解码Base64内容（URLSearchParams已经处理了URL解码）
        const decodedContent = decodeURIComponent(escape(atob(content)));
        
        // 设置搜索内容到输入框
        const smartSearchInput = document.getElementById('smartSearchInput');
        if (smartSearchInput) {
            smartSearchInput.value = decodedContent;
        }
        
        // 执行智能搜索
        if (typeof startSmartSearch !== 'undefined') {
            await startSmartSearch();
            
            // 应用日期筛选（如果有）
            if (filter && filter !== 'all') {
                setTimeout(() => {
                    applyDateFilterFromUrl(filter);
                }, 1000); // 延迟应用筛选，确保搜索完成
            }
        }
        
    } catch (error) {
        console.error('解析智能搜索URL参数失败:', error);
        if (typeof showError === 'function') {
            showError('⚠️ URL参数解析失败，请重新搜索');
        } else {
            console.error('showError函数不可用，错误:', error.message);
        }
    }
}

/**
 * 从URL应用日期筛选
 * @param {string} filterString - 筛选字符串，如 "2025-08-25,2025-08-29"
 */
function applyDateFilterFromUrl(filterString) {
    if (!filterString || filterString === 'all') {
        return;
    }
    
    try {
        const selectedDates = filterString.split(',');
        
        // 取消"全部日期"选项
        const allCheckbox = document.querySelector('#dateFilterDropdown input[value="all"]');
        if (allCheckbox) {
            allCheckbox.checked = false;
        }
        
        // 只选中指定的日期
        const checkboxes = document.querySelectorAll('#dateFilterOptions input[type="checkbox"]');
        checkboxes.forEach(cb => {
            cb.checked = selectedDates.includes(cb.value);
        });
        
        // 自动应用筛选
        if (typeof applyColumnDateFilter !== 'undefined') {
            // 创建模拟事件对象
            const mockEvent = { stopPropagation: () => {} };
            applyColumnDateFilter(mockEvent);
        }
        
        console.log(`📅 已从URL应用日期筛选: ${filterString}`);
        
    } catch (error) {
        console.error('应用URL日期筛选失败:', error);
    }
}

/**
 * 更新智能搜索的URL状态
 * @param {string} content - 搜索内容
 * @param {string} filter - 当前筛选状态
 */
function updateSmartSearchUrlState(content, filter = 'all') {
    updateUrlState('smart_search', null, null, null, content, filter);
}

/**
 * 更新智能搜索分析的URL状态
 * @param {string} content - 搜索内容
 * @param {string} limit - 分析限制: 'top5', 'top10', 'top20', 'full'
 * @param {string} filter - 当前筛选状态 (可选)
 */
function updateSmartSearchAnalysisUrlState(content, limit, filter = 'all') {
    updateUrlState('smart_search_analysis', null, null, limit, content, filter);
}

/**
 * 从URL执行智能搜索分析
 * @param {Object} params - URL参数对象
 */
async function executeSmartSearchAnalysisFromUrl(params) {
    const { content, filter, limit } = params;
    
    if (!content) {
        console.log('📋 URL中没有智能搜索内容');
        return;
    }
    
    // 等待DOM完全加载
    await new Promise(resolve => {
        if (document.readyState === 'complete') {
            resolve();
        } else {
            window.addEventListener('load', resolve);
        }
    });
    
    try {
        // 解码Base64内容（URLSearchParams已经处理了URL解码）
        const decodedContent = decodeURIComponent(escape(atob(content)));
        
        // 设置搜索内容到输入框
        const smartSearchInput = document.getElementById('smartSearchInput');
        if (smartSearchInput) {
            smartSearchInput.value = decodedContent;
        }
        
        // 先执行智能搜索以获取论文列表
        if (typeof startSmartSearch !== 'undefined') {
            console.log('🚀 开始执行智能搜索');
            await startSmartSearch();
            
            // 等待搜索完成，然后检查是否有分析结果
            let retryCount = 0;
            const maxRetries = 10;
            
            const checkAndLoadResults = async () => {
                console.log(`🔍 检查智能搜索结果状态 (尝试 ${retryCount + 1}/${maxRetries})`);
                
                // 应用日期筛选（如果有）
                if (filter && filter !== 'all') {
                    console.log('📅 应用日期筛选:', filter);
                    applyDateFilterFromUrl(filter);
                }
                
                // 检查当前是否有智能搜索结果
                if (window.smartSearchState && window.smartSearchState.currentResults && window.smartSearchState.currentResults.articles) {
                    console.log('📊 智能搜索完成，开始加载分析结果，范围:', limit, '论文数:', window.smartSearchState.currentResults.articles.length);
                    
                    // 直接加载已有的分析结果
                    if (typeof loadSmartSearchAnalysisResults !== 'undefined') {
                        try {
                            await loadSmartSearchAnalysisResults();
                            console.log('✅ 智能搜索分析结果加载完成');
                        } catch (error) {
                            console.error('❌ 加载分析结果失败:', error);
                        }
                    } else {
                        console.log('⚠️ loadSmartSearchAnalysisResults 函数不可用');
                    }
                } else {
                    console.log('⚠️ 智能搜索状态未准备好，当前状态:', {
                        hasSmartSearchState: !!window.smartSearchState,
                        hasCurrentResults: !!(window.smartSearchState && window.smartSearchState.currentResults),
                        hasArticles: !!(window.smartSearchState && window.smartSearchState.currentResults && window.smartSearchState.currentResults.articles)
                    });
                    
                    // 如果还没有准备好且重试次数未超限，继续等待
                    if (retryCount < maxRetries) {
                        retryCount++;
                        setTimeout(checkAndLoadResults, 500); // 每500ms检查一次
                    } else {
                        console.log('❌ 达到最大重试次数，无法加载分析结果');
                    }
                }
            };
            
            // 给智能搜索一些时间完成，然后开始检查
            setTimeout(checkAndLoadResults, 1000);
        } else {
            console.log('⚠️ startSmartSearch 函数不可用');
        }
        
    } catch (error) {
        console.error('解析智能搜索分析URL参数失败:', error);
        if (typeof showError === 'function') {
            showError('⚠️ URL参数解析失败，请重新搜索');
        } else {
            console.error('showError函数不可用，错误:', error.message);
        }
    }
}