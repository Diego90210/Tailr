// OpenRouter adapter - provider SDK import is allowed only here
import { LLMProvider, LLMRequest, LLMResponse } from '../types';

export class OpenRouterProvider implements LLMProvider {
  readonly name = 'openrouter';

  async complete<T>(req: LLMRequest<T>): Promise<LLMResponse<T>> {
    // Placeholder implementation
    return {
      data: req.schema ? ({} as T) : ({} as T),
      usage: {
        tokensIn: 0,
        tokensOut: 0,
      },
      model: 'openrouter:placeholder',
    };
  }
}
