import type { ReactNode } from 'react';

interface Column<T> {
  key:     keyof T | string;
  header:  string;
  render?: (row: T) => ReactNode;
  align?:  'left' | 'right' | 'center';
}

interface DataTableProps<T> {
  columns:      Column<T>[];
  rows:         T[];
  keyFn:        (row: T) => string;
  onRowClick?:  (row: T) => void;
  emptyMessage?: string;
}

export default function DataTable<T>({
  columns, rows, keyFn, onRowClick, emptyMessage = 'No data available',
}: DataTableProps<T>) {
  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full text-left border-collapse">
        <thead className="border-b border-border-subtle bg-surface-container">
          <tr>
            {columns.map((col) => (
              <th
                key={String(col.key)}
                className={[
                  'px-5 py-3 label-caps text-label-caps font-medium whitespace-nowrap',
                  col.align === 'right'  ? 'text-right'  :
                  col.align === 'center' ? 'text-center' : 'text-left',
                ].join(' ')}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="font-mono text-mono-data text-on-surface divide-y divide-border-subtle">
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-5 py-10 text-center text-on-surface-variant text-body-md font-body">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr
                key={keyFn(row)}
                onClick={() => onRowClick?.(row)}
                className={[
                  'hover:bg-surface-container transition-colors group',
                  onRowClick ? 'cursor-pointer' : '',
                ].join(' ')}
              >
                {columns.map((col) => (
                  <td
                    key={String(col.key)}
                    className={[
                      'px-5 py-4',
                      col.align === 'right'  ? 'text-right'  :
                      col.align === 'center' ? 'text-center' : '',
                    ].join(' ')}
                  >
                    {col.render
                      ? col.render(row)
                      : String((row as Record<string, unknown>)[String(col.key)] ?? '')}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
