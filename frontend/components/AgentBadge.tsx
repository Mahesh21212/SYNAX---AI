'use client';

import { cn } from '@/lib/utils';
import type { AgentName } from '@/lib/types';

const AGENT_META: Record<
  AgentName,
  { label: string; tint: string; dot: string }
> = {
  planner: { label: 'Planner', tint: 'text-sky-300', dot: 'bg-sky-400' },
  researcher: { label: 'Researcher', tint: 'text-emerald-300', dot: 'bg-emerald-400' },
  analyst: { label: 'Analyst', tint: 'text-amber-300', dot: 'bg-amber-400' },
  writer: { label: 'Writer', tint: 'text-violet-300', dot: 'bg-violet-400' },
  critic: { label: 'Critic', tint: 'text-rose-300', dot: 'bg-rose-400' },
  synth: { label: 'SYNAX', tint: 'text-accent-300', dot: 'bg-accent-400' },
};

export function agentLabel(agent: AgentName): string {
  return AGENT_META[agent]?.label ?? agent;
}

export function AgentBadge({
  agent,
  className,
}: {
  agent: AgentName;
  className?: string;
}) {
  const meta = AGENT_META[agent] ?? AGENT_META.synth;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border border-ink-700 bg-ink-850 px-2.5 py-0.5 text-[11px] font-medium',
        meta.tint,
        className,
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', meta.dot)} />
      {meta.label}
    </span>
  );
}
