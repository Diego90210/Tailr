-- DATA-02 regression check: the format_specs table, its seeded default and its RLS.
-- Run with: npx supabase test db   (needs `npx supabase start`)

begin;
create extension if not exists pgtap with schema extensions;

select plan(14);

select has_table('public', 'tailr_format_specs', 'tailr_format_specs exists');
select has_column('public', 'tailr_profiles', 'format_spec_id', 'tailr_profiles.format_spec_id exists');
select ok((select relrowsecurity from pg_class where oid = 'public.tailr_format_specs'::regclass),
          'RLS enabled on tailr_format_specs');

-- Exactly one global default, and it matches the docgen defaults (§11.1).
select is((select count(*) from tailr_format_specs where owner_id is null and is_default),
          1::bigint, 'one global default spec');
select is((select spec->>'font' from tailr_format_specs where owner_id is null),
          'Cambria', 'default font is Cambria');
select is((select (spec->>'nameSizePt')::int from tailr_format_specs where owner_id is null),
          15, 'default name size is 15pt');
select is((select (spec->>'bodySizePt')::int from tailr_format_specs where owner_id is null),
          11, 'default body size is 11pt');
select is((select (spec->>'dateItalic')::bool from tailr_format_specs where owner_id is null),
          true, 'default dates are italic');
select is((select spec->>'linkColor' from tailr_format_specs where owner_id is null),
          '0563C1', 'default link color');

set local role authenticated;
set local request.jwt.claims = '{"sub":"user_a"}';
select is((select count(*) from tailr_format_specs), 1::bigint, 'user A sees the global default');

insert into tailr_format_specs (owner_id, name, spec, is_default)
values ('user_a', 'mine', '{}'::jsonb, true);
select is((select count(*) from tailr_format_specs), 2::bigint, 'user A sees own spec and the global one');

set local request.jwt.claims = '{"sub":"user_b"}';
select is((select count(*) from tailr_format_specs), 1::bigint, 'user B sees only the global default');
select throws_ok(
  $$insert into tailr_format_specs (owner_id, name, spec) values (null, 'sneaky', '{}'::jsonb)$$,
  '42501',
  null,
  'user B cannot write a global spec'
);

-- An update that RLS hides must not reach the global row.
update tailr_format_specs set name = 'hacked' where owner_id is null;
reset role;
select is((select name from tailr_format_specs where owner_id is null), 'default',
          'global default is untouched after user B attempted an update');

select * from finish();
rollback;
