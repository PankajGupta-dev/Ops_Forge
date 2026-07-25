import type { MetricData } from '../../types';

interface MetricCardProps extends MetricData {
  cockpitGrid?: boolean;
}

export default function MetricCard({
  label, value, unit, icon, badge, cockpitGrid = true,
}: MetricCardProps) {
  return (
    <div className="relative overflow-hidden bg-surface-container-lowest border border-border-subtle rounded-md p-5 flex flex-col justify-between h-32 group">
      {/* Cockpit grid overlay */}
      {cockpitGrid && (
        <div className="absolute inset-0 cockpit-grid pointer-events-none z-0
                        opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
      )}

      {/* Header row */}
      <div className="relative z-10 flex justify-between items-start w-full">
        <span className="label-caps text-label-caps">{label}</span>
        <span className="material-symbols-outlined text-outline-variant text-sm select-none">{icon}</span>
      </div>

      {/* Value row */}
      <div className="relative z-10 flex items-baseline gap-2">
        <span className="font-mono text-display-lg text-on-surface tabular-nums tracking-tight leading-none">
          {value}
        </span>
        {unit && (
          <span className="font-mono text-mono-data text-on-surface-variant">{unit}</span>
        )}
        {badge && (
          <span className={[
            'ml-2 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border font-mono text-[10px] uppercase tracking-widest',
            badge.variant === 'success' ? 'bg-success/10 text-success border-success/30' :
            badge.variant === 'warning' ? 'bg-risk-amber/10 text-risk-amber border-risk-amber/30' :
            'bg-risk-red/10 text-risk-red border-risk-red/30',
          ].join(' ')}>
            <span className={[
              'w-1.5 h-1.5 rounded-full animate-pulse-dot',
              badge.variant === 'success' ? 'bg-success' :
              badge.variant === 'warning' ? 'bg-risk-amber' : 'bg-risk-red',
            ].join(' ')} />
            {badge.text}
          </span>
        )}
      </div>
    </div>
  );
}
