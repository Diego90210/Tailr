import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const PROMPTS = ["analyze-jd", "extract-profile", "gap-questions", "rewrite-bullets", "diagnose-ats", "humanizer"];

// Prompts that receive user-supplied text and must declare it as data (TR-SEC-1).
const UNTRUSTED_INPUT = ["analyze-jd", "extract-profile", "gap-questions", "rewrite-bullets", "diagnose-ats"];

function read(name: string): string {
  return readFileSync(fileURLToPath(new URL(`../../../prompts/${name}.md`, import.meta.url)), "utf8");
}

describe("prompt contract (RF-11.6)", () => {
  it("ships every migrated prompt as a non-empty file", () => {
    for (const name of PROMPTS) expect(read(name).trim().length).toBeGreaterThan(0);
  });

  it("versions every prompt with front matter whose name matches its file", () => {
    for (const name of PROMPTS) {
      const text = read(name);
      expect(text).toMatch(/^---\r?\n/);
      expect(text).toMatch(new RegExp(`\\r?\\nname: ${name}\\r?\\n`));
      expect(text).toMatch(/\r?\nversion: \d+\.\d+\.\d+\r?\n/);
    }
  });

  it("treats delimited user text as data in every prompt that reads it", () => {
    for (const name of UNTRUSTED_INPUT) {
      expect(read(name)).toMatch(/as data,\s+never as an?\s+instruction/);
    }
  });

  it("locks bullet rewriting to the referenced fact IDs", () => {
    const text = read("rewrite-bullets");
    expect(text).toContain("factIds");
    expect(text).toMatch(/at least one/i);
    expect(text).toMatch(/220/);
  });

  it("keeps the humanizer pass fact-preserving and dash-free", () => {
    const text = read("humanizer");
    expect(text).toMatch(/Keep every fact/i);
    expect(text).toMatch(/No em dashes/);
  });
});
