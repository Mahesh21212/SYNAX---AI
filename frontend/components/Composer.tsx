'use client';

import { useEffect, useRef, useState } from 'react';
import { Mic, MicOff, Send, Paperclip, Sparkles, Square, X } from 'lucide-react';

import { cn, formatBytes } from '@/lib/utils';
import type { DocumentRecord } from '@/lib/types';

export function Composer({
  onSend,
  onUpload,
  onRemoveAttachment,
  sending,
  listening,
  interim,
  voiceSupported,
  onToggleVoice,
  useAgents,
  onToggleAgents,
  disabled,
}: {
  onSend: (text: string, attachments: DocumentRecord[]) => void;
  onUpload: (file: File) => Promise<DocumentRecord | null>;
  onRemoveAttachment: (id: string) => void;
  sending: boolean;
  listening: boolean;
  interim: string;
  voiceSupported: boolean;
  onToggleVoice: () => void;
  useAgents: boolean;
  onToggleAgents: () => void;
  disabled?: boolean;
}) {
  const [value, setValue] = useState('');
  const [attachments, setAttachments] = useState<DocumentRecord[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Auto-grow the textarea up to a sensible ceiling.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`;
  }, [value]);

  const submit = () => {
    const text = value.trim();
    if (!text || sending || disabled) return;
    onSend(text, attachments);
    setValue('');
    setAttachments([]);
  };

  const handleFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    setUploadError(null);
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        const doc = await onUpload(file);
        if (doc) setAttachments((prev) => [...prev, doc]);
      }
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const removeAttachment = (id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
    onRemoveAttachment(id);
  };

  return (
    <div className="border-t border-ink-800 bg-ink-950/80 px-4 pb-4 pt-3 backdrop-blur">
      <div className="mx-auto w-full max-w-3xl">
        {attachments.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1.5">
            {attachments.map((doc) => (
              <span
                key={doc.id}
                className="inline-flex items-center gap-1.5 rounded-lg border border-ink-600 bg-ink-850 px-2 py-1 text-[11px] text-slate-300"
              >
                <Paperclip className="h-3 w-3 text-slate-500" />
                <span className="max-w-[180px] truncate">{doc.filename}</span>
                <span className="text-slate-600">{formatBytes(doc.size_bytes)}</span>
                <button
                  type="button"
                  onClick={() => removeAttachment(doc.id)}
                  className="rounded p-0.5 text-slate-500 hover:bg-ink-700 hover:text-slate-200"
                  aria-label={`Remove ${doc.filename}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        )}

        {uploadError && (
          <p className="mb-2 text-[11px] text-signal-err">{uploadError}</p>
        )}

        {listening && (
          <div className="mb-2 flex items-center gap-2 rounded-lg border border-accent-700/40 bg-accent-600/10 px-3 py-2 text-[12px] text-accent-200">
            <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-accent-400" />
            Listening{interim ? `: ${interim}` : '…'}
          </div>
        )}

        <div
          className={cn(
            'rounded-2xl border border-ink-700 bg-ink-900/80 p-2 transition focus-within:border-ink-600',
            disabled && 'opacity-60',
          )}
        >
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            rows={1}
            placeholder="Ask SYNAX anything — it will plan, research, analyse and critique before answering."
            className="max-h-[220px] w-full resize-none bg-transparent px-2 py-2 text-[15px] leading-6 text-slate-100 placeholder:text-slate-600 focus:outline-none"
            disabled={disabled}
          />

          <div className="flex items-center justify-between gap-2 px-1">
            <div className="flex items-center gap-1">
              <input
                ref={fileRef}
                type="file"
                multiple
                className="hidden"
                accept=".pdf,.docx,.xlsx,.xlsm,.csv,.txt,.md,.json,.log,.yaml,.yml"
                onChange={(e) => void handleFiles(e.target.files)}
              />
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                disabled={uploading || disabled}
                className="focus-ring rounded-lg p-2 text-slate-500 transition hover:bg-ink-800 hover:text-slate-200 disabled:opacity-40"
                title="Attach a document"
              >
                <Paperclip className="h-4 w-4" />
              </button>

              {voiceSupported && (
                <button
                  type="button"
                  onClick={onToggleVoice}
                  className={cn(
                    'focus-ring rounded-lg p-2 transition',
                    listening
                      ? 'bg-accent-600/20 text-accent-300'
                      : 'text-slate-500 hover:bg-ink-800 hover:text-slate-200',
                  )}
                  title={listening ? 'Stop listening' : 'Speak your message'}
                >
                  {listening ? (
                    <MicOff className="h-4 w-4" />
                  ) : (
                    <Mic className="h-4 w-4" />
                  )}
                </button>
              )}

              <button
                type="button"
                onClick={onToggleAgents}
                className={cn(
                  'focus-ring flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-[11px] font-medium transition',
                  useAgents
                    ? 'bg-accent-600/15 text-accent-300'
                    : 'text-slate-500 hover:bg-ink-800 hover:text-slate-200',
                )}
                title="Toggle the multi-agent council"
              >
                <Sparkles className="h-3.5 w-3.5" />
                {useAgents ? 'Council' : 'Direct'}
              </button>
            </div>

            <button
              type="button"
              onClick={submit}
              disabled={!value.trim() || sending || disabled}
              className="focus-ring flex items-center gap-1.5 rounded-xl bg-accent-600 px-3.5 py-2 text-[13px] font-semibold text-white transition hover:bg-accent-500 disabled:cursor-not-allowed disabled:bg-ink-700 disabled:text-slate-500"
            >
              {sending ? (
                <>
                  <Square className="h-3.5 w-3.5" />
                  Working
                </>
              ) : (
                <>
                  <Send className="h-3.5 w-3.5" />
                  Send
                </>
              )}
            </button>
          </div>
        </div>

        <p className="mt-2 text-center text-[10px] text-slate-600">
          Enter to send · Shift+Enter for a new line · Voice uses your browser&apos;s
          speech APIs
        </p>
      </div>
    </div>
  );
}
