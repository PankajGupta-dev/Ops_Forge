import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ShaderCanvas from '../components/ui/ShaderCanvas';
import Divider from '../components/ui/Divider';
import { API_BASE_URL } from '../services/api';

const CONNECTIONS = [
  { id: 'github', icon: 'code',  label: 'Connect GitHub repository',    sub: 'Source control & CI/CD' },
  { id: 'railway', icon: 'cloud', label: 'Connect Railway account', sub: 'Cloud infrastructure' },
];

export default function Login() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const handleConnect = async (id: string) => {
    if (id === 'github') {
      setLoading(true);
      // Redirect browser directly to backend GitHub OAuth login endpoint
      window.location.href = `${API_BASE_URL}/auth/github/login?redirect=true`;
      return;
    }

    console.log(`Connecting ${id}…`);
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 relative overflow-hidden">

      {/* Shader background */}
      <div className="absolute inset-0 z-0 opacity-35">
        <ShaderCanvas className="absolute inset-0 w-full h-full" />
      </div>

      {/* Causal chain decorative SVG */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden opacity-20 flex items-center justify-center">
        <svg className="absolute stroke-border-subtle" fill="none" width="100%" height="100%"
             viewBox="0 0 1440 900" xmlns="http://www.w3.org/2000/svg">
          <path d="M200 450 L400 450 L500 250 L800 250" strokeDasharray="4 4" strokeWidth="1"/>
          <path d="M200 450 L400 450 L500 650 L800 650" strokeDasharray="4 4" strokeWidth="1"/>
          <circle cx="200" cy="450" fill="#37393d" r="4"/>
          <circle cx="400" cy="450" fill="#37393d" r="4"/>
          <circle cx="500" cy="250" fill="#37393d" r="4"/>
          <circle cx="500" cy="650" fill="#37393d" r="4"/>
        </svg>
      </div>

      {/* Login card */}
      <main className="relative z-10 w-full max-w-[420px] bg-surface border border-border-subtle
                       rounded-xl flex flex-col items-center pt-8 pb-6 px-8 shadow-2xl animate-fade-in">

        {/* Logo */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="w-16 h-16 rounded-full bg-primary-container border border-primary/30
                          flex items-center justify-center shadow-gold-glow">
            <span className="material-symbols-outlined text-primary text-[32px]">rocket_launch</span>
          </div>
          <h1 className="font-headline text-headline-md text-primary font-semibold">OpsForge</h1>
          <p className="font-body text-body-md text-on-surface-variant text-center max-w-[280px]">
            Connect your essential infrastructure services to begin deployment orchestration.
          </p>
        </div>

        {/* Connection buttons */}
        <div className="w-full flex flex-col gap-3 mb-6">
          {CONNECTIONS.map((conn) => (
            <button
              key={conn.id}
              disabled={loading}
              onClick={() => handleConnect(conn.id)}
              className="w-full flex items-center gap-4 py-3.5 px-4 bg-surface-container-low
                         border border-border-subtle rounded-md text-on-surface
                         hover:border-primary hover:shadow-gold-glow-sm hover:bg-surface-container
                         disabled:opacity-50 disabled:cursor-not-allowed
                         transition-all duration-150 group"
            >
              <div className="w-9 h-9 rounded-md bg-surface-container border border-border-subtle
                              flex items-center justify-center flex-shrink-0 group-hover:border-primary/30
                              transition-colors">
                <span className="material-symbols-outlined text-on-surface-variant group-hover:text-primary
                                 text-[18px] transition-colors">
                  {conn.id === 'github' && loading ? 'autorenew' : conn.icon}
                </span>
              </div>
              <div className="text-left">
                <p className="font-body text-body-md text-on-surface group-hover:text-primary transition-colors">
                  {conn.label}
                </p>
                <p className="font-mono text-mono-data text-on-surface-variant">
                  {conn.id === 'github' && loading ? 'Redirecting to GitHub…' : conn.sub}
                </p>
              </div>
              <span className="material-symbols-outlined text-outline text-[16px] ml-auto
                               group-hover:text-primary transition-colors">
                chevron_right
              </span>
            </button>
          ))}
        </div>

        {/* Divider */}
        <Divider label="or" className="w-full mb-5" />

        {/* Skip */}
        <button
          onClick={() => navigate('/dashboard')}
          className="font-mono text-label-caps text-on-surface-variant hover:text-primary
                     transition-colors mb-6 underline decoration-border-subtle hover:decoration-primary
                     underline-offset-4 uppercase tracking-widest"
        >
          Proceed with manual configuration
        </button>

        {/* Permissions note */}
        <div className="text-center w-full px-2">
          <p className="font-body text-body-md text-outline text-[11px] leading-relaxed flex items-start gap-1 justify-center">
            <span className="material-symbols-outlined text-outline text-[14px] flex-shrink-0 mt-0.5">lock</span>
            OpsForge requires read access to your repositories and orchestration access to your cloud provider.
            We never store source code.
          </p>
        </div>

        {/* Back to landing */}
        <button
          onClick={() => navigate('/')}
          className="mt-4 font-mono text-[11px] text-outline hover:text-primary transition-colors uppercase tracking-widest"
        >
          ← Back to home
        </button>
      </main>
    </div>
  );
}
