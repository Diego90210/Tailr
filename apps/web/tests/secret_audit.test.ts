import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const WEB_ROOT = path.resolve(import.meta.dirname, "..");
const REPO_ROOT = path.resolve(WEB_ROOT, "..", "..");
const STATIC_DIR = path.join(WEB_ROOT, ".next", "static");

// Public by design (TR §21): publishable keys are meant to reach the browser.
const PUBLIC_SECRETS = new Set([
  "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
  "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
]);
const SECRET_NAME = /(KEY|SECRET|TOKEN|PASSWORD)/;
const BUNDLE_TEXT = /\.(js|css|map|json|txt|html)$/;

function parseEnv(source: string): Map<string, string> {
  const vars = new Map<string, string>();
  for (const line of source.split(/\r?\n/)) {
    const match = /^\s*([A-Za-z0-9_]+)\s*=\s*(.*)$/.exec(line);
    if (match) vars.set(match[1], match[2].replace(/\s+#.*$/, "").trim());
  }
  return vars;
}

const CONTRACT = parseEnv(readFileSync(path.join(REPO_ROOT, ".env.example"), "utf8"));
const SECRET_NAMES = [...CONTRACT.keys()].filter(
  (name) => SECRET_NAME.test(name) && !PUBLIC_SECRETS.has(name),
);

function filesUnder(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const file = path.join(dir, name);
    return statSync(file).isDirectory() ? filesUnder(file) : [file];
  });
}

function containsAny(text: string, needles: string[]): boolean {
  return needles.some((needle) => text.includes(needle));
}

function secretValues(): string[] {
  const fromContract = SECRET_NAMES.map((name) => process.env[name] ?? CONTRACT.get(name));
  const envFiles = [path.join(REPO_ROOT, ".env"), path.join(WEB_ROOT, ".env.local")];
  const fromFiles = envFiles
    .filter((file) => existsSync(file))
    .flatMap((file) => {
      const vars = parseEnv(readFileSync(file, "utf8"));
      return SECRET_NAMES.map((name) => vars.get(name));
    });
  return [...fromContract, ...fromFiles].filter(
    (value): value is string => typeof value === "string" && value.length >= 8,
  );
}

// Third-party code legitimately reads `process.env.SOME_SECRET` in a client bundle; Next
// resolves it to undefined, so the bare reference is harmless. A name only matters once it
// carries a value, which is what the remaining scan looks for.
const ENV_REFERENCE = /\.env(?:\.([A-Z0-9_]+)|\[["'`]([A-Z0-9_]+)["'`]\])/g;

describe("secret audit", () => {
  it("keeps every secret-looking variable out of the public prefix", () => {
    expect(SECRET_NAMES.length).toBeGreaterThan(5);
    const exposed = SECRET_NAMES.filter(
      (name) => name.startsWith("NEXT_PUBLIC_") && !PUBLIC_SECRETS.has(name),
    );
    expect(exposed).toEqual([]);
  });

  // The scan needs a build: init.sh and CI run `pnpm build` before this suite.
  // shortcut: only scans when apps/web/.next/static exists, add an explicit build step if it becomes a standalone gate.
  const bundleFiles = existsSync(STATIC_DIR)
    ? filesUnder(STATIC_DIR).filter(
        (file) => BUNDLE_TEXT.test(file) && statSync(file).size < 5_000_000,
      )
    : [];

  it.skipIf(bundleFiles.length === 0)("ships no secret name or value to the client", () => {
    const values = secretValues();
    const leaks: string[] = [];
    for (const file of bundleFiles) {
      const text = readFileSync(file, "utf8").replace(ENV_REFERENCE, "");
      const where = path.relative(WEB_ROOT, file);
      if (containsAny(text, SECRET_NAMES)) leaks.push(`secret name in ${where}`);
      if (containsAny(text, values)) leaks.push(`secret value in ${where}`);
    }
    expect(leaks).toEqual([]);
  });

  it("detects a planted secret (positive control)", () => {
    expect(containsAny("var key = GROQ_API_KEY;", SECRET_NAMES)).toBe(true);
    expect(containsAny("var url = NEXT_PUBLIC_SUPABASE_URL;", SECRET_NAMES)).toBe(false);
  });
});
