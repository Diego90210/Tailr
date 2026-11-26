// OpenRouter adapter - provider SDK import is allowed only here
import { LLMProvider, LLMRequest, LLMResponse } from '../types';

export class OpenRouterProvider implements LLMProvider {
  readonly name = 'openrouter';

  async complete<T>(_req: LLMRequest<T>): Promise<LLMResponse<T>> {
    throw new Error('[llm:openrouter] Provider is not implemented');
  }
}
