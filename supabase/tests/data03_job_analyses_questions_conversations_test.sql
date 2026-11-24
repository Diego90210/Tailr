-- DATA-03: run with supabase test db --local.
begin;
create extension if not exists pgtap with schema extensions;

select plan(21);

select ok(relrowsecurity, relname || ' has RLS enabled')
from pg_class
where oid in ('public.tailr_job_analyses'::regclass, 'public.tailr_questions'::regclass,
              'public.tailr_conversations'::regclass)
order by relname;

select ok(not has_table_privilege('anon', oid, 'SELECT, INSERT, UPDATE, DELETE, TRUNCATE'),
          relname || ' denies anonymous access')
from pg_class
where oid in ('public.tailr_job_analyses'::regclass, 'public.tailr_questions'::regclass,
              'public.tailr_conversations'::regclass)
order by relname;

insert into tailr_profiles (id, user_id, name) values
  ('00000000-0000-4000-8000-000000000001', 'data03_a', 'User A'),
  ('00000000-0000-4000-8000-000000000002', 'data03_b', 'User B');
insert into tailr_facts (id, profile_id, kind, text, provenance) values
  ('00000000-0000-4000-8000-000000000003', '00000000-0000-4000-8000-000000000001', 'skill', 'Fact A', 'user_input'),
  ('00000000-0000-4000-8000-000000000004', '00000000-0000-4000-8000-000000000002', 'skill', 'Fact B', 'user_input');
insert into tailr_job_analyses (id, profile_id, jd_text, jd_hash, requirements, keywords)
values ('00000000-0000-4000-8000-000000000006', '00000000-0000-4000-8000-000000000002', 'Posting B', 'hash-b', '[]', '[]');

set local role authenticated;
set local request.jwt.claims = '{"sub":"data03_a"}';
insert into tailr_job_analyses (id, profile_id, jd_text, jd_hash, requirements, keywords)
values ('00000000-0000-4000-8000-000000000005', '00000000-0000-4000-8000-000000000001', 'Posting A', 'hash-a', '[]', '[]');
insert into tailr_questions (analysis_id, text, status, answer, fact_id)
values ('00000000-0000-4000-8000-000000000005', 'Question A', 'answered', 'Answer A', '00000000-0000-4000-8000-000000000003');
insert into tailr_conversations (analysis_id) values ('00000000-0000-4000-8000-000000000005');

select results_eq('select jd_text from tailr_job_analyses', array['Posting A'], 'A reads only their own analysis');
select results_eq('select text from tailr_questions', array['Question A'], 'A reads their own question');
select results_eq('select confidence::text from tailr_conversations', array['0.0000'], 'A reads their own conversation');
select throws_ok(
  $$update tailr_job_analyses set profile_id = '00000000-0000-4000-8000-000000000002'$$,
  '42501', null, 'A cannot move an analysis to B profile');
select throws_ok(
  $$update tailr_questions set analysis_id = '00000000-0000-4000-8000-000000000006'$$,
  '42501', null, 'A cannot move a question to B analysis');
select throws_ok(
  $$update tailr_conversations set analysis_id = '00000000-0000-4000-8000-000000000006'$$,
  '42501', null, 'A cannot move a conversation to B analysis');
select throws_ok(
  $$update tailr_questions set fact_id = '00000000-0000-4000-8000-000000000004'$$,
  '42501', null, 'A cannot link B fact to their own question');

set local request.jwt.claims = '{"sub":"data03_b"}';
select results_eq('select jd_text from tailr_job_analyses', array['Posting B'], 'B reads only their own analysis');
select is_empty('select id from tailr_questions', 'B cannot read A questions');
select is_empty('select id from tailr_conversations', 'B cannot read A conversations');
select throws_ok(
  $$insert into tailr_job_analyses (profile_id, jd_text, jd_hash, requirements, keywords)
    values ('00000000-0000-4000-8000-000000000001', 'Other posting', 'other', '[]', '[]')$$,
  '42501', null, 'B cannot add an analysis to A profile');
select throws_ok(
  $$insert into tailr_questions (analysis_id, text)
    values ('00000000-0000-4000-8000-000000000005', 'Other question')$$,
  '42501', null, 'B cannot add a question to A analysis');
select throws_ok(
  $$insert into tailr_conversations (analysis_id) values ('00000000-0000-4000-8000-000000000005')$$,
  '42501', null, 'B cannot add a conversation to A analysis');

set local request.jwt.claims = '{"sub":"data03_a"}';
delete from tailr_facts where id = '00000000-0000-4000-8000-000000000003';
select results_eq('select answer from tailr_questions where fact_id is null',
                  array['Answer A'], 'removing a fact unlinks it without removing the answer');

delete from tailr_profiles where id = '00000000-0000-4000-8000-000000000001';
reset role;
select is_empty($$select id from tailr_job_analyses where id = '00000000-0000-4000-8000-000000000005'
                  union all select id from tailr_questions where analysis_id = '00000000-0000-4000-8000-000000000005'
                  union all select id from tailr_conversations where analysis_id = '00000000-0000-4000-8000-000000000005'$$,
                'deleting a profile cascades to its analyses, questions and conversations');

select * from finish();
rollback;
