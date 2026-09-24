"use client";

import { AlertTriangle, RotateCcw } from "lucide-react";
import { useEffect } from "react";

export default function ProtectedError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("Protected route failed", error);
  }, [error]);

  return (
    <section className="empty-state panel">
      <AlertTriangle size={32} />
      <p className="eyebrow">Workspace unavailable</p>
      <h1>That security view could not be loaded.</h1>
      <p>Retry the request. If it continues, use the API request ID when reviewing audit logs.</p>
      <button className="primary-button retry-button" onClick={reset}><span>Try again</span><RotateCcw size={17} /></button>
    </section>
  );
}
