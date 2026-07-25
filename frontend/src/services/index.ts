// ──────────────────────────────────────────────────────────
// OpsForge — API Services (Mock Data Layer)
// ──────────────────────────────────────────────────────────

import {
  mockDeployments,
  mockIncidents,
  mockRCA,
  mockRecovery,
  mockKnowledgeEntries,
  mockPostmortem,
  mockIntegrations,
  mockMetrics
} from '../data/mock';
import type {
  Deployment,
  Incident,
  RootCauseAnalysis,
  RecoveryAction,
  KnowledgeEntry,
  Postmortem,
  Integration,
  MetricData
} from '../types';

export const deploymentService = {
  async getAll(): Promise<Deployment[]> {
    return Promise.resolve([...mockDeployments]);
  },
  async getById(id: string): Promise<Deployment | undefined> {
    return Promise.resolve(mockDeployments.find((d) => d.id === id));
  },
  async create(newDeployment: Omit<Deployment, 'id' | 'startedAt' | 'healthScore'>): Promise<Deployment> {
    const created: Deployment = {
      ...newDeployment,
      id: `dep-${Date.now().toString().slice(-3)}`,
      startedAt: new Date().toISOString(),
      healthScore: 100,
      logs: [
        { id: `l-${Date.now()}`, timestamp: new Date().toLocaleTimeString(), level: 'info', message: `Deployment triggered for ${newDeployment.service}` }
      ]
    };
    mockDeployments.unshift(created);
    return Promise.resolve(created);
  }
};

export const incidentService = {
  async getAll(): Promise<Incident[]> {
    return Promise.resolve([...mockIncidents]);
  },
  async getById(id: string): Promise<Incident | undefined> {
    return Promise.resolve(mockIncidents.find((i) => i.id === id));
  },
  async getRCA(incidentId: string): Promise<RootCauseAnalysis> {
    return Promise.resolve({ ...mockRCA, incidentId });
  }
};

export const recoveryService = {
  async getAction(incidentId: string): Promise<RecoveryAction> {
    return Promise.resolve({ ...mockRecovery, incidentId });
  },
  async approveAction(actionId: string): Promise<RecoveryAction> {
    return Promise.resolve({ ...mockRecovery, id: actionId, status: 'approved' });
  }
};

export const knowledgeService = {
  async getAll(): Promise<KnowledgeEntry[]> {
    return Promise.resolve([...mockKnowledgeEntries]);
  },
  async getPostmortem(id: string): Promise<Postmortem> {
    return Promise.resolve({ ...mockPostmortem, id });
  }
};

export const integrationService = {
  async getAll(): Promise<Integration[]> {
    return Promise.resolve([...mockIntegrations]);
  }
};

export const metricsService = {
  async getMetrics(): Promise<MetricData[]> {
    return Promise.resolve([...mockMetrics]);
  }
};
