import { AlertCircle, Inbox, LoaderCircle, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";

export function LoadingState({ label = "Loading data" }: { label?: string }) {
  return (
    <div className="data-state" role="status" aria-live="polite">
      <LoaderCircle className="spin" size={24} aria-hidden="true" />
      <strong>{label}</strong>
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <div className="data-state data-state-error" role="alert">
      <AlertCircle size={24} aria-hidden="true" />
      <strong>Unable to load this view</strong>
      <p>{error.message}</p>
      {onRetry ? (
        <button className="secondary-button" type="button" onClick={onRetry}>
          <RefreshCw size={15} aria-hidden="true" /> Try again
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <div className="data-state" role="status">
      <Inbox size={26} aria-hidden="true" />
      <strong>{title}</strong>
      <p>{description}</p>
      {action}
    </div>
  );
}