-- 允许 API 访问 app schema
grant usage on schema app to service_role, anon, authenticated;

-- 已有表的权限
grant all privileges on all tables in schema app to service_role;
grant usage, select, update on all sequences in schema app to service_role;

grant select on all tables in schema app to anon, authenticated;
grant usage, select on all sequences in schema app to anon, authenticated;

-- 未来新表也自动有权限
alter default privileges in schema app grant all on tables to service_role;
alter default privileges in schema app grant select on tables to anon, authenticated;
alter default privileges in schema app grant usage, select, update on sequences to service_role;
alter default privileges in schema app grant usage, select on sequences to anon, authenticated;