/**
 * 全局配置和变量
 */

// 全局变量
let currentArticles = [];
let hasSearched = false;
let currentAnalysisArticles = []; // 存储当前分析结果
let sortColumn = ''; // 当前排序列
let sortDirection = 'asc'; // 排序方向

// SSE连接管理变量
let currentEventSource = null;
let progressCheckInterval = null;
let analysisStartTime = null;
let lastProgressUpdate = null;

// 导出全局变量（用于模块间共享）
window.AppState = {
    currentArticles,
    hasSearched,
    currentAnalysisArticles,
    sortColumn,
    sortDirection,
    currentEventSource,
    progressCheckInterval,
    analysisStartTime,
    lastProgressUpdate
};