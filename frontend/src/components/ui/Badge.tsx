import type { ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  variant?: 'default' | 'primary' | 'amber' | 'red' | 'outline';
  size?: 'sm' | 'md';
}

const variants = {
  default: 'bg-surface-container text-on-surface-variant border-border-subtle',
  primary: 'bg-primary/10 text-primary border-primary/30',
  amber:   'bg-risk-amber/10 text-risk-amber border-risk-amber/30',
  red:     'bg-risk-red/10 text-risk-red border-risk-red/30',
  outline: 'bg-transparent text-on-surface-variant border-border-subtle',
};

export default function Badge({ children, variant = 'default', size = 'sm' }: BadgeProps) {
  return (
    <span className={[
      'inline-flex items-center border rounded-sm font-mono uppercase tracking-widest',
      variants[variant],
      size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-1 text-label-caps',
    ].join(' ')}>
      {children}
    </span>
  );
}
