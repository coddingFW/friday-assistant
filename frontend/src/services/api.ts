// Cliente REST fino do backend (config, saúde, modelos, sensores).

import { REST_BASE_URL } from "./config";
import type { HealthResponse } from "../types";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${REST_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`GET ${path} falhou: ${response.status}`);
  }
  return (await response.json()) as T;
}

export function getHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/health");
}

export function listModels(): Promise<{ provider: string; models: string[] }> {
  return getJson("/llm/models");
}
