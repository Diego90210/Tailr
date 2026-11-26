// Groq adapter - provider SDK/HTTP import is allowed only here
// Uses the OpenAI-compatible chat completions API with strict json_schema output.
import { z } from 'zod/v4';
import { LLMProvider, LLMRequest, LLMResponse } from '../types';
import { routeForTask } from '../router';
import { InvalidLLMResponseError, validateResponse } from '../validation';

const GROQ_CHAT_URL = 'https://api.groq.com/openai/v1/chat/completions';

const GroqChatResponseSchema = z.object({
  choices: z.array(z.object({ message: z.object({ content: z.string() }) })).min(1),
  usage: z.object({
    prompt_tokens: z.number().int().nonnegative().optional(),
    completion_tokens: z.number().int().nonnegative().optional(),
  }).optional(),
});

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
    const schema = z.toJSONSchema(req.schema);
    forceAllRequired(schema);
    const body = {
      model,
      messages: [{ role: 'system', content: req.system }, ...req.messages],
      max_tokens: req.maxTokens,
      temperature: req.temperature,
      response_format: {
        type: 'json_schema',
        json_schema: { name: req.task, strict: true, schema },
      },
    };

    const res = await fetch(GROQ_CHAT_URL, {
      method: 'POST',
      headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      throw new Error(`[llm:groq] Upstream HTTP ${res.status}`);
    }

    let json: z.infer<typeof GroqChatResponseSchema>;
    let payload: unknown;
    try {
      json = GroqChatResponseSchema.parse(await res.json());
      payload = JSON.parse(json.choices[0].message.content);
    } catch {
      throw new InvalidLLMResponseError(this.name);
    }
    const data = await validateResponse(this.name, req.schema, payload);
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
