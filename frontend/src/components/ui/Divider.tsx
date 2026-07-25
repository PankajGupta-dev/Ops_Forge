interface DividerProps {
  className?: string;
  label?: string;
}

export default function Divider({ className = '', label }: DividerProps) {
  if (label) {
    return (
      <div className={`relative flex items-center ${className}`}>
        <span className="flex-1 border-t border-border-subtle" />
        <span className="mx-3 label-caps text-label-caps text-on-surface-variant bg-background px-2 uppercase">
          {label}
        </span>
        <span className="flex-1 border-t border-border-subtle" />
      </div>
    );
  }
  return <hr className={`border-t border-border-subtle ${className}`} />;
}
