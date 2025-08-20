   -- 1. 撤销anon和authenticated角色对app schema的使用权限
   REVOKE USAGE ON SCHEMA app FROM anon, authenticated;
   
   -- 2. 撤销anon和authenticated角色对app schema中所有表的所有权限  
   REVOKE ALL ON ALL TABLES IN SCHEMA app FROM anon, authenticated;
   
   -- 3. 设置默认权限：新创建的表默认不给anon和authenticated角色任何权限
   ALTER DEFAULT PRIVILEGES IN SCHEMA app REVOKE ALL ON TABLES FROM anon, authenticated;