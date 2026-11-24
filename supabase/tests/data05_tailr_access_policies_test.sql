-- DATA-05: run with supabase test db --local.
begin;
create extension if not exists pgtap with schema extensions;
select plan(9);

select is_empty(
  $$select relname from pg_class where relnamespace = 'public'::regnamespace
      and left(relname, 6) = 'tailr_' and relkind = 'r' and not relrowsecurity$$,
  'every Tailr table has RLS');
select is_empty(
  $$select relname from pg_class where relnamespace = 'public'::regnamespace
      and left(relname, 6) = 'tailr_' and relkind = 'r'
      and has_table_privilege('authenticated', oid, 'TRUNCATE, REFERENCES, TRIGGER')$$,
  'authenticated cannot use privileges outside row-level CRUD');
select results_eq(
  $$select oid from pg_class where relnamespace = 'public'::regnamespace
      and left(relname, 6) = 'tailr_' and relkind = 'r'
      and has_table_privilege('anon', oid, 'SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER')$$,
  array['public.tailr_format_specs'::regclass::oid], 'format specs are the only table with anonymous grants');

insert into tailr_format_specs (id, owner_id, name, spec) values
  ('00000000-0000-4000-8000-000000000051', 'data05_a', 'A private spec', '{}'),
  ('00000000-0000-4000-8000-000000000052', 'data05_b', 'B private spec', '{}');

set local role anon;
select is_empty('select id from tailr_format_specs where owner_id is not null',
                'anon cannot see private format specs');
select throws_ok($$delete from tailr_format_specs where owner_id is null$$,
                 '42501', null, 'anon cannot delete the global format spec');

set local role authenticated;
set local request.jwt.claims = '{"sub":"data05_a"}';
select throws_ok(
  $$insert into tailr_profiles (user_id, name, format_spec_id)
    values ('data05_a', 'User A', '00000000-0000-4000-8000-000000000052')$$,
  '42501', null, 'A cannot create a profile linked to a private B spec');
select lives_ok(
  $$insert into tailr_profiles (user_id, name, format_spec_id)
    values ('data05_a', 'User A', '00000000-0000-4000-8000-000000000051')$$,
  'A can link to their own format spec');
select throws_ok(
  $$update tailr_profiles set format_spec_id = '00000000-0000-4000-8000-000000000052'$$,
  '42501', null, 'A cannot change an existing profile to a private B spec');
select lives_ok(
  $$update tailr_profiles set format_spec_id = (select id from tailr_format_specs where owner_id is null and is_default)$$,
  'A can link to the global default');

reset role;
select * from finish();
rollback;
