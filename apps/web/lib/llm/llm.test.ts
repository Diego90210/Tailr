import { describe, it, expect } from 'vitest';
import { routeForTask, getFallbackChain } from './router';
import { MockProvider } from './providers/mock';
import { getProvider } from './providers';
import { z } from 'zod/v4';

describe('LLM abstraction', () => {
  it('should route tasks based on env', () => {
    process.env.LLM_ROUTE_EXTRACT_PROFILE = 'groq:llama-3.1-8b';
    const route = routeForTask('extract_profile');
    expect(route.provider).toBe('groq');
    expect(route.model).toBe('llama-3.1-8b');
  });

  it('should get fallback chain', () => {
    process.env.LLM_FALLBACK_CHAIN = 'groq,gemini';
    const chain = getFallbackChain();
    expect(chain).toEqual(['groq', 'gemini']);
  });

  it('routes classify_facts, the last TaskKind without a route in .env.example', () => {
    process.env.LLM_ROUTE_CLASSIFY_FACTS = 'groq:openai/gpt-oss-120b';
    expect(routeForTask('classify_facts')).toEqual({
      provider: 'groq',
      model: 'openai/gpt-oss-120b',
    });
  });

  it('throws a named error when a task has no route', () => {
    delete process.env.LLM_ROUTE_REWRITE_BULLETS;
    expect(() => routeForTask('rewrite_bullets')).toThrow(/LLM_ROUTE_REWRITE_BULLETS/);
  });

  it('resolves a route provider name to an adapter', () => {
    expect(getProvider('groq').name).toBe('groq');
    expect(getProvider('gemini').name).toBe('gemini');
    expect(getProvider('openrouter').name).toBe('openrouter');
    expect(getProvider('mock').name).toBe('mock');
  });

  it('throws for an unknown provider name', () => {
    expect(() => getProvider('not-a-provider')).toThrow(/Unknown provider/);
  });

  it('mock provider should work', async () => {
    const schema = z.object({ name: z.string() });
    const provider = new MockProvider({ name: 'test' });
    const result = await provider.complete({
      task: 'extract_profile',
      system: 'test',
      messages: [{ role: 'user' as const, content: 'test' }],
      schema,
      maxTokens: 100,
      temperature: 0.1,
      locale: 'en' as const,
    });
    expect(result.data).toEqual({ name: 'test' });
    expect(result.usage.tokensIn).toBe(100);
  });
});
