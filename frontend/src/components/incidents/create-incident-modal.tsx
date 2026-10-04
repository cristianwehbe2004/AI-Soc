"use client";

import { useCreateIncident } from "@/lib/api/hooks";
import type { IncidentCreatePayload } from "@/lib/api/resources";
import { AlertTriangle, Plus, Sparkles, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

interface CreateIncidentModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CreateIncidentModal({ isOpen, onClose }: CreateIncidentModalProps) {
  const router = useRouter();
  const createMutation = useCreateIncident();
  const [tab, setTab] = useState<"preset" | "custom">("preset");
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const form = new FormData(event.currentTarget);

    let payload: IncidentCreatePayload;

    if (tab === "preset") {
      const preset = String(form.get("preset") || "brute_force") as
        | "brute_force"
        | "privilege_escalation"
        | "data_exfiltration";
      const username = String(form.get("username") || "victim-admin").trim();
      const sourceIp = String(form.get("source_ip") || "198.51.100.60").trim();

      const presetTitles = {
        brute_force: `Brute-force authentication attack on ${username}`,
        privilege_escalation: `Suspicious privilege escalation by ${username}`,
        data_exfiltration: `Mass data exfiltration attempt from ${sourceIp}`,
      };

      const presetDescriptions = {
        brute_force: `Multiple rapid login failures detected targeting account ${username} from ${sourceIp}, followed by a successful login.`,
        privilege_escalation: `Account ${username} engaged in suspicious role escalation following multiple failed authentication attempts.`,
        data_exfiltration: `High-volume file download exceeding safety threshold initiated by ${username} from IP ${sourceIp}.`,
      };

      payload = {
        title: presetTitles[preset],
        description: presetDescriptions[preset],
        severity: preset === "data_exfiltration" ? "critical" : "high",
        primary_username: username,
        primary_source_ip: sourceIp,
        preset_scenario: preset,
      };
    } else {
      const title = String(form.get("title") || "").trim();
      const description = String(form.get("description") || "").trim();
      const severity = String(form.get("severity") || "high") as "low" | "medium" | "high" | "critical";
      const username = String(form.get("username") || "").trim() || undefined;
      const sourceIp = String(form.get("source_ip") || "").trim() || undefined;

      if (title.length < 3) {
        setError("Title must be at least 3 characters long.");
        return;
      }
      if (description.length < 5) {
        setError("Description must be at least 5 characters long.");
        return;
      }

      payload = {
        title,
        description,
        severity,
        primary_username: username,
        primary_source_ip: sourceIp,
        preset_scenario: "custom",
      };
    }

    try {
      const result = await createMutation.mutateAsync(payload);
      onClose();
      router.push(`/incidents/${result.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to create incident.");
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(15, 23, 42, 0.6)",
        backdropFilter: "blur(4px)",
        display: "grid",
        placeItems: "center",
        zIndex: 9999,
        padding: "20px",
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: "min(100%, 540px)",
          backgroundColor: "#ffffff",
          borderRadius: "16px",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)",
          overflow: "hidden",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid #e2e8f0",
            display: "flex",
            justify: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <p className="eyebrow" style={{ margin: 0 }}>Create Case</p>
            <h2 style={{ margin: "4px 0 0 0", fontSize: "20px", fontWeight: 700 }}>New Incident Entry</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{ border: "none", background: "transparent", cursor: "pointer", color: "#64748b" }}
          >
            <X size={20} />
          </button>
        </div>

        <div style={{ padding: "24px" }}>
          <div
            style={{
              display: "flex",
              gap: "8px",
              marginBottom: "20px",
              background: "#f1f5f9",
              padding: "4px",
              borderRadius: "10px",
            }}
          >
            <button
              type="button"
              onClick={() => { setTab("preset"); setError(null); }}
              style={{
                flex: 1,
                padding: "8px 12px",
                borderRadius: "8px",
                border: "none",
                fontWeight: 600,
                fontSize: "14px",
                cursor: "pointer",
                background: tab === "preset" ? "#ffffff" : "transparent",
                color: tab === "preset" ? "#0f172a" : "#64748b",
                boxShadow: tab === "preset" ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
                transition: "all 0.2s",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "6px",
              }}
            >
              <Sparkles size={15} /> Attack Scenario Preset
            </button>
            <button
              type="button"
              onClick={() => { setTab("custom"); setError(null); }}
              style={{
                flex: 1,
                padding: "8px 12px",
                borderRadius: "8px",
                border: "none",
                fontWeight: 600,
                fontSize: "14px",
                cursor: "pointer",
                background: tab === "custom" ? "#ffffff" : "transparent",
                color: tab === "custom" ? "#0f172a" : "#64748b",
                boxShadow: tab === "custom" ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
                transition: "all 0.2s",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "6px",
              }}
            >
              <Plus size={15} /> Custom Manual Entry
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            {tab === "preset" ? (
              <>
                <label className="field-label" htmlFor="preset">Attack Scenario Template</label>
                <select
                  id="preset"
                  name="preset"
                  defaultValue="brute_force"
                  style={{ width: "100%", height: "46px", padding: "0 12px", borderRadius: "8px", border: "1px solid #cbd5e1", marginBottom: "16px" }}
                >
                  <option value="brute_force">Brute Force & Authentication Burst</option>
                  <option value="privilege_escalation">Suspicious Privilege Escalation</option>
                  <option value="data_exfiltration">High-Volume Data Exfiltration</option>
                </select>

                <label className="field-label" htmlFor="username">Target Username</label>
                <input
                  id="username"
                  name="username"
                  defaultValue="victim-admin"
                  required
                  placeholder="e.g. victim-admin"
                  style={{ width: "100%", height: "46px", padding: "0 12px", borderRadius: "8px", border: "1px solid #cbd5e1", marginBottom: "16px" }}
                />

                <label className="field-label" htmlFor="source_ip">Source IP Address</label>
                <input
                  id="source_ip"
                  name="source_ip"
                  defaultValue="198.51.100.60"
                  required
                  placeholder="e.g. 198.51.100.60"
                  style={{ width: "100%", height: "46px", padding: "0 12px", borderRadius: "8px", border: "1px solid #cbd5e1", marginBottom: "20px" }}
                />
              </>
            ) : (
              <>
                <label className="field-label" htmlFor="title">Incident Title</label>
                <input
                  id="title"
                  name="title"
                  required
                  minLength={3}
                  placeholder="e.g. Suspicious API Key Generation & Exfiltration"
                  style={{ width: "100%", height: "46px", padding: "0 12px", borderRadius: "8px", border: "1px solid #cbd5e1", marginBottom: "16px" }}
                />

                <label className="field-label" htmlFor="severity">Severity Level</label>
                <select
                  id="severity"
                  name="severity"
                  defaultValue="high"
                  style={{ width: "100%", height: "46px", padding: "0 12px", borderRadius: "8px", border: "1px solid #cbd5e1", marginBottom: "16px" }}
                >
                  <option value="low">Low (Risk ~30)</option>
                  <option value="medium">Medium (Risk ~55)</option>
                  <option value="high">High (Risk ~80)</option>
                  <option value="critical">Critical (Risk ~95)</option>
                </select>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "16px" }}>
                  <div>
                    <label className="field-label" htmlFor="username">Username (Optional)</label>
                    <input
                      id="username"
                      name="username"
                      placeholder="e.g. analyst@company.com"
                      style={{ width: "100%", height: "46px", padding: "0 12px", borderRadius: "8px", border: "1px solid #cbd5e1" }}
                    />
                  </div>
                  <div>
                    <label className="field-label" htmlFor="source_ip">Source IP (Optional)</label>
                    <input
                      id="source_ip"
                      name="source_ip"
                      placeholder="e.g. 192.168.1.10"
                      style={{ width: "100%", height: "46px", padding: "0 12px", borderRadius: "8px", border: "1px solid #cbd5e1" }}
                    />
                  </div>
                </div>

                <label className="field-label" htmlFor="description">Incident Description</label>
                <textarea
                  id="description"
                  name="description"
                  required
                  rows={3}
                  placeholder="Describe the initial security findings and evidence..."
                  style={{ width: "100%", padding: "12px", borderRadius: "8px", border: "1px solid #cbd5e1", marginBottom: "20px", fontFamily: "inherit" }}
                />
              </>
            )}

            {error && (
              <div className="form-error" role="alert" style={{ marginBottom: "16px" }}>
                <AlertTriangle size={16} /> {error}
              </div>
            )}

            <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
              <button className="secondary-button" type="button" onClick={onClose}>
                Cancel
              </button>
              <button
                className="primary-button"
                type="submit"
                disabled={createMutation.isPending}
              >
                <span>{createMutation.isPending ? "Creating Case..." : "Create & Investigate"}</span>
                <Sparkles size={16} />
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
