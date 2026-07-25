interface SparklineProps {
  data?: number[];
  color?: string;
  width?: number;
  height?: number;
  healthy?: boolean;
}

const DEFAULT_DATA = [10, 10, 2, 18, 10, 60, 10];

export default function Sparkline({
  data = DEFAULT_DATA,
  color,
  width = 60,
  height = 20,
  healthy = true,
}: SparklineProps) {
  const strokeColor = color ?? (healthy ? '#4ade80' : '#e05c4c');
  const max = Math.max(...data, 1);
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - (v / max) * height * 0.8 - height * 0.1;
    return `${x},${y}`;
  }).join(' L');

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      fill="none"
      className="opacity-80 group-hover:opacity-100 transition-opacity"
    >
      <polyline
        points={pts.replace('L', '')}
        stroke={strokeColor}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}
