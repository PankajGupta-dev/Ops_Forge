import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import StatusBadge from '../components/ui/StatusBadge';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { knowledgeService } from '../services';
import type { KnowledgeEntry } from '../types';

export default function KnowledgeBase() {
  const navigate = useNavigate();
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [search, setSearch] = useState('');

  useEffect(() => {
    knowledgeService.getAll().then(setEntries);
  }, []);

  const filtered = entries.filter((e) =>
    e.title.toLowerCase().includes(search.toLowerCase()) ||
    e.service.toLowerCase().includes(search.toLowerCase()) ||
    e.tags.some((t) => t.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-headline text-headline-md text-on-surface">Incident Memory & Knowledge Base</h1>
          <p className="font-body text-body-md text-on-surface-variant">Indexed operational memory, postmortems, and learned systemic mitigations</p>
        </div>
      </div>

      {/* Search Bar */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-4 flex gap-4">
        <div className="flex items-center w-full bg-surface-container border border-border-subtle rounded-md px-3 py-2 focus-within:border-primary">
          <span className="material-symbols-outlined text-on-surface-variant text-[18px] mr-2">search</span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-transparent border-none outline-none font-mono text-mono-data w-full text-on-surface placeholder:text-on-surface-variant p-0 focus:ring-0"
            placeholder="Search knowledge base by keyword, service, or tag..."
          />
        </div>
      </div>

      {/* Knowledge Base Entries List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {filtered.map((entry) => (
          <div
            key={entry.id}
            className="bg-surface-container-lowest border border-border-subtle rounded-md p-6 flex flex-col justify-between hover:border-primary/50 transition-colors"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="font-mono text-mono-data text-on-surface-variant">{entry.date}</span>
                <StatusBadge status={entry.severity} />
              </div>
              <h3 className="font-headline text-headline-sm text-on-surface mb-2">{entry.title}</h3>
              <p className="font-body text-body-md text-on-surface-variant mb-4">{entry.summary}</p>

              <div className="flex items-center gap-2 flex-wrap mb-4">
                <Badge variant="primary">{entry.service}</Badge>
                {entry.tags.map((tag) => (
                  <Badge key={tag}>{tag}</Badge>
                ))}
              </div>
            </div>

            <div className="pt-4 border-t border-border-subtle flex items-center justify-between">
              <span className="font-mono text-[11px] text-on-surface-variant">
                {entry.hasPostmortem ? 'Postmortem Available' : 'Incident Logged'}
              </span>
              {entry.hasPostmortem && (
                <Button
                  variant="ghost"
                  size="sm"
                  icon="description"
                  onClick={() => navigate('/postmortem/pm-001')}
                >
                  View Postmortem
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
