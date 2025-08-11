-- 查询特定date和category的论文分析结果
-- 使用方法：修改下面的参数
-- @target_date: 目标日期，格式 '20250722'
-- @target_category: 目标分类，如 'cs.AI', 'cs.CV' 等

WITH target_params AS (
  SELECT 
    '20250722' as target_date,
    'cs.AI' as target_category
),
-- 聚合每篇论文的所有分类
paper_categories_agg AS (
  SELECT 
    pc.paper_id,
    string_agg(c.category_name, ', ' ORDER BY c.category_name) as all_categories
  FROM app.paper_categories pc
  JOIN app.categories c ON pc.category_id = c.category_id
  GROUP BY pc.paper_id
)

SELECT
  p.title,
  p.update_date,
  ar.pass_filter,
  ar.raw_score as score,
  p.arxiv_id,
  p.author_affiliation,
  ar.analysis_result,
  COALESCE(pca.all_categories, '') as all_categories
FROM app.papers p
JOIN app.analysis_results ar ON ar.paper_id = p.paper_id
-- 确保论文属于目标分类
JOIN app.paper_categories pc ON pc.paper_id = p.paper_id
JOIN app.categories c ON c.category_id = pc.category_id
-- 获取论文的所有分类
LEFT JOIN paper_categories_agg pca ON pca.paper_id = p.paper_id
CROSS JOIN target_params tp
WHERE 
  p.update_date = to_date(tp.target_date, 'YYYYMMDD')
  AND c.category_name = tp.target_category
ORDER BY ar.raw_score DESC NULLS LAST, p.title;