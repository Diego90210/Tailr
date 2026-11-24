#!/usr/bin/env bash
set -euo pipefail
set -o noclobber

deploy_dir=${1:?pass an empty deployment directory}
mkdir "$deploy_dir/supabase"
cp -R supabase/config.toml supabase/migrations "$deploy_dir/supabase/"

# Only an existing ledger entry may satisfy these WikiFlash versions.
for version in 20251212034332 20251217204548 20251217204558 20251217204604; do
  printf 'do $$ begin raise exception %s; end $$;\n' "'WikiFlash baseline $version must already be applied'" \
    > "$deploy_dir/supabase/migrations/${version}_wikiflash_baseline.sql"
done
