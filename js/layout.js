/**
 * 页面布局管理功能
 */

/**
 * 设置页面为分析模式（更宽的容器）
 */
function setAnalysisMode() {
    const container = document.querySelector('.container');
    if (!container.classList.contains('analysis-mode')) {
        container.classList.add('analysis-mode');
        console.log('🔧 页面已切换到分析模式（宽屏）');
    }
}

/**
 * 设置页面为搜索模式（标准容器宽度）
 */
function setSearchMode() {
    const container = document.querySelector('.container');
    if (container.classList.contains('analysis-mode')) {
        container.classList.remove('analysis-mode');
        console.log('🔧 页面已切换到搜索模式（标准宽度）');
    }
}