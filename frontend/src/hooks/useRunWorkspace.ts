import { useEffect, useRef, useState } from "react";
import { createRunEventSource, fetchRun, fetchRuns } from "../api/client";
import type { AppRun, RunEvent } from "../types";

const ACTIVE_STATUSES = new Set(["created", "queued", "running"]);

function uniqueEvents(primary: RunEvent[], extra: RunEvent[]): RunEvent[] {
  const merged: RunEvent[] = [];
  for (const item of [...primary, ...extra]) {
    if (!merged.some((existing) => existing.id === item.id)) {
      merged.push(item);
    }
  }
  return merged.sort((left, right) => left.id - right.id);
}

export function useRunWorkspace(mode?: string) {
  const [currentRun, setCurrentRun] = useState<AppRun | null>(null);
  const [recentRuns, setRecentRuns] = useState<AppRun[]>([]);
  const [liveEvents, setLiveEvents] = useState<RunEvent[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchRuns(mode)
      .then((runs) => {
        if (!cancelled) {
          setRecentRuns(runs);
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [mode]);

  useEffect(() => () => eventSourceRef.current?.close(), []);

  useEffect(() => {
    if (!currentRun || !ACTIVE_STATUSES.has(currentRun.status)) {
      return;
    }
    const timer = window.setInterval(() => {
      fetchRun(currentRun.id).then(setCurrentRun).catch(() => undefined);
      fetchRuns(mode).then(setRecentRuns).catch(() => undefined);
    }, 2500);
    return () => window.clearInterval(timer);
  }, [currentRun, mode]);

  function openEventStream(runId: string, after: number) {
    eventSourceRef.current?.close();
    const source = createRunEventSource(runId, after);
    source.onmessage = (event) => {
      const payload = JSON.parse(event.data) as RunEvent;
      setLiveEvents((previous) => uniqueEvents(previous, [payload]));
    };
    source.addEventListener("run.completed", () => {
      fetchRun(runId).then(setCurrentRun).catch(() => undefined);
      fetchRuns(mode).then(setRecentRuns).catch(() => undefined);
      source.close();
    });
    source.addEventListener("run.failed", () => {
      fetchRun(runId).then(setCurrentRun).catch(() => undefined);
      fetchRuns(mode).then(setRecentRuns).catch(() => undefined);
      source.close();
    });
    source.onerror = () => {
      source.close();
    };
    eventSourceRef.current = source;
  }

  function trackRun(run: AppRun) {
    setCurrentRun(run);
    setLiveEvents([]);
    setRecentRuns((previous) => [run, ...previous.filter((item) => item.id !== run.id)]);
    if (ACTIVE_STATUSES.has(run.status)) {
      openEventStream(run.id, run.event_count);
    }
  }

  function selectRun(run: AppRun) {
    trackRun(run);
  }

  const mergedEvents = uniqueEvents(currentRun?.events || [], liveEvents);
  const hydratedRun = currentRun ? { ...currentRun, events: mergedEvents } : null;

  return {
    currentRun: hydratedRun,
    recentRuns,
    selectRun,
    trackRun,
    refreshRuns: () => fetchRuns(mode).then(setRecentRuns),
  };
}
