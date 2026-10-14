import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it } from "vitest";

const script = fileURLToPath(new URL("../../../scripts/check_locale_parity.mjs", import.meta.url));

let dir: string;

function run(): { status: number | null; out: string } {
  const r = spawnSync(process.execPath, [script, dir], { encoding: "utf8" });
  return { status: r.status, out: r.stdout + r.stderr };
}

function write(locale: string, value: unknown): void {
  writeFileSync(join(dir, `${locale}.json`), JSON.stringify(value));
}

afterEach(() => {
  if (dir) rmSync(dir, { recursive: true, force: true });
  dir = "";
});

describe("locale parity gate (TR-TEST-3)", () => {
  it("passes when both locales carry the same keys", () => {
    dir = mkdtempSync(join(tmpdir(), "i18n-ok-"));
    write("es", { nav: { start: "Empezar" }, cta: "Generar" });
    write("en", { nav: { start: "Start" }, cta: "Generate" });
    expect(run().status).toBe(0);
  });

  it("fails when a key exists in es but is missing in en", () => {
    dir = mkdtempSync(join(tmpdir(), "i18n-missing-"));
    write("es", { nav: { start: "Empezar" }, cta: "Generar" });
    write("en", { nav: { start: "Start" } });
    const r = run();
    expect(r.status).toBe(1);
    expect(r.out).toContain("cta");
  });

  it("fails when only one locale file exists", () => {
    dir = mkdtempSync(join(tmpdir(), "i18n-one-"));
    write("es", { cta: "Generar" });
    const r = run();
    expect(r.status).toBe(1);
    expect(r.out).toContain("en.json");
  });

  it("passes vacuously when no locale files exist yet", () => {
    dir = mkdtempSync(join(tmpdir(), "i18n-none-"));
    expect(run().status).toBe(0);
  });
});
