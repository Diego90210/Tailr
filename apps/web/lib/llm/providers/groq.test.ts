import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { z } from 'zod/v4';
import { PostingAnalysisSchema } from '@/lib/contracts/analysis';
import { GroqProvider } from './groq';
import { InvalidLLMResponseError } from '../validation';

type FetchLike = (url: string, init?: RequestInit) => Promise<Response>;

const req = (over: Partial<Parameters<GroqProvider['complete']>[0]> = {}) =>
  ({
    task: 'analyze_jd' as const,
    system: 'sys',
    messages: [{ role: 'user' as const, content: 'job posting' }],
    schema: z.object({ role: z.string() }),
    maxTokens: 1000,
    temperature: 0,
    locale: 'en' as const,
    ...over,
  }) as Parameters<GroqProvider['complete']>[0];

function mockFetch(status: number, json: unknown) {
  return vi.fn<FetchLike>(
    async () =>
      ({
        ok: status >= 200 && status < 300,
        status,
        statusText: status === 200 ? 'OK' : 'Error',
        json: async () => json,
        text: async () => JSON.stringify(json),
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

  it('accepts a documented analysis contract for schema negotiation and validation', async () => {
    const data = {
      jdLang: 'en', companyName: null, roleTitle: null, seniority: null,
      requirements: [], keywords: [], redFlags: [],
    };
    const fetchMock = mockFetch(200, { choices: [{ message: { content: JSON.stringify(data) } }] });
    vi.stubGlobal('fetch', fetchMock);
    await expect(new GroqProvider().complete(req({ schema: PostingAnalysisSchema })))
      .resolves.toMatchObject({ data });
    expect(sentBody(fetchMock).response_format.json_schema.schema.required).toContain('seniority');
    expect(sentBody(fetchMock).response_format.json_schema.schema.properties).not.toHaveProperty('matchScore');
  });

  it('throws on a non-OK response and on missing API key', async () => {
    const fetchMock = mockFetch(429, { detail: 'private posting' });
    vi.stubGlobal('fetch', fetchMock);
    await expect(new GroqProvider().complete(req())).rejects.toThrow(/^\[llm:groq\] Upstream HTTP 429$/);

    delete process.env.GROQ_API_KEY;
    await expect(new GroqProvider().complete(req())).rejects.toThrow(/GROQ_API_KEY/);
  });

  it.each([
    ['plain text', { choices: [{ message: { content: 'private posting' } }] }],
    ['wrong shape', { choices: [{ message: { content: '{"role":123}' } }] }],
    ['missing completion', { choices: [] }],
  ])('rejects %s without returning model output', async (_case, json) => {
    vi.stubGlobal('fetch', mockFetch(200, json));
    const result = new GroqProvider().complete(req());
    await expect(result).rejects.toBeInstanceOf(InvalidLLMResponseError);
    await expect(result).rejects.toThrow(/^\[llm:groq\] Response failed schema validation$/);
  });
});
