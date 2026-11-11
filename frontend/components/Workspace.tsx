'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Brain,
  FileText,
  Menu,
  PanelLeftClose,
  Sparkles,
  Volume2,
  VolumeX,
} from 'lucide-react';

import * as api from '@/lib/api';
import { cn } from '@/lib/utils';
import type { DocumentRecord } from '@/lib/types';
import { useChat } from '@/hooks/useChat';
import { useVoice } from '@/hooks/useVoice';

import { AgentTrace } from './AgentTrace';
import { Composer } from './Composer';
import { DocumentsPanel } from './DocumentsPanel';
import { MemoryPanel } from './MemoryPanel';
import { MessageBubble } from './MessageBubble';
import { ModelPicker } from './ModelPicker';
import { Sidebar } from './Sidebar';

const STARTERS = [
  'Explain how a multi-agent system differs from a single-prompt chatbot.',
  'Summarise the attached document and list its three weakest arguments.',
  'Draft a technical README section for a FastAPI + MongoDB service.',
  'Compare Postgres and MongoDB for a chat-history workload.',
];

export function Workspace() {
  const chat = useChat();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [docsOpen, setDocsOpen] = useState(false);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [pendingAttachments, setPendingAttachments] = useState<DocumentRecord[]>([]);
  const [autoSpeak, setAutoSpeak] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const lastSpokenRef = useRef<string | null>(null);

  const voice = useVoice({
    onFinalTranscript: (text) => {
      void chat.send(text, pendingAttachments);
      setPendingAttachments([]);
    },
  });

  // Keep the transcript pinned to the newest message.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, [chat.messages.length, chat.sending]);

  // Optionally read each new answer aloud.
  useEffect(() => {
    if (!autoSpeak || !voice.ttsSupported) return;
    const last = chat.messages[chat.messages.length - 1];
    if (!last || last.role !== 'assistant') return;
    if (lastSpokenRef.current === last.id) return;
    lastSpokenRef.current = last.id;
    voice.speak(last.content);
  }, [autoSpeak, chat.messages, voice]);

  const handleUpload = useCallback(
    async (file: File): Promise<DocumentRecord | null> => {
      const doc = await api.uploadDocument(file);
      setPendingAttachments((prev) => [...prev, doc]);
      return doc;
    },
    [],
  );

  const handleSend = useCallback(
    (text: string, attachments: DocumentRecord[]) => {
      void chat.send(text, attachments);
      setPendingAttachments([]);
    },
    [chat],
  );

  const isEmpty = chat.messages.length === 0;

  return (
    <div className="flex h-dvh overflow-hidden">
      <Sidebar
        conversations={chat.conversations}
        activeId={chat.activeId}
        onSelect={(id) => void chat.selectConversation(id)}
        onNew={chat.newConversation}
        onDelete={(id) => void chat.removeConversation(id)}
        onTogglePin={(id, pinned) => void chat.togglePin(id, pinned)}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        {/* --- Top bar ---------------------------------------------------- */}
        <header className="flex items-center justify-between gap-3 border-b border-ink-800 bg-ink-950/70 px-4 py-2.5 backdrop-blur">
          <div className="flex min-w-0 items-center gap-2">
            <button
              type="button"
              onClick={() => setSidebarOpen((v) => !v)}
              className="focus-ring rounded-lg p-1.5 text-slate-400 hover:bg-ink-800 hover:text-slate-200 lg:hidden"
              aria-label="Toggle sidebar"
            >
              <Menu className="h-4 w-4" />
            </button>
            <PanelLeftClose className="hidden h-4 w-4 text-ink-600 lg:block" />
            <h2 className="truncate text-[13px] font-medium text-slate-300">
              {chat.activeId
                ? chat.conversations.find((c) => c.id === chat.activeId)?.title ??
                  'Chat'
                : 'New chat'}
            </h2>
          </div>

          <div className="flex items-center gap-1.5">
            <ModelPicker
              value={chat.model}
              onChange={(m) => void chat.changeModel(m)}
              disabled={chat.sending}
            />

            <button
              type="button"
              onClick={() => setDocsOpen(true)}
              className="focus-ring rounded-lg p-2 text-slate-500 transition hover:bg-ink-800 hover:text-slate-200"
              title="Documents"
            >
              <FileText className="h-4 w-4" />
            </button>

            <button
              type="button"
              onClick={() => setMemoryOpen(true)}
              className="focus-ring rounded-lg p-2 text-slate-500 transition hover:bg-ink-800 hover:text-slate-200"
              title="Memory"
            >
              <Brain className="h-4 w-4" />
            </button>

            {voice.ttsSupported && (
              <button
                type="button"
                onClick={() => {
                  if (autoSpeak) voice.stopSpeaking();
                  setAutoSpeak((v) => !v);
                }}
                className={cn(
                  'focus-ring rounded-lg p-2 transition',
                  autoSpeak
                    ? 'bg-accent-600/15 text-accent-300'
                    : 'text-slate-500 hover:bg-ink-800 hover:text-slate-200',
                )}
                title={autoSpeak ? 'Stop reading answers aloud' : 'Read answers aloud'}
              >
                {autoSpeak ? (
                  <Volume2 className="h-4 w-4" />
                ) : (
                  <VolumeX className="h-4 w-4" />
                )}
              </button>
            )}
          </div>
        </header>

        {/* --- Transcript ------------------------------------------------- */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6">
          <div className="mx-auto w-full max-w-3xl space-y-6">
            {isEmpty && !chat.loadingConversation && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-accent-600/15">
                  <Sparkles className="h-7 w-7 text-accent-400" />
                </div>
                <h1 className="text-2xl font-semibold tracking-tight text-white">
                  What should the council work on?
                </h1>
                <p className="mt-2 max-w-md text-[13px] leading-6 text-slate-500">
                  A planner splits the request, specialists research and analyse in
                  parallel, a critic reviews the drafts, and SYNAX writes the answer.
                </p>

                <div className="mt-8 grid w-full max-w-xl gap-2 sm:grid-cols-2">
                  {STARTERS.map((starter) => (
                    <button
                      key={starter}
                      type="button"
                      onClick={() => handleSend(starter, [])}
                      className="focus-ring rounded-xl border border-ink-700 bg-ink-900/60 px-3.5 py-3 text-left text-[12.5px] leading-5 text-slate-400 transition hover:border-ink-600 hover:bg-ink-850 hover:text-slate-200"
                    >
                      {starter}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {chat.loadingConversation && (
              <p className="py-10 text-center text-[12px] text-slate-500">
                Loading conversation…
              </p>
            )}

            {chat.messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                onSpeak={voice.ttsSupported ? voice.speak : undefined}
                speaking={voice.speaking}
              />
            ))}

            {(chat.sending || chat.steps.length > 0) && (
              <AgentTrace steps={chat.steps} running={chat.sending} />
            )}

            {chat.error && (
              <div className="rounded-xl border border-signal-err/30 bg-signal-err/10 px-4 py-3">
                <p className="text-[12.5px] font-medium text-signal-err">
                  {chat.error}
                </p>
                <button
                  type="button"
                  onClick={() => chat.setError(null)}
                  className="mt-1.5 text-[11px] text-slate-400 underline hover:text-slate-200"
                >
                  Dismiss
                </button>
              </div>
            )}
          </div>
        </div>

        {/* --- Composer --------------------------------------------------- */}
        <Composer
          onSend={handleSend}
          onUpload={handleUpload}
          onRemoveAttachment={(id) =>
            setPendingAttachments((prev) => prev.filter((a) => a.id !== id))
          }
          sending={chat.sending}
          listening={voice.listening}
          interim={voice.interim}
          voiceSupported={voice.supported}
          onToggleVoice={voice.toggleListening}
          useAgents={chat.useAgents}
          onToggleAgents={() => chat.setUseAgents(!chat.useAgents)}
          disabled={chat.sending}
        />

        {voice.error && (
          <p className="px-4 pb-2 text-center text-[11px] text-signal-warn">
            {voice.error}
          </p>
        )}
      </main>

      <DocumentsPanel
        open={docsOpen}
        onClose={() => setDocsOpen(false)}
        onAttach={(doc) => setPendingAttachments((prev) => [...prev, doc])}
      />

      <MemoryPanel open={memoryOpen} onClose={() => setMemoryOpen(false)} />
    </div>
  );
}
