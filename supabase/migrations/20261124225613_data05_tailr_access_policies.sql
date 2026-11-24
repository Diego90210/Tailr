-- DATA-05: replace inherited grants on the original Tailr tables only.
revoke all on
  public.tailr_profiles, public.tailr_facts, public.tailr_experience, public.tailr_projects,
  public.tailr_education, public.tailr_certifications, public.tailr_format_specs
  from public, anon, authenticated, service_role;

grant select, insert, update, delete on
  public.tailr_profiles, public.tailr_facts, public.tailr_experience, public.tailr_projects,
  public.tailr_education, public.tailr_certifications, public.tailr_format_specs
  to authenticated, service_role;

grant select on public.tailr_format_specs to anon;

-- Foreign keys check existence even when RLS hides the referenced row.
alter policy "own profile" on public.tailr_profiles
  to authenticated
  using (user_id = ((select auth.jwt()) ->> 'sub'))
  with check (
    user_id = ((select auth.jwt()) ->> 'sub')
    and (format_spec_id is null or exists (
      select 1 from public.tailr_format_specs s where s.id = tailr_profiles.format_spec_id
    ))
  );

alter policy "own specs" on public.tailr_format_specs
  to authenticated
  using (owner_id = ((select auth.jwt()) ->> 'sub'))
  with check (owner_id = ((select auth.jwt()) ->> 'sub'));
