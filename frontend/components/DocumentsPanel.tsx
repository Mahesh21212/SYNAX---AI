'use client';

import { useEffect, useState } from 'react';
import { FileText, Trash2, X, RefreshCw } from 'lucide-react';

import * as api from '@/lib/api';
import { formatBytes, formatRelative } from '@/lib/utils';
import type { DocumentRecord } from '@/lib/types';

export function DocumentsPanel({
  open,
  onClose,
  onAttach,
}: {
  open: boolean;
  onClose: () => void;
  onAttach: (doc: DocumentRecord) => void;
}) {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setDocuments(await api.listDocuments());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load documents');
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

  const remove = async (id: string) => {
    try {
      await api.deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  };

  if (!open) return null;

  return (
    <>
      <button
        type="button"
        aria-label="Close documents"
        onClick={onClose}
        className="fixed inset-0 z-40 bg-black/50"
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Documents"
        className="fixed inset-y-0 right-0 z-50 flex w-full max-w-[400px] flex-col border-l border-ink-800 bg-ink-900 shadow-2xl"
      >
        <header className="flex items-center justify-between border-b border-ink-800 px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold text-white">Documents</h2>
            <p className="text-[11px] text-slate-500">
              Uploaded files available for analysis
            </p>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => void load()}
              className="rounded-lg p-1.5 text-slate-500 hover:bg-ink-800 hover:text-slate-200"
              title="Refresh"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-500 hover:bg-ink-800 hover:text-slate-200"
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-3">
          {error && (
            <p className="mb-2 rounded-lg bg-signal-err/10 px-3 py-2 text-[11px] text-signal-err">
              {error}
            </p>
          )}

          {loading && (
            <p className="py-8 text-center text-[12px] text-slate-500">Loading…</p>
          )}

          {!loading && documents.length === 0 && (
            <div className="py-12 text-center">
              <FileText className="mx-auto mb-2 h-8 w-8 text-ink-600" />
              <p className="text-[12px] text-slate-500">No documents yet.</p>
              <p className="mt-1 text-[11px] text-slate-600">
                Attach a PDF, DOCX, XLSX or CSV from the composer.
              </p>
            </div>
          )}

          <ul className="space-y-1.5">
            {documents.map((doc) => (
              <li
                key={doc.id}
                className="group rounded-xl border border-ink-700 bg-ink-850 p-3"
              >
                <div className="flex items-start gap-2">
                  <FileText className="mt-0.5 h-4 w-4 shrink-0 text-accent-400" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[12.5px] font-medium text-slate-200">
                      {doc.filename}
                    </p>
                    <p className="mt-0.5 text-[10px] text-slate-600">
                      {formatBytes(doc.size_bytes)}
                      {doc.pages ? ` · ${doc.pages} pages` : ''}
                      {` · ${doc.char_count.toLocaleString()} chars`}
                      {` · ${formatRelative(doc.created_at)}`}
                    </p>
                    {doc.excerpt && (
                      <p className="mt-1.5 line-clamp-2 text-[11px] leading-4 text-slate-500">
                        {doc.excerpt}
                      </p>
                    )}
                  </div>
                </div>

                <div className="mt-2 flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => {
                      onAttach(doc);
                      onClose();
                    }}
                    className="rounded-md bg-accent-600/15 px-2 py-1 text-[11px] font-medium text-accent-300 hover:bg-accent-600/25"
                  >
                    Attach to chat
                  </button>
                  <button
                    type="button"
                    onClick={() => void remove(doc.id)}
                    className="rounded-md px-2 py-1 text-[11px] text-slate-500 hover:bg-ink-800 hover:text-signal-err"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </>
  );
}
