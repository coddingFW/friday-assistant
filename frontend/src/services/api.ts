// Cliente REST fino do backend (saúde, modelos, visão, workspace).

import { REST_BASE_URL } from "./config";
import type {
  ConversationDetail,
  ConversationSummary,
  HealthResponse,
  WsFile,
  WsRoot,
  WsTreeEntry,
  WsWriteResult,
} from "../types";

/** Extrai a mensagem de erro do backend (campo `detail`) quando houver. */
async function errorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (body && typeof body.detail === "string") return body.detail;
  } catch {
    /* corpo não-JSON */
  }
  return `HTTP ${response.status}`;
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${REST_BASE_URL}${path}`);
  if (!response.ok) throw new Error(await errorDetail(response));
  return (await response.json()) as T;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${REST_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await errorDetail(response));
  return (await response.json()) as T;
}

export function getHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/health");
}

export function listModels(): Promise<{ provider: string; models: string[] }> {
  return getJson("/llm/models");
}

export function captureScreen(): Promise<{ image: string; mime: string }> {
  return getJson("/vision/screen");
}

/** OCR: extrai o texto literal de uma imagem enviada (base64) ou da tela. */
export function runOcr(payload: {
  source?: "upload" | "screen";
  image?: string;
  lang?: string;
}): Promise<{ text: string; lang: string; chars: number }> {
  return postJson("/vision/ocr", payload);
}

// --- Workspace (projeto local — Fase 10) -----------------------------------

export function getWorkspaceRoot(): Promise<WsRoot> {
  return getJson<WsRoot>("/workspace/root");
}

export function setWorkspaceRoot(path: string): Promise<WsRoot> {
  return postJson<WsRoot>("/workspace/root", { path });
}

export function getWorkspaceTree(): Promise<WsTreeEntry[]> {
  return getJson<WsTreeEntry[]>("/workspace/tree");
}

export function getWorkspaceFile(path: string): Promise<WsFile> {
  return getJson<WsFile>(`/workspace/file?path=${encodeURIComponent(path)}`);
}

export function writeWorkspaceFile(
  path: string,
  text: string,
): Promise<WsWriteResult> {
  return postJson<WsWriteResult>("/workspace/file", { path, text });
}

// --- Conversas (histórico / memória de longo prazo — Fase 9) ----------------

export function listConversations(limit = 50): Promise<ConversationSummary[]> {
  return getJson<ConversationSummary[]>(`/conversations?limit=${limit}`);
}

export function getConversation(id: string): Promise<ConversationDetail> {
  return getJson<ConversationDetail>(`/conversations/${encodeURIComponent(id)}`);
}

export async function deleteConversation(id: string): Promise<void> {
  const response = await fetch(
    `${REST_BASE_URL}/conversations/${encodeURIComponent(id)}`,
    { method: "DELETE" },
  );
  if (!response.ok) throw new Error(await errorDetail(response));
}
