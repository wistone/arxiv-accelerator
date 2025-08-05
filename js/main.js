/**
 * 主初始化和事件监听
 */

// 页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', async function() {
    console.log('Arxiv文章初筛小助手已加载完成');
    
    // 获取今天的日期
    const today = new Date().toISOString().split('T')[0];
    const dateSelect = document.getElementById('dateSelect');
    
    // 设置日期选择器的最大值为今天
    dateSelect.max = today;
    
    // 设置默认日期为今天
    dateSelect.value = today;
    
    console.log(`📅 设置日期限制: 最大日期 = ${today}, 默认日期 = ${today}`);
    
    // 初始化事件监听器
    initializeEventListeners();
    
    // 添加浏览器前进/后退事件监听
    window.addEventListener('popstate', handlePopState);
    
    // 初始化分析选项为默认状态
    resetAnalysisOptions();
    
    // 初始化页面为搜索模式（标准宽度）
    setSearchMode();
    
    // 加载可用的日期列表
    try {
        const response = await fetch('/api/available_dates');
        const data = await response.json();
        
        if (data.dates && data.dates.length > 0) {
            // 更新日期选择器的提示
            dateSelect.placeholder = `可用日期: ${data.dates.slice(0, 3).join(', ')}...`;
            
            // 如果最新的可用日期比今天更合适（比如今天没有数据），则使用最新可用日期
            const latestAvailableDate = data.dates[0];
            if (latestAvailableDate && latestAvailableDate <= today) {
                dateSelect.value = latestAvailableDate;
                console.log(`📅 使用最新可用日期: ${latestAvailableDate}`);
            }
        }
    } catch (error) {
        console.log('无法加载可用日期列表，使用默认设置:', error);
    }
    
    // 检查URL参数并自动执行相应操作
    const urlParams = parseUrlParams();
    if (urlParams.action) {
        console.log('🔗 检测到URL参数，准备自动执行操作...');
        await executeFromUrlParams(urlParams);
    } else {
        console.log('📋 未检测到URL参数，使用默认状态');
    }
});

/**
 * 获取作者机构信息
 */
async function getAuthorAffiliations(arxivUrl, title) {
    console.log('🏢 正在获取作者机构信息:', arxivUrl);
    
    // 显示弹窗和加载状态
    showAffiliationsModal(title, 'loading');
    
    try {
        const response = await fetch('/api/get_author_affiliations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                arxiv_url: arxivUrl
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('✅ 成功获取作者机构信息:', data);
            showAffiliationsModal(title, 'success', data.affiliations);
        } else {
            console.error('❌ 获取作者机构信息失败:', data.error);
            showAffiliationsModal(title, 'error', null, data.error);
        }
        
    } catch (error) {
        console.error('❌ 请求失败:', error);
        showAffiliationsModal(title, 'error', null, '网络请求失败，请检查服务器连接');
    }
}

/**
 * 显示作者机构弹窗
 */
function showAffiliationsModal(title, state, affiliations = null, errorMessage = null) {
    const modal = document.getElementById('affiliationsModal');
    const content = document.getElementById('affiliationsContent');
    const modalTitle = document.querySelector('.affiliations-modal-title');
    
    // 更新标题
    modalTitle.innerHTML = `🏢 作者机构信息 - ${title.substring(0, 50)}${title.length > 50 ? '...' : ''}`;
    
    // 根据状态显示不同内容
    switch (state) {
        case 'loading':
            content.innerHTML = `
                <div class="affiliations-loading">
                    <div class="spinner"></div>
                    <p>正在使用豆包API智能解析作者机构信息...</p>
                    <p style="font-size: 12px; color: #999; margin-top: 10px;">
                        这可能需要10-30秒的时间，请耐心等待
                    </p>
                </div>
            `;
            break;
            
        case 'success':
            if (affiliations && affiliations.length > 0) {
                const affiliationsList = affiliations.map((affiliation, index) => 
                    `<div class="affiliation-item">
                        <span class="affiliation-number">${index + 1}.</span>
                        ${affiliation}
                    </div>`
                ).join('');
                
                content.innerHTML = `
                    <div class="affiliations-list">
                        <h4>📊 共找到 ${affiliations.length} 个作者机构：</h4>
                        ${affiliationsList}
                    </div>
                    <div style="margin-top: 20px; padding: 15px; background: #e8f5e8; border-radius: 6px; font-size: 14px; color: #155724;">
                        💡 数据来源：豆包AI智能解析论文第一页内容
                    </div>
                `;
            } else {
                content.innerHTML = `
                    <div class="affiliations-empty">
                        <p>😔 未能识别到作者机构信息</p>
                        <p style="font-size: 14px; margin-top: 10px;">
                            可能原因：论文格式特殊、机构信息不清晰或解析失败
                        </p>
                    </div>
                `;
            }
            break;
            
        case 'error':
            content.innerHTML = `
                <div class="affiliations-error">
                    <h4>❌ 获取作者机构信息失败</h4>
                    <p>${errorMessage || '未知错误'}</p>
                    <p style="margin-top: 10px; font-size: 14px;">
                        请稍后重试，或检查论文链接是否有效
                    </p>
                </div>
            `;
            break;
    }
    
    // 显示弹窗
    modal.style.display = 'block';
    
    // 点击背景关闭弹窗
    modal.onclick = function(event) {
        if (event.target === modal) {
            closeAffiliationsModal();
        }
    };
}

/**
 * 关闭作者机构弹窗
 */
function closeAffiliationsModal() {
    const modal = document.getElementById('affiliationsModal');
    modal.style.display = 'none';
}

// 确保函数在全局范围内可用
window.getAuthorAffiliations = getAuthorAffiliations;
window.closeAffiliationsModal = closeAffiliationsModal;