import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import StatusBadge from '../components/ui/StatusBadge';
import Button from '../components/ui/Button';
import Timeline from '../components/ui/Timeline';
import { knowledgeService } from '../services';
import type { Postmortem } from '../types';

export default function PostmortemReport() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [postmortem, setPostmortem] = useState<Postmortem | null>(null);

  useEffect(() => {
    knowledgeService.getPostmortem(id || 'pm-001').then(setPostmortem);
  }, [id]);

  if (!postmortem) {
    return <div className="p-8 text-center text-on-surface-variant font-mono">Loading postmortem report...</div>;
  }

  return (
    <div className="flex flex-col gap-6 max-w-4xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-on-surface-variant font-mono text-mono-data">
        <button onClick={() => navigate('/knowledge')} className="hover:text-primary transition-colors">
          Knowledge Base
        </button>
        <span>/</span>
        <span className="text-on-surface">Postmortem</span>
        <span>/</span>
        <span className="text-primary font-medium">{postmortem.id}</span>
      </div>

      {/* Action Bar */}
      <div className="flex justify-between items-center bg-surface-container-lowest border border-border-subtle rounded-md p-4">
        <div>
          <span className="font-mono text-mono-data text-on-surface-variant">Document ID: {postmortem.id}</span>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" icon="print" onClick={() => window.print()}>
            Print / Export PDF
          </Button>
        </div>
      </div>

      {/* Main Document Content */}
      <article className="bg-surface-container-lowest border border-border-subtle rounded-md p-8 flex flex-col gap-8">
        {/* Title Section */}
        <div className="border-b border-border-subtle pb-6">
          <div className="flex items-center gap-3 mb-2">
            <StatusBadge status={postmortem.severity} size="md" />
            <span className="font-mono text-mono-data text-on-surface-variant">{postmortem.date}</span>
            <span className="font-mono text-mono-data text-primary">• Service: {postmortem.service}</span>
          </div>
          <h1 className="font-headline text-display-lg text-on-surface">{postmortem.title}</h1>
        </div>

        {/* Executive Summary / Root Cause */}
        <section>
          <h2 className="font-headline text-headline-sm text-primary mb-2 flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px]">psychology</span>
            1. Root Cause Summary
          </h2>
          <div className="bg-surface-container p-4 rounded-md border border-border-subtle font-body text-body-md text-on-surface">
            {postmortem.rootCause}
          </div>
        </section>

        {/* Business & System Impact */}
        <section>
          <h2 className="font-headline text-headline-sm text-primary mb-2 flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px]">impact_mine</span>
            2. System & Business Impact
          </h2>
          <div className="bg-surface-container p-4 rounded-md border border-border-subtle font-body text-body-md text-on-surface">
            {postmortem.impact}
          </div>
        </section>

        {/* Event Timeline */}
        <section>
          <h2 className="font-headline text-headline-sm text-primary mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px]">schedule</span>
            3. Incident Sequence & Timeline
          </h2>
          <div className="bg-surface-container p-6 rounded-md border border-border-subtle">
            <Timeline events={postmortem.timeline} />
          </div>
        </section>

        {/* Action Items */}
        <section>
          <h2 className="font-headline text-headline-sm text-primary mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px]">checklist</span>
            4. Preventative Action Items
          </h2>
          <div className="flex flex-col gap-3 font-mono text-mono-data">
            {postmortem.actionItems.map((item) => (
              <div
                key={item.id}
                className="p-4 bg-surface-container border border-border-subtle rounded-md flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2"
              >
                <div>
                  <p className="text-on-surface font-medium">{item.title}</p>
                  <p className="text-[11px] text-on-surface-variant">Owner: {item.owner} • Due: {item.dueDate}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={[
                    'px-2 py-0.5 rounded text-[10px] uppercase font-bold',
                    item.status === 'done' ? 'bg-success/20 text-success' :
                    item.status === 'in-progress' ? 'bg-primary/20 text-primary' : 'bg-outline/20 text-outline'
                  ].join(' ')}>
                    {item.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </article>
    </div>
  );
}
