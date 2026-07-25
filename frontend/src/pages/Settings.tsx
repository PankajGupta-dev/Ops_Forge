import { useState, useEffect } from 'react';
import Button from '../components/ui/Button';
import StatusBadge from '../components/ui/StatusBadge';
import { integrationService } from '../services';
import type { Integration } from '../types';

export default function Settings() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);

  useEffect(() => {
    integrationService.getAll().then(setIntegrations);
  }, []);

  const toggleIntegration = (id: string) => {
    setIntegrations((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, connected: !item.connected } : item
      )
    );
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div>
        <h1 className="font-headline text-headline-md text-on-surface">Settings & Integrations</h1>
        <p className="font-body text-body-md text-on-surface-variant">Manage cloud provider connections, credentials, and automated recovery thresholds</p>
      </div>

      {/* Integrations Grid */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6">
        <h2 className="font-headline text-headline-sm text-on-surface mb-4 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-[20px]">extension</span>
          Connected Services & Infrastructure Providers
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {integrations.map((item) => (
            <div
              key={item.id}
              className="p-4 bg-surface-container border border-border-subtle rounded-md flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-md bg-surface-container-high border border-border-subtle flex items-center justify-center">
                  <span className="material-symbols-outlined text-primary text-[20px]">{item.icon}</span>
                </div>
                <div>
                  <p className="font-body text-body-md text-on-surface font-medium">{item.name}</p>
                  <p className="font-mono text-mono-data text-on-surface-variant text-[11px]">
                    {item.connected ? item.account || 'Connected' : 'Not Configured'}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <StatusBadge status={item.connected ? 'connected' : 'disconnected'} />
                <Button
                  variant={item.connected ? 'ghost' : 'primary'}
                  size="sm"
                  onClick={() => toggleIntegration(item.id)}
                >
                  {item.connected ? 'Disconnect' : 'Connect'}
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Autonomous Recovery Thresholds */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6">
        <h2 className="font-headline text-headline-sm text-on-surface mb-4 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-[20px]">tune</span>
          Autonomous Policy & Approvals
        </h2>

        <div className="flex flex-col gap-4 max-w-2xl font-mono text-mono-data">
          <div className="p-4 bg-surface-container border border-border-subtle rounded-md flex items-center justify-between">
            <div>
              <p className="text-on-surface font-medium">Require Approval for Low-Risk Rollbacks</p>
              <p className="text-on-surface-variant text-[11px]">If disabled, low-risk patches execute autonomously</p>
            </div>
            <input type="checkbox" className="w-4 h-4 accent-primary rounded cursor-pointer" defaultChecked />
          </div>

          <div className="p-4 bg-surface-container border border-border-subtle rounded-md flex items-center justify-between">
            <div>
              <p className="text-on-surface font-medium">Auto-Generate Postmortems</p>
              <p className="text-on-surface-variant text-[11px]">Index incident memory automatically upon recovery resolution</p>
            </div>
            <input type="checkbox" className="w-4 h-4 accent-primary rounded cursor-pointer" defaultChecked />
          </div>
        </div>
      </div>
    </div>
  );
}
