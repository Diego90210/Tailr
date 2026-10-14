// Cost meter + versioned pricing table

export interface TokenCost {
  input: number;
  output: number;
  cachedInput?: number;
}

export interface ModelPricing {
  [model: string]: TokenCost;
}

export interface PricingTable {
  version: string;
  effectiveDate: string;
  models: ModelPricing;
}

export const PRICING_TABLE: PricingTable = {
  version: '1.0.0',
  effectiveDate: '2026-10-01',
  models: {},
};

export function estimateCost(
  model: string,
  tokensIn: number,
  tokensOut: number
): number {
  const pricing = PRICING_TABLE.models[model];
  if (!pricing) {
    return 0;
  }
  const cost = pricing.input * tokensIn * 1e-6 + pricing.output * tokensOut * 1e-6;
  return Math.round(cost * 1e6) / 1e6;
}
