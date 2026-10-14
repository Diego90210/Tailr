export async function register(): Promise<void> {
  // Called for every runtime; env validation is a Node-side concern.
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  const { checkEnv } = await import("./lib/env");
  checkEnv();
  // Refuse a training-enabled provider before the first request (LLM-10, §8.1).
  const { assertZdrSafe } = await import("./lib/llm/zdr");
  assertZdrSafe();
}
