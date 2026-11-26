import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

import { applyEnvFile } from "./lib/env";

// ponytail: the repo keeps a single .env at the root (scripts/spike02_groq.py reads it
// from there); Next only auto-loads .env from its own project dir, so feed the root file
// in here. Config runs at build time too, which also gets root NEXT_PUBLIC_* inlined.
// Process env and apps/web/.env(.local) still win. Ceiling: values containing " #"
// would be truncated — don't put secrets in comments.
const rootEnv = join(dirname(fileURLToPath(import.meta.url)), "..", "..", ".env");
if (existsSync(rootEnv)) {
  applyEnvFile(process.env, readFileSync(rootEnv, "utf8"));
}


const nextConfig: NextConfig = {
  outputFileTracingRoot: dirname(rootEnv),
  outputFileTracingIncludes: { "/api/analyze": ["../../prompts/analyze-jd.md"] },
  experimental: {
    // pinned after the 16.4.0 security advisory: the agent build guard must not fire
    agentUpgrade: "security",
  },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
