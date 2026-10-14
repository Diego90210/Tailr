// Task router driven by env (LLM_ROUTE_*), no recompilation to change models

import { TaskKind } from './types';

export interface RouteConfig {
  provider: string;
  model: string;
}

export function routeForTask(task: TaskKind): RouteConfig {
  const envKey = `LLM_ROUTE_${task.toUpperCase()}`;
  const route = process.env[envKey];
  
  if (!route) {
    throw new Error(`Missing routing configuration for task: ${task} (env: ${envKey})`);
  }
  
  const [provider, model] = route.split(':');
  if (!provider || !model) {
    throw new Error(`Invalid routing format for ${task}: ${route}. Expected "provider:model"`);
  }
  
  return { provider, model };
}

export function getFallbackChain(): string[] {
  const chain = process.env.LLM_FALLBACK_CHAIN || 'groq';
  return chain.split(',').map(p => p.trim()).filter(Boolean);
}
