-- Verify ownership as two authenticated users with Clerk-style subjects.
begin;
create extension if not exists pgtap with schema extensions;
select plan(13);

insert into public.tailr_profiles (id, user_id, name) values
  ('00000000-0000-4000-8000-000000000101', 'user_data10_a', 'User A'),
  ('00000000-0000-4000-8000-000000000102', 'user_data10_b', 'User B');
insert into public.tailr_experience (profile_id, company, role)
values ('00000000-0000-4000-8000-000000000101', 'Example', 'Engineer');
insert into public.tailr_projects (profile_id, name)
values ('00000000-0000-4000-8000-000000000101', 'Example project');
insert into public.tailr_education (profile_id, degree, institution)
values ('00000000-0000-4000-8000-000000000101', 'Example degree', 'Example school');
insert into public.tailr_certifications (profile_id, name)
values ('00000000-0000-4000-8000-000000000101', 'Example certification');

set local role authenticated;
set local request.jwt.claims = '{"role":"authenticated","sub":"user_data10_a"}';

select results_eq(
  $$select name from public.tailr_profiles where id = '00000000-0000-4000-8000-000000000101'$$,
  array['User A'], 'A can read their profile by ID');
select results_eq(
  $$select company from public.tailr_experience where profile_id = '00000000-0000-4000-8000-000000000101'$$,
  array['Example'], 'A can read their experience');
select results_eq(
  $$select name from public.tailr_projects where profile_id = '00000000-0000-4000-8000-000000000101'$$,
  array['Example project'], 'A can read their projects');
select results_eq(
  $$select degree from public.tailr_education where profile_id = '00000000-0000-4000-8000-000000000101'$$,
  array['Example degree'], 'A can read their education');
select results_eq(
  $$select name from public.tailr_certifications where profile_id = '00000000-0000-4000-8000-000000000101'$$,
  array['Example certification'], 'A can read their certifications');

set local request.jwt.claims = '{"role":"authenticated","sub":"user_data10_b"}';

select results_eq(
  $$select name from public.tailr_profiles where id = '00000000-0000-4000-8000-000000000102'$$,
  array['User B'], 'B can read their profile by ID');
select is_empty(
  $$select name from public.tailr_profiles where id = '00000000-0000-4000-8000-000000000101'$$,
  'B cannot read A profile even with its ID');
select is_empty(
  $$select company from public.tailr_experience where profile_id = '00000000-0000-4000-8000-000000000101'$$,
  'B cannot read A experience');
select is_empty(
  $$select name from public.tailr_projects where profile_id = '00000000-0000-4000-8000-000000000101'$$,
  'B cannot read A projects');
select is_empty(
  $$select degree from public.tailr_education where profile_id = '00000000-0000-4000-8000-000000000101'$$,
  'B cannot read A education');
select is_empty(
  $$select name from public.tailr_certifications where profile_id = '00000000-0000-4000-8000-000000000101'$$,
  'B cannot read A certifications');
select is_empty(
  $$update public.tailr_profiles set name = 'Changed'
    where id = '00000000-0000-4000-8000-000000000101' returning id$$,
  'B cannot update A profile');
select is_empty(
  $$delete from public.tailr_profiles
    where id = '00000000-0000-4000-8000-000000000101' returning id$$,
  'B cannot delete A profile');

reset role;
select * from finish();
rollback;
