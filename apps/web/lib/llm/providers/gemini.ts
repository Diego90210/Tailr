// Gemini adapter - provider SDK import is allowed only here
import { LLMProvider, LLMRequest, LLMResponse } from '../types';

export class GeminiProvider implements LLMProvider {
  readonly name = 'gemini';

  async complete<T>(req: LLMRequest<T>): Promise<LLMResponse<T>> {
    // Placeholder implementation
    return {
      data: req.schema ? ({} as T) : ({} as T),
      usage: {
        tokensIn: 0,
        tokensOut: 0,
      },
      model: 'gemini:placeholder',
    };
  }
}
