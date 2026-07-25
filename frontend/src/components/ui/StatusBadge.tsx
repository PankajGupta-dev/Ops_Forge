import type { DeploymentStatus, IncidentSeverity, IncidentStatus, RecoveryStatus } from '../../types';

type StatusType =
  | DeploymentStatus
  | IncidentSeverity
  | IncidentStatus
  | RecoveryStatus
  | 'connected'
  | 'disconnected';

interface StatusBadgeProps {
  status: StatusType;
  showDot?: boolean;
  size?: 'sm' | 'md';
}

const CONFIG: Record<string, { label: string; dot: string; bg: string; text: string; border: string }> = {
  // Deployment
  healthy:      { label: 'Healthy',      dot: 'bg-success',    bg: 'bg-success/10',    text: 'text-success',    border: 'border-success/30' },
  deploying:    { label: 'Deploying',    dot: 'bg-primary',    bg: 'bg-primary/10',    text: 'text-primary',    border: 'border-primary/30' },
  degraded:     { label: 'Degraded',     dot: 'bg-risk-amber', bg: 'bg-risk-amber/10', text: 'text-risk-amber', border: 'border-risk-amber/30' },
  failed:       { label: 'Failed',       dot: 'bg-risk-red',   bg: 'bg-risk-red/10',   text: 'text-risk-red',   border: 'border-risk-red/30' },
  pending:      { label: 'Pending',      dot: 'bg-outline',    bg: 'bg-outline/10',    text: 'text-outline',    border: 'border-outline/30' },
  'rolled-back':{ label: 'Rolled Back',  dot: 'bg-risk-amber', bg: 'bg-risk-amber/10', text: 'text-risk-amber', border: 'border-risk-amber/30' },
  // Severity
  critical:     { label: 'Critical',     dot: 'bg-risk-red',   bg: 'bg-risk-red/10',   text: 'text-risk-red',   border: 'border-risk-red/30' },
  high:         { label: 'High',         dot: 'bg-risk-amber', bg: 'bg-risk-amber/10', text: 'text-risk-amber', border: 'border-risk-amber/30' },
  medium:       { label: 'Medium',       dot: 'bg-primary',    bg: 'bg-primary/10',    text: 'text-primary',    border: 'border-primary/30' },
  low:          { label: 'Low',          dot: 'bg-outline',    bg: 'bg-outline/10',    text: 'text-outline',    border: 'border-outline/30' },
  // Incident status
  open:         { label: 'Open',         dot: 'bg-risk-red',   bg: 'bg-risk-red/10',   text: 'text-risk-red',   border: 'border-risk-red/30' },
  investigating:{ label: 'Investigating',dot: 'bg-risk-amber', bg: 'bg-risk-amber/10', text: 'text-risk-amber', border: 'border-risk-amber/30' },
  resolved:     { label: 'Resolved',     dot: 'bg-success',    bg: 'bg-success/10',    text: 'text-success',    border: 'border-success/30' },
  closed:       { label: 'Closed',       dot: 'bg-outline',    bg: 'bg-outline/10',    text: 'text-outline',    border: 'border-outline/30' },
  // Recovery
  approved:     { label: 'Approved',     dot: 'bg-success',    bg: 'bg-success/10',    text: 'text-success',    border: 'border-success/30' },
  executing:    { label: 'Executing',    dot: 'bg-primary',    bg: 'bg-primary/10',    text: 'text-primary',    border: 'border-primary/30' },
  verified:     { label: 'Verified',     dot: 'bg-success',    bg: 'bg-success/10',    text: 'text-success',    border: 'border-success/30' },
  rejected:     { label: 'Rejected',     dot: 'bg-risk-red',   bg: 'bg-risk-red/10',   text: 'text-risk-red',   border: 'border-risk-red/30' },
  // Integration
  connected:    { label: 'Connected',    dot: 'bg-success',    bg: 'bg-success/10',    text: 'text-success',    border: 'border-success/30' },
  disconnected: { label: 'Disconnected', dot: 'bg-outline',    bg: 'bg-outline/10',    text: 'text-outline',    border: 'border-outline/30' },
};

export default function StatusBadge({ status, showDot = true, size = 'sm' }: StatusBadgeProps) {
  const cfg = CONFIG[status] ?? CONFIG['pending'];
  const sizeClass = size === 'sm'
    ? 'px-2 py-0.5 text-[10px] gap-1.5'
    : 'px-2.5 py-1 text-label-caps gap-2';

  return (
    <span className={[
      'inline-flex items-center rounded-full border font-mono font-medium uppercase tracking-widest',
      cfg.bg, cfg.text, cfg.border, sizeClass,
    ].join(' ')}>
      {showDot && (
        <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 animate-pulse-dot ${cfg.dot}`} />
      )}
      {cfg.label}
    </span>
  );
}
