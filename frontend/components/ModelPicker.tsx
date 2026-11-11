'use client';

import { useEffect, useState } from 'react';
import { ChevronDown, Cpu } from 'lucide-react';

import * as api from '@/lib/api';
import { cn } from '@/lib/utils';
import type { ModelOption } from '@/lib/types';

export function ModelPicker({
  value,
  onChange,
  disabled,
}: {
  value: string;
  onChange: (model: string) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [models, setModels] = useState<ModelOption[]>([]);
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [query, setQuery] = useState('');

  useEffect(() => {
    let cancelled = false;
    void api
      .listModels()
      .then((catalogue) => {
        if (cancelled) return;
        setModels(catalogue.models);
        setConfigured(catalogue.configured);
      })
      .catch(() => {
        if (!cancelled) setConfigured(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selected = models.find((m) => m.id === value);
  const filtered = query
    ? models.filter(
        (m) =>
          m.name.toLowerCase().includes(query.toLowerCase()) ||
          m.id.toLowerCase().includes(query.toLowerCase()),
      )
    : models;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        disabled={disabled}
        className="focus-ring flex max-w-[240px] items-center gap-2 rounded-lg border border-ink-700 bg-ink-850 px-2.5 py-1.5 text-[12px] text-slate-300 transition hover:border-ink-600 disabled:opacity-50"
      >
        <Cpu className="h-3.5 w-3.5 shrink-0 text-slate-500" />
        <span className="truncate">{selected?.name ?? value}</span>
        <ChevronDown className="h-3.5 w-3.5 shrink-0 text-slate-500" />
      </button>

      {open && (
        <>
          <button
            type="button"
            aria-label="Close model picker"
            className="fixed inset-0 z-40 cursor-default"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 z-50 mt-1.5 w-[320px] overflow-hidden rounded-xl border border-ink-700 bg-ink-900 shadow-2xl">
            <div className="border-b border-ink-800 p-2">
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search models"
                className="w-full rounded-md bg-ink-850 px-2.5 py-1.5 text-[12px] text-slate-200 placeholder:text-slate-600 focus:outline-none"
              />
            </div>

            {configured === false && (
              <p className="border-b border-ink-800 bg-signal-warn/10 px-3 py-2 text-[11px] text-signal-warn">
                No OpenRouter key configured — showing a fallback list.
              </p>
            )}

            <ul className="max-h-[300px] overflow-y-auto p-1">
              {filtered.length === 0 && (
                <li className="px-3 py-4 text-center text-[12px] text-slate-600">
                  No models match
                </li>
              )}
              {filtered.map((model) => (
                <li key={model.id}>
                  <button
                    type="button"
                    onClick={() => {
                      onChange(model.id);
                      setOpen(false);
                      setQuery('');
                    }}
                    className={cn(
                      'w-full rounded-lg px-2.5 py-2 text-left transition',
                      model.id === value
                        ? 'bg-accent-600/15 text-accent-200'
                        : 'text-slate-300 hover:bg-ink-850',
                    )}
                  >
                    <span className="block truncate text-[12.5px] font-medium">
                      {model.name}
                    </span>
                    <span className="block truncate font-mono text-[10px] text-slate-600">
                      {model.id}
                      {model.context_length
                        ? ` · ${Math.round(model.context_length / 1000)}k ctx`
                        : ''}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}
