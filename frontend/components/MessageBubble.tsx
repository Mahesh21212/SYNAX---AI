'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { cn, formatRelative } from '@/lib/utils';
import type { Message } from '@/lib/types';
import { AgentBadge } from './AgentBadge';

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };

  return (
    <button
      type="button"
      onClick={copy}
      className="focus-ring rounded-md px-2 py-1 text-[11px] text-slate-500 transition hover:bg-ink-800 hover:text-slate-300"
    >
      {copied ? 'Copied' : 'Copy'}
    </button>
  );
}

export function MessageBubble({
  message,
  onSpeak,
  speaking,
}: {
  message: Message;
  onSpeak?: (text: string) => void;
  speaking?: boolean;
}) {
  const isUser = message.role === 'user';

  return (
    <article
      className={cn(
        'group animate-fade-up',
        isUser ? 'flex justify-end' : 'flex justify-start',
      )}
    >
      <div className={cn('w-full max-w-3xl', isUser && 'flex flex-col items-end')}>
        <div className="mb-1.5 flex items-center gap-2 px-1">
          {isUser ? (
            <span className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
              You
            </span>
          ) : (
            <AgentBadge agent={message.agent ?? 'synth'} />
          )}
          <span className="text-[10px] text-slate-600">
            {formatRelative(message.created_at)}
          </span>
        </div>

        <div
          className={cn(
            'w-full rounded-2xl border px-4 py-3',
            isUser
              ? 'border-accent-700/40 bg-accent-600/10'
              : 'border-ink-700 bg-ink-850/80',
          )}
        >
          {message.attachments.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-1.5">
              {message.attachments.map((att) => (
                <span
                  key={att.id}
                  className="inline-flex items-center gap-1 rounded-md border border-ink-600 bg-ink-800 px-2 py-0.5 text-[11px] text-slate-300"
                  title={att.excerpt ?? att.filename}
                >
                  📎 {att.filename}
                </span>
              ))}
            </div>
          )}

          {isUser ? (
            <p className="whitespace-pre-wrap text-[15px] leading-7 text-slate-100">
              {message.content}
            </p>
          ) : (
            <div className="prose-synax">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {!isUser && (
          <div className="mt-1 flex items-center gap-1 opacity-0 transition group-hover:opacity-100 focus-within:opacity-100">
            <CopyButton text={message.content} />
            {onSpeak && (
              <button
                type="button"
                onClick={() => onSpeak(message.content)}
                className="focus-ring rounded-md px-2 py-1 text-[11px] text-slate-500 transition hover:bg-ink-800 hover:text-slate-300"
              >
                {speaking ? 'Speaking…' : 'Read aloud'}
              </button>
            )}
          </div>
        )}
      </div>
    </article>
  );
}
