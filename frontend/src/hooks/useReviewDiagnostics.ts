import { useEffect, useState } from "react";
import { fetchRunDiagnostics } from "../api/client";
import type { AppRun, DiagnosticsPayload } from "../types";

export function useReviewDiagnostics(run: AppRun | null) {
  const [diagnostics, setDiagnostics] = useState<DiagnosticsPayload | null>(null);
  const [diagnosticsError, setDiagnosticsError] = useState("");
  const artifactSignature = run?.artifacts.map((artifact) => artifact.name).sort().join(",") || "";
  const diagnosticsPath = typeof run?.result.diagnostics_path === "string" ? run.result.diagnostics_path : "";

  useEffect(() => {
    if (!run || run.mode !== "review") {
      setDiagnostics(null);
      setDiagnosticsError("");
      return;
    }
    const hasDiagnostics =
      run.artifacts.some((artifact) => artifact.name === "diagnostics_json") ||
      typeof run.result.diagnostics_path === "string";
    if (!hasDiagnostics) {
      setDiagnostics(null);
      setDiagnosticsError("");
      return;
    }

    let cancelled = false;
    fetchRunDiagnostics(run.id)
      .then((payload) => {
        if (!cancelled) {
          setDiagnostics(payload);
          setDiagnosticsError("");
        }
      })
      .catch((error: Error) => {
        if (!cancelled) {
          setDiagnostics(null);
          setDiagnosticsError(error.message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [artifactSignature, diagnosticsPath, run?.event_count, run?.id, run?.mode]);

  return { diagnostics, diagnosticsError };
}
