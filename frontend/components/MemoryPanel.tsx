'use client';

import { useEffect, useState } from 'react';
import { Brain, Plus, Trash2, X } from 'lucide-react';

import * as api from '@/lib/api';
import { formatRelative } from '@/lib/utils';
import type { MemoryRecord } from '@/lib/types';

const KINDS = ['fact', 'preference', 'context'] as const;

export function MemoryPanel({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [memories, setMemories] = useState<MemoryRecord[]>([]);
  const [content, setContent] = useState('');
  const [kind, setKind] = useState<(typeof KINDS)[number]>('fact');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      setMemories(await api.listMemories());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load memory');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) void load();
  }, [open]);

  // Escape closes the panel.
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  const add = async () => {
    const text = content.trim();
    if (!text) return;
    try {
      const created = await api.createMemory({ content: text, kind });
      setMemories((prev) => [created, ...prev]);
      setContent('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save');
    }
  };

  const remove = async (id: string) => {
    try {
      await api.deleteMemory(id);
      setMemories((prev) => prev.filter((m) => m.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  };

  if (!open) return null;

  return (
    <>
      <button
        type="button"
        aria-label="Close memory"
        onClick={onClose}
        className="fixed inset-0 z-40 bg-black/50"
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Memory"
        className="fixed inset-y-0 right-0 z-50 flex w-full max-w-[400px] flex-col border-l border-ink-800 bg-ink-900 shadow-2xl"
      >
        <header className="flex items-center justify-between border-b border-ink-800 px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold text-white">Memory</h2>
            <p className="text-[11px] text-slate-500">
              Facts SYNAX carries between chats
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-500 hover:bg-ink-800 hover:text-slate-200"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="border-b border-ink-800 p-3">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={2}
            placeholder="e.g. Works on a fintech product; prefers concise answers."
            className="w-full resize-none rounded-lg border border-ink-700 bg-ink-850 px-3 py-2 text-[12.5px] text-slate-200 placeholder:text-slate-600 focus:border-ink-600 focus:outline-none"
          />
          <div className="mt-2 flex items-center justify-between">
            <div className="flex gap-1">
              {KINDS.map((k) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => setKind(k)}
                  className={
                    kind === k
                      ? 'rounded-md bg-accent-600/20 px-2 py-1 text-[11px] font-medium text-accent-300'
                      : 'rounded-md px-2 py-1 text-[11px] text-slate-500 hover:bg-ink-800'
                  }
                >
                  {k}
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={() => void add()}
              disabled={!content.trim()}
              className="flex items-center gap-1 rounded-lg bg-accent-600 px-2.5 py-1.5 text-[11px] font-semibold text-white hover:bg-accent-500 disabled:bg-ink-700 disabled:text-slate-500"
            >
              <Plus className="h-3 w-3" />
              Save
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          {error && (
            <p className="mb-2 rounded-lg bg-signal-err/10 px-3 py-2 text-[11px] text-signal-err">
              {error}
            </p>
          )}
          {loading && (
            <p className="py-8 text-center text-[12px] text-slate-500">Loading…</p>
          )}
          {!loading && memories.length === 0 && (
            <div className="py-12 text-center">
              <Brain className="mx-auto mb-2 h-8 w-8 text-ink-600" />
              <p className="text-[12px] text-slate-500">Nothing remembered yet.</p>
            </div>
          )}
          <ul className="space-y-1.5">
            {memories.map((memory) => (
              <li
                key={memory.id}
                className="group rounded-xl border border-ink-700 bg-ink-850 p-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-[12.5px] leading-5 text-slate-200">
                    {memory.content}
                  </p>
                  <button
                    type="button"
                    onClick={() => void remove(memory.id)}
                    className="shrink-0 rounded p-1 text-slate-600 opacity-0 transition hover:text-signal-err group-hover:opacity-100"
                    aria-label="Delete memory"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
                <p className="mt-1 text-[10px] text-slate-600">
                  {memory.kind} · {formatRelative(memory.created_at)}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </>
  );
}
