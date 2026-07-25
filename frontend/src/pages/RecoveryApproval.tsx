import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import { recoveryService } from '../services';
import { getAudioStreamUrl } from '../services/api';
import type { RecoveryAction } from '../types';

export default function RecoveryApproval() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [action, setAction] = useState<RecoveryAction | null>(null);
  const [loading, setLoading] = useState(true);
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [audioPlaying, setAudioPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (!id) return;
    recoveryService
      .getAction(id)
      .then((a) => { setAction(a); setLoading(false); })
      .catch((err) => { setError(err?.message ?? 'Failed to load recovery action.'); setLoading(false); });
  }, [id]);

  const handleApprove = async () => {
    if (!action) return;
    setIsApproving(true);
    setError(null);
    try {
      await recoveryService.approveAction(action.id, {
        approved: true,
        approver: 'Operator',
        approvalMode: 'ui',
      });
      navigate(`/incidents/${id}/verify`);
    } catch (err: any) {
      setError(err?.message ?? 'Approval failed. Please try again.');
      setIsApproving(false);
    }
  };

  const handleReject = async () => {
    if (!action) return;
    setIsRejecting(true);
    setError(null);
    try {
      await recoveryService.approveAction(action.id, {
        approved: false,
        approver: 'Operator',
        approvalMode: 'ui',
      });
      navigate('/incidents');
    } catch (err: any) {
      setError(err?.message ?? 'Rejection failed. Please try again.');
      setIsRejecting(false);
    }
  };

  const toggleAudio = () => {
    if (!audioRef.current) return;
    if (audioPlaying) {
      audioRef.current.pause();
      setAudioPlaying(false);
    } else {
      audioRef.current.play().catch(() => {});
      setAudioPlaying(true);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24 text-on-surface-variant font-mono">
        <span className="material-symbols-outlined text-primary text-4xl animate-spin">autorenew</span>
        Loading recovery plan…
      </div>
    );
  }

  if (error && !action) {
    return (
      <div className="p-8 text-center">
        <p className="text-risk-red font-mono mb-4">{error}</p>
        <Button variant="ghost" icon="arrow_back" onClick={() => navigate('/incidents')}>Back to Incidents</Button>
      </div>
    );
  }

  if (!action) return null;

  const audioUrl = getAudioStreamUrl(action.id);

  return (
    <div className="flex flex-col gap-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-on-surface-variant font-mono text-mono-data">
        <button onClick={() => navigate('/incidents')} className="hover:text-primary transition-colors">Incidents</button>
        <span>/</span>
        <button onClick={() => navigate(`/incidents/${id}/rca`)} className="hover:text-primary transition-colors">RCA</button>
        <span>/</span>
        <span className="text-primary font-medium">Recovery Approval</span>
      </div>

      {/* Recovery Plan Summary Banner */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1 flex-wrap">
            <span className="font-mono text-mono-data text-primary">STRATEGY #{action.id}</span>
            <Badge variant={action.riskLevel === 'high' ? 'red' : action.riskLevel === 'medium' ? 'amber' : 'primary'}>
              {action.riskLevel} Risk
            </Badge>
          </div>
          <h1 className="font-headline text-headline-md text-on-surface">{action.title}</h1>
          <p className="font-body text-body-md text-on-surface-variant mt-1">{action.description}</p>
        </div>

        <div className="flex items-center gap-3 flex-wrap flex-shrink-0">
          <Button
            variant="danger"
            icon="close"
            loading={isRejecting}
            onClick={handleReject}
          >
            Reject Strategy
          </Button>
          <Button
            variant="primary"
            icon="play_arrow"
            loading={isApproving}
            onClick={handleApprove}
          >
            Approve &amp; Execute
          </Button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 bg-risk-red/10 border border-risk-red/30 rounded-md font-mono text-mono-data text-risk-red flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px]">error</span>
          {error}
        </div>
      )}

      {/* ── Voice Narration Card ─────────────────────────────── */}
      {(action.narrative || action.audioUrl) && (
        <div className="bg-surface-container-lowest border border-primary/20 rounded-md p-6">
          <h2 className="font-headline text-headline-sm text-on-surface mb-3 flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[20px]">record_voice_over</span>
            AI Voice Briefing
          </h2>

          {/* Audio player */}
          <div className="flex items-center gap-4 mb-4 p-4 bg-surface-container rounded-md border border-border-subtle">
            <button
              onClick={toggleAudio}
              className="w-10 h-10 rounded-full bg-primary/20 border border-primary/40 flex items-center justify-center hover:bg-primary/30 transition-colors flex-shrink-0"
            >
              <span className="material-symbols-outlined text-primary text-[20px]">
                {audioPlaying ? 'pause' : 'play_arrow'}
              </span>
            </button>

            {/* Waveform animation */}
            <div className="flex items-end gap-0.5 h-8 flex-1">
              {Array.from({ length: 32 }).map((_, i) => (
                <div
                  key={i}
                  className={`w-1 rounded-full transition-all ${audioPlaying ? 'bg-primary' : 'bg-primary/30'}`}
                  style={{
                    height: audioPlaying
                      ? `${20 + Math.sin(Date.now() / 200 + i) * 12}px`
                      : `${4 + Math.sin(i * 0.8) * 10}px`,
                  }}
                />
              ))}
            </div>

            <span className="font-mono text-mono-data text-on-surface-variant text-sm flex-shrink-0">
              {audioPlaying ? 'Playing…' : 'Press to play'}
            </span>
          </div>

          {/* Hidden audio element */}
          <audio
            ref={audioRef}
            src={audioUrl}
            onEnded={() => setAudioPlaying(false)}
            onError={() => setAudioPlaying(false)}
          />

          {/* Narration text */}
          {action.narrative && (
            <div className="bg-surface-container p-4 rounded-md border border-border-subtle font-body text-body-md text-on-surface-variant leading-relaxed italic">
              &ldquo;{action.narrative}&rdquo;
            </div>
          )}
        </div>
      )}

      {/* ── Recovery Steps ───────────────────────────────────── */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6">
        <h2 className="font-headline text-headline-sm text-on-surface mb-4 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-[20px]">format_list_numbered</span>
          Orchestrated Recovery Steps ({action.steps.length})
        </h2>

        <div className="flex flex-col gap-3">
          {action.steps.map((step) => (
            <div
              key={step.id}
              className="p-4 bg-surface-container border border-border-subtle rounded-md flex flex-col gap-2"
            >
              <div className="flex items-center gap-3">
                <span className="w-6 h-6 rounded-full bg-primary/20 text-primary border border-primary/40 font-mono text-xs flex items-center justify-center font-bold flex-shrink-0">
                  {step.order}
                </span>
                <span className="font-body text-body-md text-on-surface font-medium">{step.title}</span>
              </div>
              {step.command && (
                <div className="bg-background rounded p-3 font-mono text-mono-data text-on-surface-variant border border-border-subtle overflow-x-auto">
                  <code>$ {step.command}</code>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* ── Impact Assessment ────────────────────────────────── */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6">
        <h3 className="font-headline text-headline-sm text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-risk-amber text-[20px]">shield</span>
          Safety &amp; Impact Assessment
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-mono-data">
          <div className="p-4 bg-surface-container rounded border border-border-subtle">
            <p className="label-caps mb-1">Estimated Downtime</p>
            <p className="text-on-surface font-medium">Zero Downtime (Rolling)</p>
          </div>
          <div className="p-4 bg-surface-container rounded border border-border-subtle">
            <p className="label-caps mb-1">Estimated Duration</p>
            <p className="text-on-surface font-medium">{action.estimatedDuration}</p>
          </div>
          <div className="p-4 bg-surface-container rounded border border-border-subtle">
            <p className="label-caps mb-1">Auto-Rollback Trigger</p>
            <p className="text-on-surface font-medium">Active (If 5xx &gt; 1%)</p>
          </div>
        </div>
      </div>
    </div>
  );
}
