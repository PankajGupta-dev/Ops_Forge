import { useState, useEffect } from 'react';
import IncidentRow from '../components/incident/IncidentRow';
import { incidentService } from '../services';
import type { Incident } from '../types';

export default function IncidentFeed() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [search, setSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    incidentService.getAll().then(setIncidents);
  }, []);

  const filtered = incidents.filter((inc) => {
    const matchesSearch = inc.title.toLowerCase().includes(search.toLowerCase()) ||
                          inc.id.toLowerCase().includes(search.toLowerCase()) ||
                          inc.service.toLowerCase().includes(search.toLowerCase());
    const matchesSeverity = severityFilter === 'all' || inc.severity === severityFilter;
    const matchesStatus = statusFilter === 'all' || inc.status === statusFilter;
    return matchesSearch && matchesSeverity && matchesStatus;
  });

  const criticalCount = incidents.filter((i) => i.severity === 'critical').length;
  const highCount     = incidents.filter((i) => i.severity === 'high').length;
  const openCount     = incidents.filter((i) => i.status === 'open' || i.status === 'investigating').length;

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-headline text-headline-md text-on-surface">Incident Feed</h1>
          <p className="font-body text-body-md text-on-surface-variant">Real-time alert stream and autonomous incident detection feed</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="font-mono text-mono-data text-risk-red bg-risk-red/10 border border-risk-red/30 px-3 py-1.5 rounded-full flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-risk-red animate-pulse-dot" />
            {openCount} Active Alerts
          </span>
        </div>
      </div>

      {/* Summary KPI Badges */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-4 flex items-center justify-between">
          <div>
            <p className="label-caps">Critical</p>
            <p className="font-mono text-headline-md text-risk-red">{criticalCount}</p>
          </div>
          <span className="material-symbols-outlined text-risk-red text-2xl">error</span>
        </div>
        <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-4 flex items-center justify-between">
          <div>
            <p className="label-caps">High Severity</p>
            <p className="font-mono text-headline-md text-risk-amber">{highCount}</p>
          </div>
          <span className="material-symbols-outlined text-risk-amber text-2xl">warning</span>
        </div>
        <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-4 flex items-center justify-between">
          <div>
            <p className="label-caps">Open / Active</p>
            <p className="font-mono text-headline-md text-primary">{openCount}</p>
          </div>
          <span className="material-symbols-outlined text-primary text-2xl">sensors</span>
        </div>
        <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-4 flex items-center justify-between">
          <div>
            <p className="label-caps font-mono">Avg MTTR</p>
            <p className="font-mono text-headline-md text-success">14m</p>
          </div>
          <span className="material-symbols-outlined text-success text-2xl">timer</span>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-4 flex flex-col sm:flex-row gap-4 items-center justify-between">
        <div className="flex items-center w-full sm:w-72 bg-surface-container border border-border-subtle rounded-md px-3 py-1.5 focus-within:border-primary">
          <span className="material-symbols-outlined text-on-surface-variant text-[16px] mr-2">search</span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-transparent border-none outline-none font-mono text-mono-data w-full text-on-surface placeholder:text-on-surface-variant p-0 focus:ring-0"
            placeholder="Filter by title, ID or service..."
          />
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          {/* Severity selector */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="input-base w-36"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          {/* Status selector */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="input-base w-36"
          >
            <option value="all">All Statuses</option>
            <option value="open">Open</option>
            <option value="investigating">Investigating</option>
            <option value="resolved">Resolved</option>
          </select>
        </div>
      </div>

      {/* Incidents Feed List */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md">
        {filtered.length > 0 ? (
          filtered.map((incident) => (
            <IncidentRow key={incident.id} incident={incident} />
          ))
        ) : (
          <div className="p-12 text-center text-on-surface-variant font-mono">
            No incidents found matching current filters.
          </div>
        )}
      </div>
    </div>
  );
}
