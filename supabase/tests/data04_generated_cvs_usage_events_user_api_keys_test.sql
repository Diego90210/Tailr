-- DATA-04: run with supabase test db --local.
begin;
create extension if not exists pgtap with schema extensions;

select plan(17);

select ok(relrowsecurity, relname || ' has RLS enabled')
from pg_class
where oid in ('public.tailr_generated_cvs'::regclass, 'public.tailr_usage_events'::regclass,
              'public.tailr_user_api_keys'::regclass)
order by relname;

insert into tailr_profiles (id, user_id, name) values
  ('00000000-0000-4000-8000-000000000041', 'data04_a', 'User A'),
  ('00000000-0000-4000-8000-000000000042', 'data04_b', 'User B');
insert into tailr_job_analyses (id, profile_id, jd_text, jd_hash, requirements, keywords) values
  ('00000000-0000-4000-8000-000000000043', '00000000-0000-4000-8000-000000000041', 'Posting A', 'hash-a', '[]', '[]'),
  ('00000000-0000-4000-8000-000000000044', '00000000-0000-4000-8000-000000000042', 'Posting B', 'hash-b', '[]', '[]');

set local role service_role;
insert into tailr_usage_events (user_id, task) values ('data04_a', 'test_default');
insert into tailr_usage_events (user_id, task, cost_source) values ('data04_a', 'test_byo', 'byo_key');
insert into tailr_user_api_keys (user_id, provider, key_ciphertext, key_hint)
values ('data04_a', 'groq', decode('00', 'hex'), 'test hint');
select results_eq($$select provider from tailr_user_api_keys where user_id = 'data04_a'$$,
                  array['groq'], 'service role can manage key records');
select throws_ok('select id from tailr_usage_events',
                 '42501', null, 'service role cannot read insert-only usage events');

set local role authenticated;
set local request.jwt.claims = '{"sub":"data04_a"}';
insert into tailr_generated_cvs (analysis_id, docx_path, ui_locale, cv_lang)
values ('00000000-0000-4000-8000-000000000043', 'test.docx', 'es', 'en');
select results_eq('select docx_path from tailr_generated_cvs',
                  array['test.docx'], 'A reads their own generated CV');
select throws_ok(
  $$update tailr_generated_cvs set analysis_id = '00000000-0000-4000-8000-000000000044'$$,
  '42501', null, 'A cannot reparent a generated CV to a B analysis');

select throws_ok('select id from tailr_usage_events', '42501', null, 'A cannot read usage events');
select throws_ok(
  $$insert into tailr_usage_events (user_id, task) values ('data04_a', 'test_forged')$$,
  '42501', null, 'A cannot write usage events');
select throws_ok('select provider, key_hint from tailr_user_api_keys',
                 '42501', null, 'A cannot access key metadata directly');
select throws_ok('select key_ciphertext from tailr_user_api_keys',
                 '42501', null, 'A cannot read even their own ciphertext');
select throws_ok('delete from tailr_user_api_keys',
                 '42501', null, 'A cannot delete keys directly');

set local request.jwt.claims = '{"sub":"data04_b"}';
select is_empty('select id from tailr_generated_cvs', 'B cannot read A generated CV');
select throws_ok(
  $$insert into tailr_generated_cvs (analysis_id, ui_locale, cv_lang)
    values ('00000000-0000-4000-8000-000000000043', 'es', 'es')$$,
  '42501', null, 'B cannot attach a generated CV to A analysis');

set local role anon;
select throws_ok('select id from tailr_generated_cvs', '42501', null, 'anon cannot read generated CVs');

reset role;
select results_eq(
  $$select cost_source from tailr_usage_events where user_id = 'data04_a' order by id$$,
  array['platform', 'byo_key'], 'usage distinguishes default platform spend from BYO');
select throws_ok(
  $$insert into tailr_usage_events (task, cost_source) values ('invalid', 'unknown')$$,
  '23514', null, 'usage rejects an unknown cost source');

select * from finish();
rollback;
