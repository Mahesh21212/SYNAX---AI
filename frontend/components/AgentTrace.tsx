'use client';

import { cn, formatDuration } from '@/lib/utils';
import type { AgentStep } from '@/lib/types';
import { AgentBadge } from './AgentBadge';

/**
 * Live trace of the agent council: which specialist ran, on what model, how
 * long it took, and whether it failed.
 */
export function AgentTrace({
  steps,
  running,
  className,
}: {
  steps: AgentStep[];
  running?: boolean;
  className?: string;
}) {
  if (!steps.length && !running) return null;

  return (
    <div
      className={cn(
        'rounded-xl border border-ink-700 bg-ink-900/60 p-3',
        className,
      )}
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          Agent council
        </span>
        {running && (
          <span className="flex items-center gap-1.5 text-[11px] text-accent-300">
            <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-accent-400" />
            working
          </span>
        )}
      </div>

      {steps.length === 0 && running && (
        <div className="space-y-1.5">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-4 animate-pulse-soft rounded bg-ink-800"
              style={{ animationDelay: `${i * 120}ms` }}
            />
          ))}
        </div>
      )}

      <ul className="space-y-1.5">
        {steps.map((step, index) => (
          <li
            key={`${step.agent}-${index}`}
            className="flex items-start gap-2 text-[12px]"
          >
            <span
              className={cn(
                'mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full',
                step.status === 'done' && 'bg-signal-ok',
                step.status === 'error' && 'bg-signal-err',
                step.status === 'running' && 'animate-pulse-soft bg-accent-400',
                step.status === 'pending' && 'bg-ink-500',
              )}
            />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-1.5">
                <AgentBadge agent={step.agent} />
                <span className="truncate font-mono text-[10px] text-slate-500">
                  {step.model}
                </span>
                {step.duration_ms ? (
                  <span className="text-[10px] text-slate-600">
                    {formatDuration(step.duration_ms)}
                  </span>
                ) : null}
              </div>
              {step.summary && (
                <p
                  className={cn(
                    'mt-0.5 line-clamp-2 text-[11px] leading-5',
                    step.status === 'error' ? 'text-signal-err' : 'text-slate-400',
                  )}
                >
                  {step.summary}
                </p>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
