// ZDR policy (backend_schema.md §8.1): the provider hop is the only place profile data
// leaves our infrastructure, so a provider that trains on free-tier content is never used
// for it — not even as a last resort. The startup assertion below refuses a configuration
// that names such a provider, so the failure lands at boot instead of on a user's CV.
//
// ponytail: allowlist, not blocklist — an unknown provider token fails closed. Add a
// provider here only once its zero-retention posture is documented in §8.1.
export const ZDR_APPROVED: readonly string[] = ["groq", "mock"];

export interface ConfiguredProvider {
  varName: string;
  provider: string;
}

/** Every provider token named by the env contract: LLM_ROUTE_* values and LLM_FALLBACK_CHAIN. */
export function configuredProviders(env: Record<string, string | undefined> = process.env): ConfiguredProvider[] {
  const out: ConfiguredProvider[] = [];
  for (const [varName, value] of Object.entries(env)) {
    if (!/^LLM_ROUTE_[A-Z_]+$/.test(varName)) continue;
    const provider = value?.split(":")[0]?.trim();
    if (provider) out.push({ varName, provider });
  }
  const chain = env.LLM_FALLBACK_CHAIN;
  if (chain?.trim()) {
    for (const token of chain.split(",")) {
      const provider = token.trim();
      if (provider) out.push({ varName: "LLM_FALLBACK_CHAIN", provider });
    }
  }
  return out;
}

export function assertZdrSafe(env: Record<string, string | undefined> = process.env): void {
  const refused = configuredProviders(env).filter(({ provider }) => !ZDR_APPROVED.includes(provider));
  if (refused.length === 0) return;
  const detail = refused.map(({ varName, provider }) => `${varName}=${provider}`).join(", ");
  throw new Error(
    `[zdr] Refusing a training-enabled LLM configuration: ${detail}.\n` +
      `Only ${ZDR_APPROVED.join(", ")} are approved for profile data (backend_schema.md §8.1).`
  );
}
