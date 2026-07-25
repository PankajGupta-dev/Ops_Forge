import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Button from '../components/ui/Button';
import { pipelineService } from '../services';
import type { WorkflowResult, StageResult } from '../types';

// ── The 11 canonical pipeline stages ──────────────────────────────────────────
const PIPELINE_STAGES = [
  { key: 'PLAN',           label: 'Planning',              icon: 'architecture',        agent: 'Agent 1' },
  { key: 'DEPLOY',         label: 'Deployment',            icon: 'rocket_launch',       agent: 'Agent 2' },
  { key: 'RUNNING',        label: 'Running Application',   icon: 'check_circle',        agent: 'System' },
  { key: 'FAILURE',        label: 'Failure Injection',     icon: 'bug_report',          agent: 'System' },
  { key: 'RCA',            label: 'Root Cause Analysis',   icon: 'psychology',          agent: 'Agent 3' },
  { key: 'SIMILARITY',     label: 'Similarity Search',     icon: 'manage_search',       agent: 'Agent 5' },
  { key: 'ENHANCED',       label: 'Enhanced Analysis',     icon: 'auto_awesome',        agent: 'Agent 3' },
  { key: 'RECOVERY_PLAN',  label: 'Recovery Approval',     icon: 'task_alt',            agent: 'Agent 4' },
  { key: 'EXECUTE',        label: 'Recovery Execution',    icon: 'settings_backup_restore', agent: 'Agent 2' },
  { key: 'VERIFY',         label: 'Recovery Verification', icon: 'fact_check',          agent: 'Agent 4' },
  { key: 'STORE_MEMORY',   label: 'Knowledge Storage',     icon: 'storage',             agent: 'Agent 5' },
];

/** Map backend stage keys to the canonical pipeline stage list. */
function resolveStages(result: WorkflowResult): Array<{ key: string; status: string; durationMs?: number; data?: any; error?: string }> {
  const backendMap: Record<string, StageResult> = {};
  for (const s of result.stages) {
    backendMap[s.stage] = s;
  }

  return PIPELINE_STAGES.map((ps) => {
    const backend = backendMap[ps.key];
    if (!backend) {
      // Derive implied stages from workflow state
      if (ps.key === 'RUNNING' && backendMap['DEPLOY']?.status === 'completed') {
        return { key: ps.key, status: 'completed' };
      }
      if (ps.key === 'FAILURE' && backendMap['RCA']) {
        return { key: ps.key, status: 'completed' };
      }
      if (ps.key === 'SIMILARITY' && backendMap['RCA']?.status === 'completed') {
        return { key: ps.key, status: 'completed', data: { count: result.similarIncidentsFound ?? 0 } };
      }
      if (ps.key === 'ENHANCED' && backendMap['RCA']?.status === 'completed') {
        return { key: ps.key, status: 'completed' };
      }
      if (ps.key === 'EXECUTE' && result.workflowStatus !== 'awaiting_approval') {
        return { key: ps.key, status: 'pending' };
      }
      if (ps.key === 'VERIFY' && result.workflowStatus !== 'awaiting_approval') {
        return { key: ps.key, status: 'pending' };
      }
      if (ps.key === 'STORE_MEMORY') {
        return { key: ps.key, status: 'pending' };
      }
      return { key: ps.key, status: 'pending' };
    }
    return {
      key: ps.key,
      status: backend.status,
      durationMs: backend.durationMs,
      data: backend.data,
      error: backend.error,
    };
  });
}

function stageColor(status: string) {
  switch (status) {
    case 'completed': return 'text-success border-success/30 bg-success/5';
    case 'running':   return 'text-primary border-primary/40 bg-primary/10 animate-pulse';
    case 'failed':    return 'text-risk-red border-risk-red/30 bg-risk-red/5';
    case 'skipped':   return 'text-on-surface-variant border-border-subtle bg-surface-container';
    default:          return 'text-on-surface-variant border-border-subtle bg-surface-container';
  }
}

function stageIcon(status: string, icon: string) {
  if (status === 'completed') return 'check_circle';
  if (status === 'failed')    return 'cancel';
  if (status === 'running')   return 'pending';
  return icon;
}

function completedCount(stages: ReturnType<typeof resolveStages>) {
  return stages.filter((s) => s.status === 'completed').length;
}

export default function DeploymentDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [workflow, setWorkflow] = useState<WorkflowResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    pipelineService
      .getStatus(id)
      .then((r) => { setWorkflow(r); setLoading(false); })
      .catch((err) => { setError(err?.message ?? 'Failed to load pipeline result.'); setLoading(false); });
  }, [id]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24 text-on-surface-variant font-mono">
        <span className="material-symbols-outlined text-primary text-4xl animate-spin">autorenew</span>
        Loading pipeline result…
      </div>
    );
  }

  if (error || !workflow) {
    return (
      <div className="p-8 text-center">
        <p className="text-risk-red font-mono">{error ?? 'Pipeline result not found.'}</p>
        <Button variant="ghost" icon="arrow_back" onClick={() => navigate('/deployments')} className="mt-4">
          Back to Deployments
        </Button>
      </div>
    );
  }

  const stages = resolveStages(workflow);
  const completed = completedCount(stages);
  const pct = Math.round((completed / stages.length) * 100);

  const rcaStage  = workflow.stages.find((s) => s.stage === 'RCA');
  const planStage = workflow.stages.find((s) => s.stage === 'PLAN');

  return (
    <div className="flex flex-col gap-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-on-surface-variant font-mono text-mono-data">
        <button onClick={() => navigate('/deployments')} className="hover:text-primary transition-colors">
          Deployments
        </button>
        <span>/</span>
        <span className="text-on-surface truncate max-w-[200px]">{workflow.traceId}</span>
      </div>

      {/* Summary Banner */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1 flex-wrap">
            <h1 className="font-headline text-headline-md text-on-surface">
              {workflow.appName ?? planStage?.data?.app_name ?? 'Pipeline Run'}
            </h1>
            <span className={[
              'font-mono text-label-caps px-2 py-1 rounded-full border text-[11px] uppercase',
              workflow.workflowStatus === 'awaiting_approval' ? 'text-risk-amber border-risk-amber/40 bg-risk-amber/10' :
              workflow.workflowStatus === 'completed'         ? 'text-success border-success/40 bg-success/10' :
              workflow.workflowStatus === 'failed'            ? 'text-risk-red border-risk-red/40 bg-risk-red/10' :
                                                                'text-primary border-primary/40 bg-primary/10'
            ].join(' ')}>
              {workflow.workflowStatus.replace(/_/g, ' ')}
            </span>
          </div>
          <p className="font-mono text-mono-data text-on-surface-variant">
            Trace: {workflow.traceId}
            {workflow.liveUrl && (
              <> · <a href={workflow.liveUrl} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">{workflow.liveUrl}</a></>
            )}
          </p>
        </div>

        <div className="flex items-center gap-3 flex-shrink-0 flex-wrap">
          {workflow.incidentDetected && workflow.recoveryActionId && (
            <Button
              variant="primary"
              icon="task_alt"
              onClick={() => navigate(`/incidents/${workflow.recoveryActionId}/recovery`)}
            >
              Review Recovery
            </Button>
          )}
          {workflow.workflowStatus === 'awaiting_approval' && !workflow.incidentDetected && (
            <span className="font-mono text-mono-data text-success flex items-center gap-2">
              <span className="material-symbols-outlined text-[16px]">check_circle</span>
              Deployment healthy — no incident detected
            </span>
          )}
        </div>
      </div>

      {/* Progress Bar + Percentage */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-5">
        <div className="flex justify-between items-center mb-2 font-mono text-mono-data">
          <span className="text-on-surface font-medium">Pipeline Progress</span>
          <span className="text-primary font-bold">{pct}%</span>
        </div>
        <div className="w-full bg-surface-container h-2 rounded-full overflow-hidden border border-border-subtle">
          <div
            className="bg-primary h-full transition-all duration-700 ease-out"
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="font-mono text-[11px] text-on-surface-variant mt-2">
          {completed} of {stages.length} stages complete
          {workflow.totalDurationMs && ` · Total: ${(workflow.totalDurationMs / 1000).toFixed(1)}s`}
        </p>
      </div>

      {/* ── 11-Stage Visualization ─────────────────────────────── */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6">
        <h2 className="font-headline text-headline-sm text-on-surface mb-5 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-[20px]">account_tree</span>
          Pipeline Stages
        </h2>

        <div className="flex flex-col gap-3">
          {stages.map((stage, idx) => {
            const def = PIPELINE_STAGES[idx];
            const colorClass = stageColor(stage.status);
            const iconName = stageIcon(stage.status, def.icon);

            return (
              <div
                key={def.key}
                className={`flex items-start gap-4 p-4 rounded-md border transition-colors ${colorClass}`}
              >
                {/* Stage Number + Connector */}
                <div className="flex flex-col items-center flex-shrink-0">
                  <div className={`w-8 h-8 rounded-full border flex items-center justify-center ${colorClass}`}>
                    <span className="material-symbols-outlined text-[18px]">{iconName}</span>
                  </div>
                  {idx < stages.length - 1 && (
                    <div className={`w-px flex-1 min-h-[16px] mt-1 ${stage.status === 'completed' ? 'bg-success/30' : 'bg-border-subtle'}`} />
                  )}
                </div>

                {/* Stage Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="font-mono text-mono-data text-on-surface font-medium">{def.label}</span>
                    <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider border border-border-subtle px-1.5 py-0.5 rounded">
                      {def.agent}
                    </span>
                    {stage.durationMs && (
                      <span className="font-mono text-[10px] text-on-surface-variant">
                        {(stage.durationMs / 1000).toFixed(1)}s
                      </span>
                    )}
                  </div>

                  {/* Stage output summary */}
                  {stage.status === 'completed' && stage.data && Object.keys(stage.data).length > 0 && (
                    <div className="mt-1 font-mono text-[11px] text-on-surface-variant">
                      {def.key === 'PLAN'    && stage.data.app_name   && `App: ${stage.data.app_name} · Platform: ${stage.data.platform} · Strategy: ${stage.data.strategy}`}
                      {def.key === 'DEPLOY'  && stage.data.status     && `Status: ${stage.data.status}${stage.data.live_url ? ` · ${stage.data.live_url}` : ''}`}
                      {def.key === 'RCA'     && stage.data.root_cause && `${stage.data.root_cause}`}
                      {def.key === 'SIMILARITY' && `${stage.data.count ?? stage.data.similar_incidents_found ?? 0} similar incidents found`}
                      {def.key === 'RECOVERY_PLAN' && stage.data.title && `Plan: ${stage.data.title} (${stage.data.risk_level} risk)`}
                    </div>
                  )}

                  {stage.error && (
                    <p className="mt-1 font-mono text-[11px] text-risk-red">{stage.error}</p>
                  )}
                </div>

                {/* Status label */}
                <span className={`font-mono text-[10px] uppercase tracking-wider flex-shrink-0 ${
                  stage.status === 'completed' ? 'text-success' :
                  stage.status === 'running'   ? 'text-primary' :
                  stage.status === 'failed'    ? 'text-risk-red' : 'text-on-surface-variant'
                }`}>
                  {stage.status}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── RCA Summary Card (if incident detected) ───────────── */}
      {workflow.incidentDetected && workflow.rootCause && (
        <div className="bg-surface-container-lowest border border-risk-amber/30 rounded-md p-6">
          <h2 className="font-headline text-headline-sm text-risk-amber mb-3 flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px]">warning</span>
            Incident Detected
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-mono-data mb-4">
            <div className="p-3 bg-surface-container rounded-md border border-border-subtle">
              <p className="label-caps mb-1">Severity</p>
              <p className="text-risk-amber font-bold uppercase">{workflow.severity}</p>
            </div>
            <div className="p-3 bg-surface-container rounded-md border border-border-subtle">
              <p className="label-caps mb-1">Confidence</p>
              <p className="text-primary font-bold">{workflow.confidence ? `${Math.round(workflow.confidence * 100)}%` : '—'}</p>
            </div>
            <div className="p-3 bg-surface-container rounded-md border border-border-subtle">
              <p className="label-caps mb-1">Similar Incidents Found</p>
              <p className="text-on-surface font-bold">{workflow.similarIncidentsFound ?? 0}</p>
            </div>
          </div>
          <div className="bg-surface-container p-4 rounded-md border border-border-subtle font-body text-body-md text-on-surface leading-relaxed mb-4">
            <p className="label-caps mb-2">Root Cause</p>
            <p>{workflow.rootCause}</p>
          </div>
          <div className="flex gap-3">
            <Button
              variant="primary"
              icon="task_alt"
              onClick={() => navigate(`/incidents/${workflow.recoveryActionId}/recovery`)}
            >
              Review Recovery Plan
            </Button>
            <Button
              variant="ghost"
              icon="psychology"
              onClick={() => navigate(`/incidents/${workflow.traceId}/rca`)}
            >
              View Full RCA
            </Button>
          </div>
        </div>
      )}

      {/* ── Plan Output ───────────────────────────────────────── */}
      {planStage?.data && (
        <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6">
          <h2 className="font-headline text-headline-sm text-on-surface mb-3 flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[20px]">architecture</span>
            Deployment Plan
          </h2>
          <div className="bg-background rounded-md border border-border-subtle p-4 font-mono text-mono-data text-primary overflow-x-auto">
            <pre className="text-xs">{JSON.stringify(planStage.data, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
