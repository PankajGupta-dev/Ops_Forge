import type { CausalNode, CausalEdge } from '../../types';

interface CausalChainProps {
  nodes: CausalNode[];
  edges: CausalEdge[];
}

const NODE_W  = 120;
const NODE_H  = 48;
const SPACING = 160;
const SVG_H   = 200;
const OFFSET_Y = (SVG_H - NODE_H) / 2;

const TYPE_COLORS: Record<CausalNode['type'], { border: string; fill: string; text: string; icon: string }> = {
  trigger: { border: '#e5ab3b', fill: '#e5ab3b18', text: '#e5ab3b', icon: 'flash_on' },
  logic:   { border: '#44474e', fill: '#1e202318', text: '#c4c6d0', icon: 'settings' },
  impact:  { border: '#e05c4c', fill: '#e05c4c18', text: '#e05c4c', icon: 'warning' },
  action:  { border: '#d4a056', fill: '#d4a05618', text: '#d4a056', icon: 'build' },
};

export default function CausalChain({ nodes, edges }: CausalChainProps) {
  const totalWidth = nodes.length * SPACING;

  // Map node id → x centre
  const centres: Record<string, number> = {};
  nodes.forEach((n, i) => { centres[n.id] = i * SPACING + NODE_W / 2; });

  return (
    <div className="w-full overflow-x-auto">
      <svg
        width={totalWidth + 40}
        height={SVG_H}
        viewBox={`0 0 ${totalWidth + 40} ${SVG_H}`}
        className="min-w-full"
      >
        {/* Edges */}
        {edges.map((e, i) => {
          const x1 = (centres[e.from] ?? 0) + NODE_W / 2 - NODE_W / 2 + NODE_W;
          const x2 = (centres[e.to]   ?? 0) - NODE_W / 2 + NODE_W / 2;
          const y  = OFFSET_Y + NODE_H / 2;
          return (
            <line
              key={i}
              x1={x1} y1={y} x2={x2} y2={y}
              stroke="#44474e"
              strokeWidth="1"
              strokeDasharray={e.dashed ? '4 4' : undefined}
            />
          );
        })}

        {/* Nodes */}
        {nodes.map((node) => {
          const cfg = TYPE_COLORS[node.type];
          const cx  = centres[node.id];
          const x   = cx - NODE_W / 2;
          return (
            <g key={node.id}>
              <rect
                x={x} y={OFFSET_Y}
                width={NODE_W} height={NODE_H}
                rx={4}
                fill={cfg.fill}
                stroke={cfg.border}
                strokeWidth="1"
              />
              {/* Icon */}
              <text
                x={x + 14} y={OFFSET_Y + NODE_H / 2}
                dominantBaseline="central"
                fontSize={14}
                fontFamily="Material Symbols Outlined"
                fill={cfg.icon}
              >
                {node.icon}
              </text>
              {/* Label */}
              <text
                x={x + 28} y={OFFSET_Y + NODE_H / 2}
                dominantBaseline="central"
                fontSize={10}
                fontFamily="JetBrains Mono, monospace"
                fontWeight={500}
                fill={cfg.text}
                letterSpacing={0.5}
              >
                {node.label}
              </text>
              {/* Type tag */}
              <text
                x={x + NODE_W / 2} y={OFFSET_Y - 8}
                textAnchor="middle"
                fontSize={8}
                fontFamily="JetBrains Mono, monospace"
                fill={cfg.border}
                letterSpacing={1}
              >
                {node.type.toUpperCase()}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
