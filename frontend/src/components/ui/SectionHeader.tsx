import type { ReactNode } from 'react';

interface SectionHeaderProps {
  title:    string;
  action?:  ReactNode;
}

export default function SectionHeader({ title, action }: SectionHeaderProps) {
  return (
    <div className="panel-header">
      <h2 className="font-headline text-headline-sm text-on-surface">{title}</h2>
      {action && <div>{action}</div>}
    </div>
  );
}
