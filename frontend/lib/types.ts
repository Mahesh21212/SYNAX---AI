/** Shared types mirroring the FastAPI schemas. */

export type Role = 'user' | 'assistant' | 'system' | 'tool';

export type AgentName =
  | 'planner'
  | 'researcher'
  | 'analyst'
  | 'writer'
  | 'critic'
  | 'synth';

export interface Attachment {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  excerpt?: string | null;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: Role;
  content: string;
  agent?: AgentName | null;
  attachments: Attachment[];
  citations: Record<string, unknown>[];
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  model: string;
  pinned: boolean;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface AgentStep {
  agent: AgentName;
  model: string;
  status: 'pending' | 'running' | 'done' | 'error';
  summary?: string | null;
  duration_ms?: number | null;
}

export interface ChatResponse {
  conversation_id: string;
  message: Message;
  steps: AgentStep[];
  usage: Record<string, number>;
}

export interface DocumentRecord {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  pages?: number | null;
  char_count: number;
  excerpt?: string | null;
  created_at: string;
}

export interface MemoryRecord {
  id: string;
  content: string;
  kind: string;
  conversation_id?: string | null;
  created_at: string;
}

export interface ModelOption {
  id: string;
  name: string;
  context_length?: number | null;
  description?: string;
}

export interface ModelCatalogue {
  source: 'openrouter' | 'fallback';
  configured: boolean;
  models: ModelOption[];
}

export interface Health {
  status: 'ok' | 'degraded';
  database: boolean;
  openrouter: boolean;
  version: string;
}
