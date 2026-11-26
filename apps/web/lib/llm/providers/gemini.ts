// Gemini adapter - provider SDK import is allowed only here
import { LLMProvider, LLMRequest, LLMResponse } from '../types';

export class GeminiProvider implements LLMProvider {
  readonly name = 'gemini';

  async complete<T>(_req: LLMRequest<T>): Promise<LLMResponse<T>> {
    throw new Error('[llm:gemini] Provider is not implemented');
  }
}
