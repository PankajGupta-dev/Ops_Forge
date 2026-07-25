import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Surface scale
        'background':                '#111317',
        'surface':                   '#111317',
        'surface-dim':               '#111317',
        'surface-bright':            '#37393d',
        'surface-container-lowest':  '#0c0e11',
        'surface-container-low':     '#1a1c1f',
        'surface-container':         '#1e2023',
        'surface-container-high':    '#282a2d',
        'surface-container-highest': '#333538',
        'surface-variant':           '#44474e',
        'surface-white':             '#111317',

        // On-surface
        'on-surface':         '#e2e2e5',
        'on-surface-variant': '#c4c6d0',
        'on-background':      '#e2e2e5',
        'inverse-surface':    '#e2e2e5',
        'inverse-on-surface': '#313033',

        // Primary (Gold accent)
        'primary':               '#d4a056',
        'on-primary':            '#3f2e00',
        'primary-container':     '#594406',
        'on-primary-container':  '#f8e0b6',
        'primary-fixed':         '#f8e0b6',
        'primary-fixed-dim':     '#d4a056',
        'on-primary-fixed':      '#251a00',
        'on-primary-fixed-variant': '#494436',
        'inverse-primary':       '#755b20',
        'surface-tint':          '#d4a056',

        // Secondary (Steel-blue)
        'secondary':               '#d4c4a6',
        'on-secondary':            '#363022',
        'secondary-container':     '#4a4437',
        'on-secondary-container':  '#f5e0c1',
        'secondary-fixed':         '#f5e0c1',
        'secondary-fixed-dim':     '#b8a88c',
        'on-secondary-fixed':      '#251a08',
        'on-secondary-fixed-variant': '#4a4437',

        // Tertiary
        'tertiary':                '#d4c2a5',
        'on-tertiary':             '#362f1f',
        'tertiary-container':      '#4a4235',
        'on-tertiary-container':   '#f8ddb5',
        'tertiary-fixed':          '#f8ddb5',
        'tertiary-fixed-dim':      '#b8a68b',
        'on-tertiary-fixed':       '#251d11',
        'on-tertiary-fixed-variant': '#494236',

        // Error
        'error':              '#ffb4ab',
        'on-error':           '#690005',
        'error-container':    '#93000a',
        'on-error-container': '#ffdad6',

        // Outline
        'outline':         '#8e9099',
        'outline-variant': '#44474e',

        // Custom semantic
        'border-subtle': '#37393d',
        'risk-red':      '#e05c4c',
        'risk-amber':    '#e5ab3b',
        'success':       '#4ade80',
      },

      fontFamily: {
        'display':   ['"IBM Plex Sans"', 'sans-serif'],
        'headline':  ['"IBM Plex Sans"', 'sans-serif'],
        'body':      ['Inter', 'sans-serif'],
        'mono':      ['"JetBrains Mono"', 'monospace'],
      },

      fontSize: {
        'display-lg':      ['40px', { lineHeight: '48px', letterSpacing: '-0.02em', fontWeight: '600' }],
        'headline-md':     ['24px', { lineHeight: '32px', letterSpacing: '-0.01em', fontWeight: '500' }],
        'headline-sm':     ['18px', { lineHeight: '24px', fontWeight: '600' }],
        'headline-mobile': ['28px', { lineHeight: '36px', fontWeight: '600' }],
        'body-lg':         ['16px', { lineHeight: '24px', fontWeight: '400' }],
        'body-md':         ['14px', { lineHeight: '20px', fontWeight: '400' }],
        'label-caps':      ['12px', { lineHeight: '16px', letterSpacing: '0.05em', fontWeight: '500' }],
        'mono-data':       ['13px', { lineHeight: '18px', fontWeight: '400' }],
      },

      borderRadius: {
        DEFAULT: '0.125rem',  // 2px — machined/sharp
        sm:      '0.125rem',
        md:      '0.25rem',   // 4px
        lg:      '0.375rem',  // 6px
        xl:      '0.5rem',    // 8px
        full:    '9999px',
      },

      spacing: {
        'sidebar-width': '260px',
        'topbar-height': '64px',
        'container-max': '1440px',
        'gutter':        '24px',
        'margin-page':   '32px',
        'stack-sm':      '8px',
        'stack-md':      '16px',
      },

      boxShadow: {
        'gold-glow':  '0 0 12px rgba(212,160,86,0.25)',
        'gold-glow-sm': '0 0 8px rgba(212,160,86,0.15)',
        'red-glow':   '0 0 12px rgba(224,92,76,0.3)',
        'inner-subtle': 'inset 0 0 10px rgba(212,160,86,0.1)',
      },

      keyframes: {
        'pulse-dot': {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0.4' },
        },
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in': {
          from: { opacity: '0', transform: 'translateX(-8px)' },
          to:   { opacity: '1', transform: 'translateX(0)' },
        },
      },
      animation: {
        'pulse-dot': 'pulse-dot 2s ease-in-out infinite',
        'fade-in':   'fade-in 0.2s ease-out',
        'slide-in':  'slide-in 0.15s ease-out',
      },
    },
  },
  plugins: [],
}

export default config
