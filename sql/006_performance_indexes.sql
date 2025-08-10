-- 性能优化索引：专门针对搜索场景
-- 运行前请确保这些索引不存在，避免重复创建

-- 1. papers表按日期查询的专用索引（最重要）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_papers_update_date_fast 
ON app.papers(update_date DESC, paper_id);

-- 2. papers表按日期+分类的复合索引（修复：去掉INCLUDE避免行过大）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_papers_date_arxiv 
ON app.papers(update_date DESC, arxiv_id DESC);

-- 3. paper_categories按分类的专用索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_paper_categories_category_fast 
ON app.paper_categories(category_id, paper_id);

-- 4. 分析结果表的优化索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analysis_results_paper_prompt 
ON app.analysis_results(paper_id, prompt_id) 
INCLUDE (analysis_result, norm_score, pass_filter, raw_score);

-- 检查索引是否生效
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'app' 
AND (indexname LIKE '%date%' OR indexname LIKE '%category%' OR indexname LIKE '%fast%')
ORDER BY tablename, indexname;
