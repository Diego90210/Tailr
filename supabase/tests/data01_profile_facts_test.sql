-- DATA-01 regression check: schema + RLS ownership for the profile/facts tables.
-- Run with: npx supabase test db   (needs `npx supabase start`)

begin;
create extension if not exists pgtap with schema extensions;

select plan(16);

select has_table('public', 'tailr_profiles', 'tailr_profiles exists');
select has_table('public', 'tailr_facts', 'tailr_facts exists');
select has_table('public', 'tailr_experience', 'tailr_experience exists');
select has_table('public', 'tailr_projects', 'tailr_projects exists');
select has_table('public', 'tailr_education', 'tailr_education exists');
select has_table('public', 'tailr_certifications', 'tailr_certifications exists');

select ok((select relrowsecurity from pg_class where oid = 'public.tailr_profiles'::regclass), 'RLS enabled on tailr_profiles');
select ok((select relrowsecurity from pg_class where oid = 'public.tailr_facts'::regclass), 'RLS enabled on tailr_facts');
select ok((select relrowsecurity from pg_class where oid = 'public.tailr_experience'::regclass), 'RLS enabled on tailr_experience');
select ok((select relrowsecurity from pg_class where oid = 'public.tailr_projects'::regclass), 'RLS enabled on tailr_projects');
select ok((select relrowsecurity from pg_class where oid = 'public.tailr_education'::regclass), 'RLS enabled on tailr_education');
select ok((select relrowsecurity from pg_class where oid = 'public.tailr_certifications'::regclass), 'RLS enabled on tailr_certifications');

-- Two users, one fact each (inserted as the migration owner, before assuming a user identity).
insert into tailr_profiles (id, user_id, name) values
  ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'user_a', 'User A'),
  ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', 'user_b', 'User B');
insert into tailr_facts (profile_id, kind, text, provenance) values
  ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'skill', 'fact owned by A', 'user_input');

set local role authenticated;
set local request.jwt.claims = '{"sub":"user_a"}';
select results_eq(
  'select text from tailr_facts',
  array['fact owned by A'],
  'user A reads their own fact'
);

set local request.jwt.claims = '{"sub":"user_b"}';
select is_empty('select id from tailr_facts', 'user B sees none of user A facts');
select results_eq(
  'select id from tailr_profiles',
  array['bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'::uuid],
  'user B sees only their own profile'
);
select throws_ok(
  $$insert into tailr_facts (profile_id, kind, text, provenance)
    values ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'skill', 'injected', 'user_input')$$,
  '42501',
  null,
  'user B cannot write a fact under user A profile'
);

reset role;
select * from finish();
rollback;
