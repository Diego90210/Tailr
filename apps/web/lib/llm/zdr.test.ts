import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { parseEnv } from "@/lib/env";
import { ZDR_APPROVED, assertZdrSafe, configuredProviders } from "@/lib/llm/zdr";

const example = readFileSync(fileURLToPath(new URL("../../../../.env.example", import.meta.url)), "utf8");

describe("ZDR policy (backend_schema.md §8.1)", () => {
  it("accepts approved providers only", () => {
    expect(() =>
      assertZdrSafe({
        LLM_ROUTE_ANALYZE_JD: "groq:openai/gpt-oss-120b",
        LLM_ROUTE_EXTRACT_PROFILE: "mock:whatever",
        LLM_FALLBACK_CHAIN: "groq",
      })
    ).not.toThrow();
  });

  it("refuses a route that names a training-enabled provider", () => {
    expect(() => assertZdrSafe({ LLM_ROUTE_GAP_QUESTIONS: "gemini:flash" })).toThrow(
      /LLM_ROUTE_GAP_QUESTIONS=gemini/
    );
  });

  it("refuses a fallback chain with an unapproved provider", () => {
    expect(() => assertZdrSafe({ LLM_FALLBACK_CHAIN: "groq,gemini,openrouter" })).toThrow(
      /LLM_FALLBACK_CHAIN=gemini, LLM_FALLBACK_CHAIN=openrouter/
    );
  });

  it("fails closed for an unknown provider token", () => {
    expect(() => assertZdrSafe({ LLM_ROUTE_ANALYZE_JD: "some-new-provider:model" })).toThrow(
      /some-new-provider/
    );
  });

  it("reads routes and the chain, and ignores unrelated env", () => {
    expect(
      configuredProviders({ GEMINI_API_KEY: "x", LLM_ROUTE_ANALYZE_JD: "groq:m", LLM_FALLBACK_CHAIN: "groq,mock" })
    ).toEqual([
      { varName: "LLM_ROUTE_ANALYZE_JD", provider: "groq" },
      { varName: "LLM_FALLBACK_CHAIN", provider: "groq" },
      { varName: "LLM_FALLBACK_CHAIN", provider: "mock" },
    ]);
  });

  it("keeps .env.example copyable: it must satisfy its own ZDR assertion", () => {
    expect(() => assertZdrSafe(parseEnv(example))).not.toThrow();
    expect(ZDR_APPROVED).toContain("groq");
  });

  it("wires the assertion into the boot hook", async () => {
    const { register } = await import("../../instrumentation");
    const saved = {
      runtime: process.env.NEXT_RUNTIME,
      key: process.env.GROQ_API_KEY,
      route: process.env.LLM_ROUTE_ANALYZE_JD,
      chain: process.env.LLM_FALLBACK_CHAIN,
    };
    try {
      process.env.NEXT_RUNTIME = "nodejs";
      process.env.GROQ_API_KEY = "gsk_test";
      delete process.env.LLM_FALLBACK_CHAIN;
      process.env.LLM_ROUTE_ANALYZE_JD = "gemini:flash";
      await expect(register()).rejects.toThrow(/gemini/);

      process.env.LLM_ROUTE_ANALYZE_JD = "groq:openai/gpt-oss-120b";
      await expect(register()).resolves.toBeUndefined();
    } finally {
      for (const [key, value] of Object.entries({
        NEXT_RUNTIME: saved.runtime,
        GROQ_API_KEY: saved.key,
        LLM_ROUTE_ANALYZE_JD: saved.route,
        LLM_FALLBACK_CHAIN: saved.chain,
      })) {
        if (value === undefined) delete process.env[key];
        else process.env[key] = value;
      }
    }
  });
});
