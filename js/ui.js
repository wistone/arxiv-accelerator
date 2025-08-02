/**
 * UI控制相关函数
 */

function showLoading() {
    document.getElementById('loading').style.display = 'block';
    document.getElementById('error').style.display = 'none';
    document.getElementById('success').style.display = 'none';
    document.getElementById('tableContainer').style.display = 'none';
    document.getElementById('stats').style.display = 'none';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function showError(message) {
    hideLoading();
    // 隐藏成功消息
    document.getElementById('success').style.display = 'none';
    // 显示错误消息
    document.getElementById('error').textContent = message;
    document.getElementById('error').style.display = 'block';
}

function showSuccess(message) {
    hideLoading();
    // 隐藏错误消息
    document.getElementById('error').style.display = 'none';
    // 显示成功消息
    document.getElementById('success').textContent = message;
    document.getElementById('success').style.display = 'block';
}

function hideAllMessages() {
    document.getElementById('error').style.display = 'none';
    document.getElementById('success').style.display = 'none';
}

function updateStats(articles) {
    document.getElementById('totalArticles').textContent = articles.length;
    document.getElementById('stats').style.display = 'flex';
}

function closeModal() {
    // 停止所有连接
    stopAllConnections();
    
    // 隐藏弹窗
    document.getElementById('analysisModal').style.display = 'none';
}

// 初始化页面事件监听器
function initializeEventListeners() {
    // 监听日期和类别变化，重置分析选项
    document.getElementById('dateSelect').addEventListener('change', resetAnalysisOptions);
    document.getElementById('categorySelect').addEventListener('change', resetAnalysisOptions);
}

// 重置分析选项到默认状态
function resetAnalysisOptions() {
    const testCountSelect = document.getElementById('testCount');
    const analysisStatus = document.getElementById('analysisStatus');
    
    // 恢复默认的所有选项
    testCountSelect.innerHTML = `
        <option value="">全部分析</option>
        <option value="5">仅前5篇</option>
        <option value="10">仅前10篇</option>
        <option value="20">仅前20篇</option>
    `;
    
    // 清空状态提示
    analysisStatus.innerHTML = '';
    
    console.log('🔄 已重置分析选项到默认状态');
}