-- Uses Supabase Auth (auth.users) as the user source

-- required extensions
create extension if not exists pgcrypto with schema public; -- for gen_random_uuid()

-- 1) schema
create schema if not exists app;

-- 2) prompts
create table if not exists app.prompts (
  prompt_id uuid primary key default gen_random_uuid(),
  prompt_name text not null unique,
  prompt_content text not null,
  created_by uuid null references auth.users(id),
  created_at timestamptz not null default now()
);

-- 3) categories
create table if not exists app.categories (
  category_id bigserial primary key,
  category_name text not null unique
);

-- 4) papers
create table if not exists app.papers (
  paper_id bigserial primary key,
  arxiv_id text not null unique,
  title text not null,
  authors text,
  author_affiliation text,
  abstract text,
  link text,
  update_date date,
  primary_category text,
  ingest_at timestamptz not null default now()
);

create index if not exists idx_papers_update_date on app.papers(update_date);

-- 5) paper_categories (many-to-many)
create table if not exists app.paper_categories (
  paper_id bigint not null references app.papers(paper_id) on delete cascade,
  category_id bigint not null references app.categories(category_id) on delete cascade,
  primary key (paper_id, category_id)
);

create index if not exists idx_paper_categories_category on app.paper_categories(category_id);

-- 6) analysis_results
create table if not exists app.analysis_results (
  analysis_id bigserial primary key,
  paper_id bigint not null references app.papers(paper_id) on delete cascade,
  prompt_id uuid not null references app.prompts(prompt_id) on delete cascade,
  analysis_result jsonb not null,
  -- generated columns for fast filtering/sorting
  pass_filter boolean generated always as ((analysis_result->>'pass_filter')::boolean) stored,
  raw_score numeric generated always as ((analysis_result->>'raw_score')::numeric) stored,
  norm_score numeric generated always as ((analysis_result->>'norm_score')::numeric) stored,
  created_by uuid null references auth.users(id),
  created_at timestamptz not null default now(),
  unique (paper_id, prompt_id)
);

-- indexes for analysis_results
create index if not exists idx_analysis_results_created_at on app.analysis_results(created_at);
create index if not exists idx_analysis_results_pass_filter on app.analysis_results(pass_filter);
create index if not exists idx_analysis_results_raw_score on app.analysis_results(raw_score desc);
create index if not exists idx_analysis_results_norm_score on app.analysis_results(norm_score desc);
create index if not exists idx_analysis_results_jsonb on app.analysis_results using gin (analysis_result);

-- RLS: keep default (disabled) during early integration; enable and add policies later

