// Provider exports
export * from './groq';
export * from './gemini';
export * from './openrouter';
export * from './mock';

import { LLMProvider } from '../types';
import { GroqProvider } from './groq';
import { GeminiProvider } from './gemini';
import { OpenRouterProvider } from './openrouter';
import { MockProvider } from './mock';

// Route strings name a provider ('groq:model'); mapping the name back to an
// adapter keeps provider choice in LLM_ROUTE_* — no code change to swap (RF-11.2).
const PROVIDERS: Record<string, () => LLMProvider> = {
  groq: () => new GroqProvider(),
  gemini: () => new GeminiProvider(),
  openrouter: () => new OpenRouterProvider(),
  mock: () => new MockProvider(),
};

export function getProvider(name: string): LLMProvider {
  const factory = PROVIDERS[name];
  if (!factory) throw new Error(`[llm] Unknown provider: ${name}`);
  return factory();
}
