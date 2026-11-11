'use client';

import { useState } from 'react';
import {
  MessageSquarePlus,
  Pin,
  PinOff,
  Trash2,
  Search,
  MessagesSquare,
} from 'lucide-react';

import { cn, formatRelative, truncate } from '@/lib/utils';
import type { Conversation } from '@/lib/types';

export function Sidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  onTogglePin,
  open,
  onClose,
}: {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string | null) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onTogglePin: (id: string, pinned: boolean) => void;
  open: boolean;
  onClose: () => void;
}) {
  const [query, setQuery] = useState('');
  const [confirmId, setConfirmId] = useState<string | null>(null);

  const filtered = query
    ? conversations.filter((c) =>
        c.title.toLowerCase().includes(query.toLowerCase()),
      )
    : conversations;

  return (
    <>
      {open && (
        <button
          type="button"
          aria-label="Close sidebar"
          onClick={onClose}
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
        />
      )}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex w-[280px] flex-col border-r border-ink-800 bg-ink-900/95 backdrop-blur transition-transform lg:static lg:z-auto lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex items-center gap-2 px-4 pb-3 pt-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-600/20">
            <MessagesSquare className="h-4 w-4 text-accent-300" />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm font-semibold tracking-tight text-white">
              SYNAX AI
            </h1>
            <p className="text-[10px] text-slate-500">Multi-agent workspace</p>
          </div>
        </div>

        <div className="px-3">
          <button
            type="button"
            onClick={onNew}
            className="focus-ring flex w-full items-center justify-center gap-2 rounded-xl bg-accent-600 px-3 py-2 text-[13px] font-semibold text-white transition hover:bg-accent-500"
          >
            <MessageSquarePlus className="h-4 w-4" />
            New chat
          </button>
        </div>

        <div className="px-3 py-3">
          <div className="flex items-center gap-2 rounded-lg border border-ink-700 bg-ink-850 px-2.5 py-1.5">
            <Search className="h-3.5 w-3.5 text-slate-500" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search chats"
              className="w-full bg-transparent text-[12px] text-slate-200 placeholder:text-slate-600 focus:outline-none"
            />
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 pb-3">
          {filtered.length === 0 ? (
            <p className="px-3 py-6 text-center text-[12px] text-slate-600">
              {query ? 'No matching chats' : 'No chats yet'}
            </p>
          ) : (
            <ul className="space-y-0.5">
              {filtered.map((conversation) => {
                const active = conversation.id === activeId;
                return (
                  <li key={conversation.id} className="group relative">
                    <button
                      type="button"
                      onClick={() => {
                        onSelect(conversation.id);
                        onClose();
                      }}
                      className={cn(
                        'w-full rounded-lg px-2.5 py-2 pr-16 text-left transition',
                        active
                          ? 'bg-ink-800 text-white'
                          : 'text-slate-400 hover:bg-ink-850 hover:text-slate-200',
                      )}
                    >
                      <span className="flex items-center gap-1.5">
                        {conversation.pinned && (
                          <Pin className="h-3 w-3 shrink-0 text-accent-400" />
                        )}
                        <span className="truncate text-[12.5px] font-medium">
                          {truncate(conversation.title, 34)}
                        </span>
                      </span>
                      <span className="mt-0.5 block text-[10px] text-slate-600">
                        {conversation.message_count} messages ·{' '}
                        {formatRelative(conversation.updated_at)}
                      </span>
                    </button>

                    <div className="absolute right-1.5 top-1.5 flex items-center gap-0.5 opacity-0 transition group-hover:opacity-100 focus-within:opacity-100">
                      <button
                        type="button"
                        onClick={() =>
                          onTogglePin(conversation.id, !conversation.pinned)
                        }
                        className="rounded p-1 text-slate-500 hover:bg-ink-700 hover:text-slate-200"
                        title={conversation.pinned ? 'Unpin' : 'Pin'}
                      >
                        {conversation.pinned ? (
                          <PinOff className="h-3 w-3" />
                        ) : (
                          <Pin className="h-3 w-3" />
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmId(conversation.id)}
                        className="rounded p-1 text-slate-500 hover:bg-ink-700 hover:text-signal-err"
                        title="Delete"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>

                    {confirmId === conversation.id && (
                      <div className="absolute inset-x-1 top-full z-10 mt-1 rounded-lg border border-ink-600 bg-ink-800 p-2 shadow-xl">
                        <p className="mb-2 text-[11px] text-slate-300">
                          Delete this chat?
                        </p>
                        <div className="flex gap-1.5">
                          <button
                            type="button"
                            onClick={() => {
                              onDelete(conversation.id);
                              setConfirmId(null);
                            }}
                            className="flex-1 rounded-md bg-signal-err/20 px-2 py-1 text-[11px] font-medium text-signal-err hover:bg-signal-err/30"
                          >
                            Delete
                          </button>
                          <button
                            type="button"
                            onClick={() => setConfirmId(null)}
                            className="flex-1 rounded-md bg-ink-700 px-2 py-1 text-[11px] text-slate-300 hover:bg-ink-600"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </nav>

        <div className="border-t border-ink-800 px-4 py-3">
          <p className="text-[10px] leading-4 text-slate-600">
            Keys stay on the server. Voice uses your browser&apos;s speech APIs.
          </p>
        </div>
      </aside>
    </>
  );
}
