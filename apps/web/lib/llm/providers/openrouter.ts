// OpenRouter adapter - provider SDK import is allowed only here
import type { LLMProvider } from '../types';

export class OpenRouterProvider implements LLMProvider {
  readonly name = 'openrouter';

  complete: LLMProvider['complete'] = async () => {
    throw new Error('[llm:openrouter] Provider is not implemented');
  };
}
