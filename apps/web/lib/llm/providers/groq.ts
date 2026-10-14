// Groq adapter - provider SDK/HTTP import is allowed only here
// Uses the OpenAI-compatible chat completions API with strict json_schema output.
import { z } from 'zod/v4';
import { LLMProvider, LLMRequest, LLMResponse } from '../types';
import { routeForTask } from '../router';

const GROQ_CHAT_URL = 'https://api.groq.com/openai/v1/chat/completions';

interface GroqChatResponse {
  choices?: { message?: { content?: string } }[];
  usage?: { prompt_tokens?: number; completion_tokens?: number };
}

// Groq strict json_schema requires every property to be listed in `required`.
// Callers should model genuinely-absent fields as `.nullable()`, not `.optional()`.
function forceAllRequired(node: unknown): void {
  if (Array.isArray(node)) {
    node.forEach(forceAllRequired);
    return;
  }
  if (!node || typeof node !== 'object') return;
  const obj = node as Record<string, unknown>;
  if (obj.properties && typeof obj.properties === 'object') {
    obj.required = Object.keys(obj.properties);
  }
  Object.values(obj).forEach(forceAllRequired);
}

export class GroqProvider implements LLMProvider {
  readonly name = 'groq';

  async complete<T>(req: LLMRequest<T>): Promise<LLMResponse<T>> {
    const apiKey = process.env.GROQ_API_KEY;
    if (!apiKey) throw new Error('[llm:groq] GROQ_API_KEY is not set');

    const { model } = routeForTask(req.task);
    // gpt-oss spends ~230 tokens on reasoning before the JSON: maxTokens < 1000
    // surfaces as a confusing API 400 json_validate_failed (SPIKE-03). Callers pass maxTokens.
    const body: Record<string, unknown> = {
      model,
      messages: [{ role: 'system', content: req.system }, ...req.messages],
      max_tokens: req.maxTokens,
      temperature: req.temperature,
    };
    if (req.schema) {
      const schema = z.toJSONSchema(req.schema) as Record<string, unknown>;
      forceAllRequired(schema);
      body.response_format = {
        type: 'json_schema',
        json_schema: { name: req.task, strict: true, schema },
      };
    }

    const res = await fetch(GROQ_CHAT_URL, {
      method: 'POST',
      headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(`[llm:groq] ${res.status} ${res.statusText}: ${detail.slice(0, 300)}`);
    }

    const json = (await res.json()) as GroqChatResponse;
    const content = json.choices?.[0]?.message?.content ?? '';
    // Typed via the caller's zod contract; invalid output throws rather than reaching the user.
    const data = (req.schema ? req.schema.parse(JSON.parse(content)) : content) as T;
    return {
      data,
      usage: {
        tokensIn: json.usage?.prompt_tokens ?? 0,
        tokensOut: json.usage?.completion_tokens ?? 0,
      },
      model,
    };
  }
}
