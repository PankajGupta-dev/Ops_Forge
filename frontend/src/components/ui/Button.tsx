import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Variant = 'primary' | 'ghost' | 'danger' | 'text';
type Size    = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?:    Size;
  icon?:    string;
  iconRight?: string;
  loading?: boolean;
  children: ReactNode;
}

const variantClasses: Record<Variant, string> = {
  primary: [
    'bg-primary-container text-on-primary-container',
    'border border-primary/40',
    'hover:bg-primary hover:text-on-primary',
    'shadow-inner-subtle',
    'disabled:opacity-40 disabled:cursor-not-allowed',
  ].join(' '),
  ghost: [
    'bg-transparent text-on-surface',
    'border border-border-subtle',
    'hover:border-primary hover:text-primary hover:shadow-gold-glow-sm',
    'disabled:opacity-40 disabled:cursor-not-allowed',
  ].join(' '),
  danger: [
    'bg-transparent text-risk-red',
    'border border-risk-red/40',
    'hover:bg-risk-red/10 hover:shadow-red-glow',
    'disabled:opacity-40 disabled:cursor-not-allowed',
  ].join(' '),
  text: [
    'bg-transparent text-primary',
    'border border-transparent',
    'hover:underline decoration-primary/60',
    'disabled:opacity-40 disabled:cursor-not-allowed',
  ].join(' '),
};

const sizeClasses: Record<Size, string> = {
  sm:  'px-3 py-1.5 text-label-caps gap-1.5',
  md:  'px-4 py-2.5 text-body-md gap-2',
  lg:  'px-6 py-3.5 text-body-md gap-2',
};

export default function Button({
  variant = 'primary',
  size    = 'md',
  icon,
  iconRight,
  loading = false,
  children,
  className = '',
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={[
        'inline-flex items-center justify-center font-mono rounded-md',
        'transition-all duration-150 select-none',
        variantClasses[variant],
        sizeClasses[size],
        className,
      ].join(' ')}
    >
      {loading ? (
        <span className="material-symbols-outlined animate-spin text-[16px]">progress_activity</span>
      ) : icon ? (
        <span className="material-symbols-outlined text-[16px]">{icon}</span>
      ) : null}
      {children}
      {iconRight && !loading && (
        <span className="material-symbols-outlined text-[16px]">{iconRight}</span>
      )}
    </button>
  );
}
