import type { TimelineEvent } from '../../types';

const TYPE_CONFIG: Record<TimelineEvent['type'], { icon: string; color: string }> = {
  detection:  { icon: 'sensors',          color: 'text-risk-red   border-risk-red/30' },
  escalation: { icon: 'campaign',         color: 'text-risk-amber border-risk-amber/30' },
  action:     { icon: 'build',            color: 'text-primary    border-primary/30' },
  resolution: { icon: 'check_circle',     color: 'text-success    border-success/30' },
};

interface TimelineProps {
  events: TimelineEvent[];
}

export default function Timeline({ events }: TimelineProps) {
  return (
    <ol className="relative flex flex-col gap-0">
      {events.map((ev, i) => {
        const cfg = TYPE_CONFIG[ev.type];
        const isLast = i === events.length - 1;
        return (
          <li key={i} className="relative flex gap-4 pl-0">
            {/* Line */}
            {!isLast && (
              <span className="absolute left-[15px] top-8 bottom-0 w-px bg-border-subtle" />
            )}
            {/* Icon */}
            <span className={[
              'flex-shrink-0 w-8 h-8 rounded-full border bg-surface-container-lowest flex items-center justify-center z-10',
              cfg.color,
            ].join(' ')}>
              <span className="material-symbols-outlined text-[14px]">{cfg.icon}</span>
            </span>
            {/* Content */}
            <div className="pb-6 flex-1">
              <p className="font-mono text-mono-data text-on-surface-variant">{ev.timestamp}</p>
              <p className="font-body text-body-md text-on-surface mt-0.5">{ev.event}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
