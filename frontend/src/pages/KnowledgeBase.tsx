import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import StatusBadge from '../components/ui/StatusBadge';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { knowledgeService } from '../services';
import type { KnowledgeEntry, SimilarityMatch } from '../types';

const SEARCH_DEBOUNCE_MS = 500;

export default function KnowledgeBase() {
  const navigate = useNavigate();
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [search, setSearch] = useState('');
  const [semanticResults, setSemanticResults] = useState<SimilarityMatch[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [loadingEntries, setLoadingEntries] = useState(true);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Initial load: fetch all stored incident records
  useEffect(() => {
    knowledgeService.getAll()
      .then(setEntries)
      .finally(() => setLoadingEntries(false));
  }, []);

  // Semantic search: fires against POST /memory/similar after debounce
  const runSemanticSearch = useCallback(async (query: string) => {
    if (!query.trim() || query.trim().length < 3) {
      setSemanticResults(null);
      return;
    }
    setSearching(true);
    try {
      const result = await knowledgeService.searchSimilar(query, 10);
      setSemanticResults(result.matches);
    } catch {
      setSemanticResults([]);
    } finally {
      setSearching(false);
    }
  }, []);

  const handleSearchChange = (value: string) => {
    setSearch(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!value.trim()) {
      setSemanticResults(null);
      return;
    }
    debounceRef.current = setTimeout(() => runSemanticSearch(value), SEARCH_DEBOUNCE_MS);
  };

  // Fallback local filter (when semantic results not yet available)
  const localFiltered = entries.filter((e) =>
    e.title.toLowerCase().includes(search.toLowerCase()) ||
    e.service.toLowerCase().includes(search.toLowerCase()) ||
    e.tags.some((t) => t.toLowerCase().includes(search.toLowerCase()))
  );

  const isSearching = search.trim().length >= 3;

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-headline text-headline-md text-on-surface">Incident Memory &amp; Knowledge Base</h1>
          <p className="font-body text-body-md text-on-surface-variant">
            Semantic vector search across indexed operational memories, postmortems, and systemic mitigations
          </p>
        </div>
      </div>

      {/* Semantic Search Bar */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-4 flex flex-col gap-3">
        <div className="flex items-center w-full bg-surface-container border border-border-subtle rounded-md px-3 py-2 focus-within:border-primary transition-colors">
          <span className="material-symbols-outlined text-on-surface-variant text-[18px] mr-2">
            {searching ? 'pending' : 'manage_search'}
          </span>
          <input
            type="text"
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="bg-transparent border-none outline-none font-mono text-mono-data w-full text-on-surface placeholder:text-on-surface-variant p-0 focus:ring-0"
            placeholder="Semantic search — describe an incident, root cause, or symptom…"
          />
          {search && (
            <button
              onClick={() => { setSearch(''); setSemanticResults(null); }}
              className="ml-2 text-on-surface-variant hover:text-on-surface"
            >
              <span className="material-symbols-outlined text-[16px]">close</span>
            </button>
          )}
        </div>
        {isSearching && (
          <p className="font-mono text-[11px] text-on-surface-variant">
            {searching
              ? 'Running semantic vector search…'
              : semanticResults === null
              ? 'Searching…'
              : `${semanticResults.length} result${semanticResults.length !== 1 ? 's' : ''} from vector search`}
          </p>
        )}
      </div>

      {/* ── Semantic Search Results ──────────────────────────── */}
      {isSearching && semanticResults !== null && (
        <div className="bg-surface-container-lowest border border-primary/20 rounded-md p-6">
          <h2 className="font-headline text-headline-sm text-on-surface mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[20px]">auto_awesome</span>
            Vector Similarity Results
            <span className="font-mono text-label-caps text-on-surface-variant ml-2">{semanticResults.length} matches</span>
          </h2>

          {semanticResults.length === 0 ? (
            <p className="font-mono text-mono-data text-on-surface-variant text-center py-6">
              No similar incidents found in knowledge base. Try a different query.
            </p>
          ) : (
            <div className="flex flex-col gap-3">
              {semanticResults.map((match) => (
                <div
                  key={match.incidentId}
                  className="p-4 bg-surface-container border border-border-subtle rounded-md flex flex-col gap-2"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1 flex-wrap">
                        <span className="font-mono text-mono-data text-on-surface-variant text-xs">{match.incidentId}</span>
                        <span className="font-mono text-xs px-2 py-0.5 rounded-full bg-primary/15 border border-primary/30 text-primary">
                          {match.similarityPercentage}% match
                        </span>
                        {match.outcomeSuccess && (
                          <span className="font-mono text-xs text-success flex items-center gap-1">
                            <span className="material-symbols-outlined text-[12px]">check_circle</span>
                            Recovery Succeeded
                          </span>
                        )}
                      </div>
                      <p className="font-body text-body-md text-on-surface font-medium">{match.rootCause}</p>
                      <p className="font-mono text-mono-data text-on-surface-variant text-xs mt-1">{match.explanation}</p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      icon="description"
                      onClick={() => navigate(`/postmortem/${match.incidentId}`)}
                    >
                      View
                    </Button>
                  </div>
                  {match.recoveryAction && (
                    <div className="font-mono text-[11px] text-on-surface-variant bg-background rounded p-2 border border-border-subtle">
                      Fix: {match.recoveryAction}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── All Entries / Filtered List ──────────────────────── */}
      {(!isSearching || semanticResults === null) && (
        <div>
          {loadingEntries ? (
            <div className="flex items-center justify-center py-16 text-on-surface-variant font-mono gap-2">
              <span className="material-symbols-outlined text-primary animate-spin">autorenew</span>
              Loading knowledge base…
            </div>
          ) : localFiltered.length === 0 ? (
            <div className="text-center py-16 text-on-surface-variant font-mono">
              <span className="material-symbols-outlined text-4xl block mb-2">menu_book</span>
              No entries found. Incidents will appear here after recovery is completed.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {localFiltered.map((entry) => (
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
                    <p className="font-body text-body-md text-on-surface-variant mb-4 line-clamp-3">{entry.summary}</p>

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
                        onClick={() => navigate(`/postmortem/${entry.id}`)}
                      >
                        View Postmortem
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
