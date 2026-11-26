import type { z } from 'zod/v4';

export class InvalidLLMResponseError extends Error {
  constructor(provider: string) {
    super(`[llm:${provider}] Response failed schema validation`);
    this.name = 'InvalidLLMResponseError';
  }
}

export async function validateResponse<T>(provider: string, schema: z.ZodType<T>, data: unknown): Promise<T> {
  try {
    return await schema.parseAsync(data);
  } catch {
    // Raw model output and Zod issues can contain private CV or posting content.
    throw new InvalidLLMResponseError(provider);
  }
}
