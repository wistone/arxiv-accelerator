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