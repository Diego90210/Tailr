// Mock provider for tests and local development
import { LLMProvider, LLMRequest, LLMResponse } from '../types';
import { validateResponse } from '../validation';

export class MockProvider implements LLMProvider {
  readonly name = 'mock';

  constructor(private readonly mockData: unknown = {}) {}

  async complete<T>(req: LLMRequest<T>): Promise<LLMResponse<T>> {
    const data = await validateResponse(this.name, req.schema, this.mockData);
    return {
      data,
      usage: {
        tokensIn: 100,
        tokensOut: 50,
      },
      model: 'mock:deterministic',
    };
  }
}
