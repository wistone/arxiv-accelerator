select p.*
from app.papers p
where p.update_date = date '2025-08-07'
  and exists (
    select 1
    from app.paper_categories pc
    join app.categories c on c.category_id = pc.category_id
    where pc.paper_id = p.paper_id
      and c.category_name = 'cs.CV'
  )
order by p.arxiv_id;