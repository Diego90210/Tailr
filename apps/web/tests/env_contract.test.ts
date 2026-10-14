import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { REQUIRED, applyEnvFile, checkEnv, missingRequired, parseEnv } from "@/lib/env";

const example = readFileSync(fileURLToPath(new URL("../../../.env.example", import.meta.url)), "utf8");

describe("env contract (TR-ENV-1/2)", () => {
  it("documents every required variable in .env.example", () => {
    for (const key of REQUIRED) expect(example).toContain(`${key}=`);
  });

  it("lists a var only when it is actually missing or empty", () => {
    expect(missingRequired({ GROQ_API_KEY: "gsk_x" })).toEqual([]);
    expect(missingRequired({ GROQ_API_KEY: "  " })).toEqual(["GROQ_API_KEY"]);
    expect(missingRequired({})).toEqual(["GROQ_API_KEY"]);
  });

  it("fails fast with a message naming every missing variable", () => {
    expect(() => checkEnv({})).toThrow(/Missing required environment variable\(s\): GROQ_API_KEY/);
    expect(() => checkEnv({})).toThrow(/\.env\.example/);
    expect(() => checkEnv({ GROQ_API_KEY: "gsk_x" })).not.toThrow();
  });

  it("commits an example file with no secret-looking values", () => {
    const values = example
      .split("\n")
      .filter((line) => !line.startsWith("#") && line.includes("="))
      .map((line) => line.slice(line.indexOf("=") + 1).trim().replace(/\s+#.*$/, ""))
      .filter(Boolean);
    expect(values.filter((v) => /^(gsk_|sk-|sb_|eyJ|ghp_|AKIA)/.test(v))).toEqual([]);
  });

  it("parses the root .env format used by this repo", () => {
    const parsed = parseEnv("GROQ_API_KEY=gsk_x\nRATE_LIMIT_ENABLED=true  # comment\n\n# a comment\nBROKEN LINE\n");
    expect(parsed).toEqual({ GROQ_API_KEY: "gsk_x", RATE_LIMIT_ENABLED: "true" });
  });

  it("never overrides variables already present in the environment", () => {
    const env: Record<string, string | undefined> = { GROQ_API_KEY: "from-process-env" };
    applyEnvFile(env, "GROQ_API_KEY=gsk_from-file\nDOCGEN_URL=https://x");
    expect(env).toEqual({ GROQ_API_KEY: "from-process-env", DOCGEN_URL: "https://x" });
  });
});
