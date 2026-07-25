import { useNavigate } from 'react-router-dom';
import type { Incident } from '../../types';
import StatusBadge from '../ui/StatusBadge';
import Badge from '../ui/Badge';

interface IncidentRowProps {
  incident: Incident;
}

export default function IncidentRow({ incident }: IncidentRowProps) {
  const navigate = useNavigate();

  return (
    <div
      onClick={() => navigate(`/incidents/${incident.id}/rca`)}
      className="flex items-start gap-4 p-5 border-b border-border-subtle last:border-0
                 hover:bg-surface-container cursor-pointer transition-colors duration-150 group"
    >
      {/* Severity indicator */}
      <div className={[
        'flex-shrink-0 w-1 self-stretch rounded-full',
        incident.severity === 'critical' ? 'bg-risk-red' :
        incident.severity === 'high'     ? 'bg-risk-amber' :
        incident.severity === 'medium'   ? 'bg-primary' : 'bg-outline',
      ].join(' ')} />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3 flex-wrap mb-1">
          <span className="font-mono text-mono-data text-on-surface-variant">{incident.id}</span>
          <StatusBadge status={incident.severity as any} />
          <StatusBadge status={incident.status as any} />
        </div>
        <p className="font-body text-body-md text-on-surface font-medium truncate group-hover:text-primary transition-colors">
          {incident.title}
        </p>
        <p className="font-body text-body-md text-on-surface-variant mt-0.5 line-clamp-1">
          {incident.description}
        </p>
        <div className="flex items-center gap-3 mt-2 flex-wrap">
          {incident.tags.map((tag) => (
            <Badge key={tag}>{tag}</Badge>
          ))}
        </div>
      </div>

      {/* Meta */}
      <div className="flex-shrink-0 text-right">
        <p className="font-mono text-mono-data text-on-surface-variant">
          {new Date(incident.openedAt).toLocaleDateString()}
        </p>
        {incident.mttr && (
          <p className="font-mono text-mono-data text-on-surface-variant mt-1">
            MTTR: {incident.mttr}
          </p>
        )}
        <div className="mt-2 flex justify-end">
          <span className="material-symbols-outlined text-on-surface-variant group-hover:text-primary
                           text-[16px] transition-colors">
            chevron_right
          </span>
        </div>
      </div>
    </div>
  );
}
