// Gemini adapter - provider SDK import is allowed only here
import type { LLMProvider } from '../types';

export class GeminiProvider implements LLMProvider {
  readonly name = 'gemini';

  complete: LLMProvider['complete'] = async () => {
    throw new Error('[llm:gemini] Provider is not implemented');
  };
}
