import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import StatusBadge from '../components/ui/StatusBadge';
import Button from '../components/ui/Button';
import CausalChain from '../components/ui/CausalChain';
import { pipelineService, incidentService } from '../services';
import type { WorkflowResult, RootCauseAnalysis as RCAType, CausalNode, CausalEdge } from '../types';

/**
 * Transform a list of causal chain strings into CausalNode + CausalEdge
 * arrays suitable for the existing CausalChain SVG component.
 */
function buildCausalGraph(chain: string[]): { nodes: CausalNode[]; edges: CausalEdge[] } {
  const nodes: CausalNode[] = chain.map((label, idx) => ({
    id: `n${idx + 1}`,
    label: label.length > 50 ? label.substring(0, 47) + '…' : label,
    type: idx === 0 ? 'trigger' : idx === chain.length - 1 ? 'impact' : 'logic',
    icon:
      idx === 0 ? 'trending_up' :
      idx === chain.length - 1 ? 'dangerous' :
      idx % 2 === 0 ? 'settings' : 'leak_add',
  }));

  const edges: CausalEdge[] = chain.slice(1).map((_, idx) => ({
    from: `n${idx + 1}`,
    to: `n${idx + 2}`,
    dashed: idx % 2 !== 0,
  }));

  return { nodes, edges };
}

/**
 * Build a RootCauseAnalysis view model from the WorkflowResult produced by
 * the orchestration pipeline — no extra RCA API call required.
 */
function workflowToRCA(workflow: WorkflowResult): RCAType {
  const rcaStage = workflow.stages.find((s) => s.stage === 'RCA');
  const causalChain: string[] = rcaStage?.data?.causal_chain ?? [workflow.rootCause ?? 'Root cause unavailable'];
  const { nodes, edges } = buildCausalGraph(causalChain);

  return {
    incidentId: workflow.traceId,
    summary: workflow.rootCause ?? 'No root cause identified.',
    confidence: workflow.confidence ? Math.round(workflow.confidence * 100) : 0,
    nodes,
    edges,
    narrative: rcaStage?.data?.summary ?? workflow.rootCause ?? '',
    generatedAt: workflow.finishedAt ?? workflow.startedAt ?? new Date().toISOString(),
  };
}

export default function RootCauseAnalysis() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [rca, setRca] = useState<RCAType | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [reanalyzing, setReanalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Primary: load RCA from existing pipeline result (no extra API call)
  useEffect(() => {
    if (!id) return;

    pipelineService
      .getStatus(id)
      .then((result) => {
        setWorkflow(result);
        setRca(workflowToRCA(result));
        setLoading(false);
      })
      .catch(async () => {
        // Fallback: load mock RCA if no pipeline result available for this ID
        try {
          const mockRca = await incidentService.getRCA(id);
          setRca(mockRca);
        } catch {
          setError('No RCA data available for this ID.');
        }
        setLoading(false);
      });
  }, [id]);

  /** Re-analyze: explicitly trigger a fresh POST /incident/analyze (user-initiated only). */
  const handleReanalyze = async () => {
    if (!workflow) return;
    setReanalyzing(true);
    setError(null);
    try {
      // Re-fetch from the pipeline status (backend may have updated)
      const fresh = await pipelineService.getStatus(id!);
      setWorkflow(fresh);
      setRca(workflowToRCA(fresh));
    } catch (err: any) {
      setError(err?.message ?? 'Re-analysis failed.');
    } finally {
      setReanalyzing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24 text-on-surface-variant font-mono">
        <span className="material-symbols-outlined text-primary text-4xl animate-spin">autorenew</span>
        Loading root cause analysis…
      </div>
    );
  }

  if (error || !rca) {
    return (
      <div className="p-8 text-center">
        <p className="text-risk-red font-mono mb-4">{error ?? 'No RCA data found.'}</p>
        <Button variant="ghost" icon="arrow_back" onClick={() => navigate('/incidents')}>Back to Incidents</Button>
      </div>
    );
  }

  const incidentId = id ?? 'Unknown';
  const severity = workflow?.severity ?? 'high';
  const incidentStatus = 'investigating';

  return (
    <div className="flex flex-col gap-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-on-surface-variant font-mono text-mono-data">
        <button onClick={() => navigate('/incidents')} className="hover:text-primary transition-colors">Incidents</button>
        <span>/</span>
        <span className="text-on-surface truncate max-w-[180px]">{incidentId}</span>
        <span>/</span>
        <span className="text-primary font-medium">Root Cause Analysis</span>
      </div>

      {/* Incident Banner */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1 flex-wrap">
            <span className="font-mono text-mono-data text-risk-red truncate max-w-[200px]">{incidentId}</span>
            <StatusBadge status={(severity as any) ?? 'high'} />
            <StatusBadge status="investigating" />
          </div>
          <h1 className="font-headline text-headline-md text-on-surface">
            {workflow?.appName ?? 'Incident Analysis'}
          </h1>
          <p className="font-body text-body-md text-on-surface-variant mt-1">{rca.summary}</p>
        </div>

        <div className="flex items-center gap-3 flex-shrink-0 flex-wrap">
          <div className="bg-primary/10 border border-primary/30 px-4 py-2 rounded-md text-center">
            <p className="label-caps text-[10px]">AI Confidence</p>
            <p className="font-mono text-headline-sm text-primary font-bold">{rca.confidence}%</p>
          </div>
          <Button
            variant="primary"
            icon="task_alt"
            onClick={() => navigate(`/incidents/${workflow?.recoveryActionId ?? id}/recovery`)}
          >
            Review Recovery Options
          </Button>
          <Button
            variant="ghost"
            icon="refresh"
            loading={reanalyzing}
            onClick={handleReanalyze}
          >
            Re-analyze
          </Button>
        </div>
      </div>

      {/* Causal Chain Graph */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-headline text-headline-sm text-on-surface flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[20px]">account_tree</span>
            Causal Chain Topology
          </h2>
          <span className="label-caps">Gemini Deterministic Model</span>
        </div>
        <div className="bg-background rounded-md border border-border-subtle p-4">
          {rca.nodes.length > 0 ? (
            <CausalChain nodes={rca.nodes} edges={rca.edges} />
          ) : (
            <p className="font-mono text-mono-data text-on-surface-variant text-center py-8">
              Causal chain data not available for this incident.
            </p>
          )}
        </div>
      </div>

      {/* Similar Incidents */}
      {workflow?.similarIncidentsFound !== undefined && workflow.similarIncidentsFound > 0 && (
        <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6">
          <h2 className="font-headline text-headline-sm text-on-surface mb-3 flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[20px]">manage_search</span>
            Historical Context — {workflow.similarIncidentsFound} Similar Incident{workflow.similarIncidentsFound !== 1 ? 's' : ''} Found
          </h2>
          {workflow.stages.find((s) => s.stage === 'RCA')?.data?.similar_incidents?.slice(0, 3)?.map((inc: any, i: number) => (
            <div key={i} className="p-3 bg-surface-container border border-border-subtle rounded-md mb-2 font-mono text-mono-data text-sm">
              <span className="text-primary">#{i + 1}</span> {inc.explanation ?? inc.root_cause ?? JSON.stringify(inc)}
            </div>
          ))}
        </div>
      )}

      {/* Narrative / Executive Summary */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6">
        <h2 className="font-headline text-headline-sm text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-[20px]">psychology</span>
          Autonomous Diagnostic Narrative
        </h2>
        <div className="bg-surface-container p-5 rounded-md border border-border-subtle font-body text-body-md text-on-surface leading-relaxed">
          <p className="mb-4">{rca.narrative || rca.summary}</p>
          {workflow?.stages.find((s) => s.stage === 'RCA')?.data?.recommendations && (
            <div className="p-3 bg-primary/10 border border-primary/30 rounded font-mono text-mono-data text-primary text-xs flex items-start gap-2">
              <span className="material-symbols-outlined text-[16px] flex-shrink-0 mt-0.5">info</span>
              <div>
                <p className="font-bold mb-1">Top Recommendation:</p>
                <p>{workflow.stages.find((s) => s.stage === 'RCA')?.data?.recommendations?.[0]?.action ?? 'See recovery plan for details.'}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
