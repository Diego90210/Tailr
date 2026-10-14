// Env contract (TR-ENV-1): vars with no safe default fail the boot with a clear
// message, never at first request. Documented in /.env.example.
//
// ponytail: only vars whose consuming feature is already shipped belong here —
// Clerk/Supabase/Upstash/Docgen move in when SETUP-07/08, DOC-* and LLM-03 land.
export const REQUIRED = ["GROQ_API_KEY"] as const;

export function missingRequired(env: Record<string, string | undefined> = process.env): string[] {
  return REQUIRED.filter((key) => !env[key]?.trim());
}

export function checkEnv(env: Record<string, string | undefined> = process.env): void {
  const missing = missingRequired(env);
  if (missing.length === 0) return;
  throw new Error(
    `[env] Missing required environment variable(s): ${missing.join(", ")}.\n` +
      `Copy .env.example to .env and fill them in before starting the server.`
  );
}

// ponytail: single-line KEY=value parser, comments stripped — enough for this repo's
// .env; multi-line values are not supported (they are not in the contract either).
export function parseEnv(text: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const line of text.split(/\r?\n/)) {
    const match = /^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/.exec(line);
    if (match) out[match[1]] = match[2].replace(/\s+#.*$/, "").trim();
  }
  return out;
}

/** Fill only keys the environment does not already define (process env always wins). */
export function applyEnvFile(env: Record<string, string | undefined>, text: string): void {
  for (const [key, value] of Object.entries(parseEnv(text))) {
    if (!(key in env)) env[key] = value;
  }
}
