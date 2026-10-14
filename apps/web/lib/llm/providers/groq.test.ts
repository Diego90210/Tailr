import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { z } from 'zod/v4';
import { GroqProvider } from './groq';

type FetchLike = (url: string, init?: RequestInit) => Promise<Response>;

const req = (over: Partial<Parameters<GroqProvider['complete']>[0]> = {}) =>
  ({
    task: 'analyze_jd' as const,
    system: 'sys',
    messages: [{ role: 'user' as const, content: 'job posting' }],
    maxTokens: 1000,
    temperature: 0,
    locale: 'en' as const,
    ...over,
  }) as Parameters<GroqProvider['complete']>[0];

function mockFetch(status: number, json: unknown, text = '') {
  return vi.fn<FetchLike>(
    async () =>
      ({
        ok: status >= 200 && status < 300,
        status,
        statusText: status === 200 ? 'OK' : 'Error',
        json: async () => json,
        text: async () => text || JSON.stringify(json),
      }) as unknown as Response
  );
}

function sentBody(fetchMock: ReturnType<typeof mockFetch>) {
  const init = fetchMock.mock.calls[0]?.[1];
  return JSON.parse(init?.body as string);
}

describe('GroqProvider', () => {
  beforeEach(() => {
    process.env.GROQ_API_KEY = 'test-key';
    process.env.LLM_ROUTE_ANALYZE_JD = 'groq:openai/gpt-oss-120b';
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.GROQ_API_KEY;
    delete process.env.LLM_ROUTE_ANALYZE_JD;
  });

  it('sends a strict json_schema with every property required', async () => {
    const fetchMock = mockFetch(200, {
      choices: [{ message: { content: '{"role":"Eng","note":"x"}' } }],
      usage: { prompt_tokens: 11, completion_tokens: 22 },
    });
    vi.stubGlobal('fetch', fetchMock);
    const schema = z.object({ role: z.string(), note: z.string().optional() });

    const out = await new GroqProvider().complete(req({ schema }));

    expect(out.data).toEqual({ role: 'Eng', note: 'x' });
    expect(out.usage).toEqual({ tokensIn: 11, tokensOut: 22 });
    expect(out.model).toBe('openai/gpt-oss-120b');

    const body = sentBody(fetchMock);
    expect(body.model).toBe('openai/gpt-oss-120b');
    expect(body.messages[0]).toEqual({ role: 'system', content: 'sys' });
    expect(body.messages[1]).toEqual({ role: 'user', content: 'job posting' });
    expect(body.response_format.json_schema.strict).toBe(true);
    // Groq rejects any property missing from `required` (measured).
    expect(body.response_format.json_schema.schema.required).toEqual(['role', 'note']);
    expect(body.response_format.json_schema.schema.additionalProperties).toBe(false);
  });

  it('forces all required in nested objects', async () => {
    const fetchMock = mockFetch(200, { choices: [{ message: { content: '{"meta":{"city":"Madrid","zip":"28001"}}' } }] });
    vi.stubGlobal('fetch', fetchMock);
    const schema = z.object({ meta: z.object({ city: z.string(), zip: z.string().optional() }) });

    await new GroqProvider().complete(req({ schema }));

    const s = sentBody(fetchMock).response_format.json_schema.schema;
    expect(s.properties.meta.required).toEqual(['city', 'zip']);
  });

  it('omits response_format and returns raw text when no schema', async () => {
    const fetchMock = mockFetch(200, { choices: [{ message: { content: 'hello' } }] });
    vi.stubGlobal('fetch', fetchMock);

    const out = await new GroqProvider().complete(req());

    expect(out.data).toBe('hello');
    expect(sentBody(fetchMock).response_format).toBeUndefined();
  });

  it('throws on a non-OK response and on missing API key', async () => {
    vi.stubGlobal('fetch', mockFetch(429, {}, 'rate limited'));
    await expect(new GroqProvider().complete(req())).rejects.toThrow(/429[\s\S]*rate limited/);

    delete process.env.GROQ_API_KEY;
    await expect(new GroqProvider().complete(req())).rejects.toThrow(/GROQ_API_KEY/);
  });

  it('rejects output that does not match the schema', async () => {
    vi.stubGlobal('fetch', mockFetch(200, { choices: [{ message: { content: '{"role":123}' } }] }));
    const schema = z.object({ role: z.string() });
    await expect(new GroqProvider().complete(req({ schema }))).rejects.toThrow();
  });
});
