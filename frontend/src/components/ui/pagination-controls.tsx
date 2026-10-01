import { ChevronLeft, ChevronRight } from "lucide-react";

export function PaginationControls({
  total,
  limit,
  offset,
  onChange,
}: {
  total: number;
  limit: number;
  offset: number;
  onChange: (offset: number) => void;
}) {
  const page = Math.floor(offset / limit) + 1;
  const pageCount = Math.max(1, Math.ceil(total / limit));
  const hasPrevious = offset > 0;
  const hasNext = offset + limit < total;

  return (
    <nav className="pagination" aria-label="Pagination">
      <span>Page {page} of {pageCount}</span>
      <div>
        <button
          className="icon-button"
          type="button"
          aria-label="Previous page"
          disabled={!hasPrevious}
          onClick={() => onChange(Math.max(0, offset - limit))}
        >
          <ChevronLeft size={17} aria-hidden="true" />
        </button>
        <button
          className="icon-button"
          type="button"
          aria-label="Next page"
          disabled={!hasNext}
          onClick={() => onChange(offset + limit)}
        >
          <ChevronRight size={17} aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
}