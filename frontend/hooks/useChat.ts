'use client';

/**
 * Chat state: conversations, messages, sending, uploads.
 *
 * Kept in one hook so the UI components stay presentational and the optimistic
 * behaviour lives in a single place.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import * as api from '@/lib/api';
import type {
  AgentStep,
  Attachment,
  Conversation,
  DocumentRecord,
  Message,
} from '@/lib/types';

const DEFAULT_MODEL = 'baidu/ernie-5.5-flash-preview:free';

function tempId(): string {
  return `tmp-${Math.random().toString(36).slice(2, 10)}`;
}

export function useChat() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [model, setModel] = useState<string>(DEFAULT_MODEL);
  const [useAgents, setUseAgents] = useState(true);
  const [sending, setSending] = useState(false);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadingConversation, setLoadingConversation] = useState(false);

  const activeIdRef = useRef<string | null>(null);
  activeIdRef.current = activeId;

  // --- Load the conversation list -----------------------------------------
  const refreshConversations = useCallback(async () => {
    try {
      const list = await api.listConversations();
      setConversations(list);
      return list;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load conversations');
      return [];
    }
  }, []);

  useEffect(() => {
    void refreshConversations();
  }, [refreshConversations]);

  // --- Select a conversation ----------------------------------------------
  const selectConversation = useCallback(async (id: string | null) => {
    setActiveId(id);
    setSteps([]);
    setError(null);

    if (!id) {
      setMessages([]);
      return;
    }

    setLoadingConversation(true);
    try {
      const [history, conversation] = await Promise.all([
        api.listMessages(id),
        api.listConversations().then((list) => list.find((c) => c.id === id)),
      ]);
      setMessages(history);
      if (conversation?.model) setModel(conversation.model);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load messages');
      setMessages([]);
    } finally {
      setLoadingConversation(false);
    }
  }, []);

  // --- New conversation ----------------------------------------------------
  const newConversation = useCallback(() => {
    setActiveId(null);
    setMessages([]);
    setSteps([]);
    setError(null);
  }, []);

  // --- Send a message ------------------------------------------------------
  const send = useCallback(
    async (text: string, attachments: DocumentRecord[] = []) => {
      const content = text.trim();
      if (!content || sending) return;

      setError(null);
      setSending(true);
      setSteps([]);

      const optimistic: Message = {
        id: tempId(),
        conversation_id: activeIdRef.current ?? '',
        role: 'user',
        content,
        attachments: attachments.map<Attachment>((doc) => ({
          id: doc.id,
          filename: doc.filename,
          content_type: doc.content_type,
          size_bytes: doc.size_bytes,
          excerpt: doc.excerpt ?? null,
        })),
        citations: [],
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, optimistic]);

      try {
        const response = await api.sendChat({
          conversation_id: activeIdRef.current,
          message: content,
          model,
          attachment_ids: attachments.map((doc) => doc.id),
          use_agents: useAgents,
        });

        setActiveId(response.conversation_id);
        setSteps(response.steps);
        setMessages((prev) => [
          ...prev.filter((m) => m.id !== optimistic.id),
          { ...optimistic, id: `${optimistic.id}-sent`, conversation_id: response.conversation_id },
          response.message,
        ]);
        void refreshConversations();
        return response.message;
      } catch (err) {
        setMessages((prev) => prev.filter((m) => m.id !== optimistic.id));
        setError(err instanceof Error ? err.message : 'The request failed');
        return null;
      } finally {
        setSending(false);
      }
    },
    [model, refreshConversations, sending, useAgents],
  );

  // --- Rename / pin / delete ----------------------------------------------
  const renameConversation = useCallback(
    async (id: string, title: string) => {
      const updated = await api.updateConversation(id, { title });
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? updated : c)),
      );
    },
    [],
  );

  const togglePin = useCallback(async (id: string, pinned: boolean) => {
    const updated = await api.updateConversation(id, { pinned });
    setConversations((prev) =>
      prev
        .map((c) => (c.id === id ? updated : c))
        .sort((a, b) => {
          if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
          return b.updated_at.localeCompare(a.updated_at);
        }),
    );
  }, []);

  const removeConversation = useCallback(
    async (id: string) => {
      await api.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeIdRef.current === id) {
        setActiveId(null);
        setMessages([]);
        setSteps([]);
      }
    },
    [],
  );

  const changeModel = useCallback(
    async (next: string) => {
      setModel(next);
      if (activeIdRef.current) {
        try {
          await api.updateConversation(activeIdRef.current, { model: next });
        } catch {
          /* model preference is non-critical */
        }
      }
    },
    [],
  );

  return {
    conversations,
    activeId,
    messages,
    model,
    useAgents,
    sending,
    steps,
    error,
    loadingConversation,
    setUseAgents,
    setError,
    send,
    selectConversation,
    newConversation,
    refreshConversations,
    renameConversation,
    togglePin,
    removeConversation,
    changeModel,
  };
}
