-- 2025-07-22 的论文，且存在分析结果（通过 inner join 保证）
select
  p.title as paper_title,
  p.update_date as date,
  ar.pass_filter,
  ar.raw_score,
  p.link,
  p.author_affiliation,
  ar.analysis_result
from app.papers p
join app.analysis_results ar
  on ar.paper_id = p.paper_id
where p.update_date = to_date('20250722', 'YYYYMMDD')
order by p.title, ar.created_at;