// Mock provider for tests and local development
import { LLMProvider, LLMRequest, LLMResponse } from '../types';

export class MockProvider<T = unknown> implements LLMProvider {
  readonly name = 'mock';

  constructor(private readonly mockData: T | null = null) {}

  async complete<U = T>(req: LLMRequest<U>): Promise<LLMResponse<U>> {
    // Return mock data if provided, otherwise empty object validated against schema
    const data = this.mockData !== null ? (this.mockData as unknown as U) : (req.schema ? ({} as U) : ({} as U));
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
