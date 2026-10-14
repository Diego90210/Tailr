#!/usr/bin/env node
// Locale parity gate (TR-TEST-3 / SETUP-03): fails if any key exists in one
// locale file but not the other.
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const LOCALES = ["es", "en"];
const dir = process.argv[2] ??
  join(dirname(fileURLToPath(import.meta.url)), "..", "apps", "web", "messages");

const files = LOCALES.map((l) => ({ locale: l, path: join(dir, `${l}.json`) }));
const present = files.filter((f) => existsSync(f.path));

if (present.length === 0) {
  // ponytail: messages/ not authored yet (I18N-02). Parity is vacuous, not broken.
  console.log(`[OK] no locale files in ${dir} yet — nothing to compare`);
  process.exit(0);
}
if (present.length !== files.length) {
  const missing = files.filter((f) => !existsSync(f.path)).map((f) => `${f.locale}.json`);
  console.error(`[FAIL] missing locale file(s): ${missing.join(", ")} (found ${present.map((f) => f.locale + ".json").join(", ")})`);
  process.exit(1);
}

// ponytail: plain objects only, arrays compared as leaves — enough for
// messages/*.json; revisit if messages ever nest objects inside arrays.
function flatten(value, prefix, out) {
  if (value !== null && typeof value === "object" && !Array.isArray(value)) {
    for (const k of Object.keys(value).sort()) {
      flatten(value[k], prefix ? `${prefix}.${k}` : k, out);
    }
    return out;
  }
  out.add(prefix);
  return out;
}

const keys = new Map(files.map((f) => [f.locale, flatten(JSON.parse(readFileSync(f.path, "utf8")), "", new Set())]));

let failed = false;
for (const [a, b] of [["es", "en"], ["en", "es"]]) {
  const only = [...keys.get(a)].filter((k) => !keys.get(b).has(k)).sort();
  if (only.length) {
    failed = true;
    console.error(`[FAIL] ${only.length} key(s) present in ${a}.json but missing in ${b}.json:`);
    for (const k of only) console.error(`       - ${k}`);
  }
}

if (failed) process.exit(1);
console.log(`[OK] locale parity: ${keys.get("es").size} keys match across es.json and en.json`);
