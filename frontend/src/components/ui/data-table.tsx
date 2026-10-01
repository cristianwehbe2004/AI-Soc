import type { ReactNode } from "react";

export function DataTable({ children, label }: { children: ReactNode; label: string }) {
  return (
    <div className="table-wrap">
      <table className="data-table" aria-label={label}>{children}</table>
    </div>
  );
}