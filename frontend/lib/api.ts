/**
 * Typed API client.
 *
 * All browser calls go to same-origin `/api/*` routes in Next.js, which proxy to
 * the FastAPI backend. The OpenRouter key never leaves the server.
 */

import type {
  ChatResponse,
  Conversation,
  DocumentRecord,
  Health,
  MemoryRecord,
  Message,
  ModelCatalogue,
} from './types';

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData
        ? {}
        : { 'Content-Type': 'application/json' }),
      ...(init?.headers ?? {}),
    },
    cache: 'no-store',
  });

  if (res.status === 204) {
    return undefined as T;
  }

  const text = await res.text();
  const data = text ? safeJson(text) : null;

  if (!res.ok) {
    const detail =
      (data && typeof data === 'object' && 'detail' in data
        ? String((data as { detail: unknown }).detail)
        : null) ?? `Request failed (${res.status})`;
    throw new ApiError(detail, res.status);
  }

  return data as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

// --- Health ---------------------------------------------------------------
export const getHealth = () => request<Health>('/api/health');

// --- Conversations --------------------------------------------------------
export const listConversations = () =>
  request<Conversation[]>('/api/conversations');

export const createConversation = (body: { title?: string; model?: string } = {}) =>
  request<Conversation>('/api/conversations', {
    method: 'POST',
    body: JSON.stringify(body),
  });

export const updateConversation = (
  id: string,
  body: { title?: string; pinned?: boolean; model?: string },
) =>
  request<Conversation>(`/api/conversations/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });

export const deleteConversation = (id: string) =>
  request<void>(`/api/conversations/${id}`, { method: 'DELETE' });

export const listMessages = (id: string) =>
  request<Message[]>(`/api/conversations/${id}/messages`);

export const clearMessages = (id: string) =>
  request<void>(`/api/conversations/${id}/messages`, { method: 'DELETE' });

// --- Chat -----------------------------------------------------------------
export const sendChat = (body: {
  conversation_id?: string | null;
  message: string;
  model?: string;
  attachment_ids?: string[];
  use_agents?: boolean;
}) =>
  request<ChatResponse>('/api/chat', {
    method: 'POST',
    body: JSON.stringify(body),
  });

// --- Documents ------------------------------------------------------------
export const listDocuments = () => request<DocumentRecord[]>('/api/documents');

export const uploadDocument = (file: File) => {
  const form = new FormData();
  form.append('file', file);
  return request<DocumentRecord>('/api/documents', {
    method: 'POST',
    body: form,
  });
};

export const deleteDocument = (id: string) =>
  request<void>(`/api/documents/${id}`, { method: 'DELETE' });

// --- Memory ---------------------------------------------------------------
export const listMemories = () => request<MemoryRecord[]>('/api/memory');

export const createMemory = (body: {
  content: string;
  kind?: 'fact' | 'preference' | 'context';
  conversation_id?: string;
}) =>
  request<MemoryRecord>('/api/memory', {
    method: 'POST',
    body: JSON.stringify(body),
  });

export const deleteMemory = (id: string) =>
  request<void>(`/api/memory/${id}`, { method: 'DELETE' });

// --- Models ---------------------------------------------------------------
export const listModels = () => request<ModelCatalogue>('/api/models');
