// LLM abstraction layer - types and interfaces
// Provider SDK imports must NOT occur outside lib/llm/providers

// zod/v4 provides z.toJSONSchema, used to derive provider JSON schemas from zod contracts.
import { z } from 'zod/v4';

export type TaskKind =
  | 'extract_profile'
  | 'analyze_jd'
  | 'gap_questions'
  | 'rewrite_bullets'
  | 'classify_facts';

export interface LLMMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface LLMRequest<T = unknown> {
  task: TaskKind;
  system: string;
  messages: { role: 'user' | 'assistant'; content: string }[];
  schema?: z.ZodType<T>;
  maxTokens: number;
  temperature: number;
  locale: 'en' | 'es';
}

export interface LLMUsage {
  tokensIn: number;
  tokensOut: number;
}

export interface LLMResponse<T = unknown> {
  data: T;
  usage: LLMUsage;
  model: string;
}

export interface LLMProvider {
  readonly name: string;
  complete<T>(req: LLMRequest<T>): Promise<LLMResponse<T>>;
}
