import { useNavigate } from 'react-router-dom';
import ShaderCanvas from '../components/ui/ShaderCanvas';
import Button from '../components/ui/Button';

const FEATURES = [
  {
    tag: 'Intelligence', icon: 'account_tree',
    title: 'Causal Chain Analysis',
    body: 'OpsForge ingests logs, metrics, and traces to autonomously infer root causes. Our deterministic models construct visual causal chains, highlighting the exact node failure across microservices.',
    bullets: ['Automated Trace Analysis', 'Topology Mapping'],
    imgAlt: 'Causal chain dashboard visualization',
    imgSrc: 'https://lh3.googleusercontent.com/aida-public/AB6AXuC52knSlGBeH4EIKAu-Vmv6RtHUAEuNC3V-1bkuhcu4uwWBEgTmKONdMrJ2clhXcR-S435-2CrrLV7HBXs8Rv7G4mUQfUTdsz8iWpttpW-QhcJP1xtEmCRj-RnnXUA3wZSfkOqWMLzShdjrEPOuBDYUEV9UkFM6eZtTK8rd7-zwCtpPPJ_dFdg68hrXEhIQ8qFFQKR0IFPTSlff1fjfpGokQm1GImQQVuyjC1r8VhQ6RZynsbgmPoOo_g',
    reversed: false,
  },
  {
    tag: 'Execution', icon: 'settings_backup_restore',
    title: 'One-Click Recovery',
    body: 'Execute complex rollback and scaling procedures with single-click authority. OpsForge handles the orchestration logic, ensuring state consistency and zero-downtime transitions.',
    bullets: ['State-Aware Rollbacks', 'Voice-Approved Actions'],
    imgAlt: 'Automated recovery sequence interface',
    imgSrc: 'https://lh3.googleusercontent.com/aida-public/AB6AXuChw2dp2nnpz9EheCF5Yj5E3m8vdBGdhyPBKPdTbt-Ar4Cdt74JmVK87MGsF9JksF530MNEPCF434dQfxp_ue8g9xOuCB3aJfQY4lxsloLkg0iIPnsBA4rMpWEG9uZJevA0bo-92pDc-6PCZkxlZGOm0QoZAK-6BcI0U45rfPPtXhGUh5vHyRpQwLttQ57oO3HoXKoo7w8Bcy6fYUP1LLgeRNFs_UGEK8GyvMuylmaXMQTskdSUMo_MsA',
    reversed: true,
  },
  {
    tag: 'Learning', icon: 'menu_book',
    title: 'Knowledge Base Integration',
    body: 'OpsForge learns from every incident. Post-mortems are automatically generated and indexed, turning operational crises into hardened systemic knowledge.',
    bullets: [],
    imgAlt: 'Knowledge base and postmortem library interface',
    imgSrc: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBmxsQiv0l-Kp2ax7VCRyrat-4135KaZrO4ah6EmD7fRp54ciXQPcL0DUcOJfus7FYWZTeALxjWg-IA56-h8uDL3proNXBgYopzpN0IJl0Di0L_JpsdUpq-dJQMHcbKQjSHO1BwWlIjQoBGTjzTzNibGAoXPkFegTIfRLP02GjwEJk0kYTkf5dz9nR3trqENngxWcB8XiV8y3C9QO00m_8xhmG7z4nENTDp7nzEvDDLJlgqtNfPJiz8KA',
    reversed: false,
  },
];

const INTEGRATIONS = ['GitHub', 'Railway', 'MongoDB Atlas', 'ElevenLabs'];

const FOOTER_LINKS = [
  { heading: 'Product',  links: ['Features', 'Pricing', 'Documentation'] },
  { heading: 'Company',  links: ['About', 'Blog', 'Careers'] },
  { heading: 'Legal',    links: ['Privacy Policy', 'Terms of Service', 'Security'] },
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background text-on-surface font-body flex flex-col">

      {/* ── Fixed top nav ── */}
      <header className="fixed top-0 left-0 right-0 h-16 bg-surface-container-lowest
                         border-b border-border-subtle z-50 flex items-center justify-between
                         px-margin-page">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-primary-container border border-primary/30
                          flex items-center justify-center shadow-gold-glow-sm">
            <span className="material-symbols-outlined text-primary text-[18px]">rocket_launch</span>
          </div>
          <span className="font-headline text-headline-sm text-primary font-bold">OpsForge</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/login')}
            className="font-mono text-mono-data text-on-surface hover:text-primary
                       transition-colors px-4 py-2 uppercase tracking-widest"
          >
            Login
          </button>
          <Button variant="primary" onClick={() => navigate('/login')} icon="rocket_launch">
            Get Started
          </Button>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="relative min-h-screen flex items-center justify-center
                          px-margin-page pt-16 overflow-hidden">
        {/* WebGL shader bg */}
        <div className="absolute inset-0 z-0 opacity-40">
          <ShaderCanvas className="absolute inset-0 w-full h-full" />
        </div>

        {/* Cockpit grid overlay */}
        <div className="absolute inset-0 z-0 cockpit-grid opacity-20 pointer-events-none" />

        {/* Content */}
        <div className="relative z-10 max-w-4xl mx-auto text-center flex flex-col items-center gap-8">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full
                          border border-primary/30 bg-primary/5 mb-2">
            <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse-dot" />
            <span className="font-mono text-label-caps text-primary uppercase tracking-widest">
              AI-Powered Cloud Operations
            </span>
          </div>

          <h1 className="font-headline text-[52px] md:text-[64px] leading-[1.1] font-semibold
                         text-on-surface tracking-tight">
            Autopilot for Production{' '}
            <span className="text-primary">Infrastructure</span>
          </h1>

          <p className="font-body text-body-lg text-on-surface-variant max-w-2xl">
            OpsForge autonomously deploys, monitors, and recovers your cloud applications
            with industrial precision. Stop reacting to alerts. Start commanding systems.
          </p>

          <div className="flex items-center gap-4 mt-4">
            <Button variant="primary" size="lg" onClick={() => navigate('/login')} iconRight="rocket_launch">
              Get Started
            </Button>
            <Button variant="ghost" size="lg" icon="play_circle">
              Watch Demo
            </Button>
          </div>

          {/* Social proof */}
          <div className="flex items-center gap-6 mt-8 text-on-surface-variant">
            {[
              { val: '99.9%', label: 'Uptime SLA' },
              { val: '< 14m', label: 'Avg. MTTR' },
              { val: '10k+', label: 'Deployments' },
            ].map((stat) => (
              <div key={stat.label} className="text-center">
                <p className="font-mono text-display-lg text-primary leading-none">{stat.val}</p>
                <p className="font-mono text-label-caps uppercase tracking-widest mt-1">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Feature sections ── */}
      <section className="py-24 px-margin-page bg-surface border-t border-border-subtle">
        <div className="max-w-container-max mx-auto flex flex-col gap-32">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className={`grid grid-cols-1 md:grid-cols-2 gap-16 items-center
                          ${f.reversed ? '' : ''}`}
            >
              <div className={`flex flex-col gap-6 ${f.reversed ? 'md:order-2' : 'md:order-1'}`}>
                <div className="inline-flex items-center gap-2 text-primary font-mono text-label-caps uppercase tracking-widest">
                  <span className="material-symbols-outlined text-[16px]">{f.icon}</span>
                  {f.tag}
                </div>
                <h2 className="font-headline text-headline-md text-on-surface">{f.title}</h2>
                <p className="font-body text-body-md text-on-surface-variant">{f.body}</p>
                {f.bullets.length > 0 && (
                  <ul className="flex flex-col gap-3 font-body text-body-md text-on-surface-variant mt-2">
                    {f.bullets.map((b) => (
                      <li key={b} className="flex items-center gap-3">
                        <span className="material-symbols-outlined text-primary text-[18px]">check_circle</span>
                        {b}
                      </li>
                    ))}
                  </ul>
                )}
                {f.tag === 'Learning' && (
                  <button className="self-start mt-2 text-primary font-mono text-mono-data
                                     hover:underline decoration-primary/60 flex items-center gap-2">
                    Explore Knowledge Base
                    <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                  </button>
                )}
              </div>

              <div className={`${f.reversed ? 'md:order-1' : 'md:order-2'}
                               machined-surface machined-border rounded-md p-3 shadow-2xl`}>
                <div
                  className="w-full h-[320px] rounded-sm border border-surface-bright bg-cover bg-center"
                  style={{ backgroundImage: `url('${f.imgSrc}')` }}
                  role="img"
                  aria-label={f.imgAlt}
                />
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Integration gallery ── */}
      <section className="py-24 px-margin-page bg-surface-container-lowest border-t border-border-subtle text-center">
        <div className="max-w-container-max mx-auto flex flex-col gap-12">
          <div>
            <h3 className="font-headline text-headline-md text-on-surface mb-3">
              Seamless Integration
            </h3>
            <p className="font-body text-body-md text-on-surface-variant max-w-2xl mx-auto">
              Connect your existing stack. OpsForge acts as the central command node
              for your entire infrastructure.
            </p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {INTEGRATIONS.map((name) => (
              <div
                key={name}
                className="machined-surface machined-border h-24 rounded-md flex items-center
                           justify-center font-mono text-label-caps text-on-surface-variant
                           uppercase tracking-widest hover:text-primary hover:border-primary/30
                           hover:shadow-gold-glow-sm transition-all duration-200 cursor-default"
              >
                {name}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="bg-surface-container-lowest border-t border-border-subtle pt-16 pb-8 px-margin-page">
        <div className="max-w-container-max mx-auto grid grid-cols-1 md:grid-cols-4 gap-12 mb-12">
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-full bg-primary-container border border-primary/20
                              flex items-center justify-center">
                <span className="material-symbols-outlined text-primary text-[14px]">rocket_launch</span>
              </div>
              <span className="font-headline text-headline-sm text-on-surface font-bold">OpsForge</span>
            </div>
            <p className="font-body text-body-md text-on-surface-variant text-sm">
              Industrial-grade AI operations for the modern cloud.
            </p>
          </div>
          {FOOTER_LINKS.map((col) => (
            <div key={col.heading} className="flex flex-col gap-3">
              <h4 className="font-mono text-label-caps text-on-surface uppercase tracking-widest mb-1">
                {col.heading}
              </h4>
              {col.links.map((l) => (
                <a
                  key={l}
                  href="#"
                  className="font-body text-body-md text-on-surface-variant hover:text-primary
                             transition-colors text-sm"
                >
                  {l}
                </a>
              ))}
            </div>
          ))}
        </div>
        <div className="max-w-container-max mx-auto pt-8 border-t border-surface-bright
                        flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="font-body text-body-md text-on-surface-variant text-xs">
            © 2024 OpsForge Systems. All rights reserved.
          </p>
          <div className="flex gap-4">
            <a href="#" className="text-on-surface-variant hover:text-primary transition-colors">
              <span className="material-symbols-outlined text-[20px]">language</span>
            </a>
            <a href="#" className="text-on-surface-variant hover:text-primary transition-colors">
              <span className="material-symbols-outlined text-[20px]">mail</span>
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
