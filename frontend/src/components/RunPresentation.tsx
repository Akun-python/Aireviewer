import { artifactUrl } from "../api/client";
import type { AppRun, DiagnosticsPayload } from "../types";

const statusLabelMap: Record<string, string> = {
  created: "已创建",
  queued: "排队中",
  running: "运行中",
  completed: "已完成",
  failed: "失败",
};

const modeLabelMap: Record<string, string> = {
  review: "智能校稿",
  report: "课题报告",
  "report-complete": "报告完善",
  "report-integrate": "多章整合",
};

export function formatStatus(status: string): string {
  return statusLabelMap[status] || status;
}

export function formatMode(mode: string): string {
  return modeLabelMap[mode] || mode;
}

function formatSeverity(severity: string): string {
  return (
    {
      critical: "critical",
      warning: "warning",
      success: "success",
      info: "info",
    }[severity] || severity
  );
}

function renderModelOutput(run: AppRun) {
  const modelOutput = typeof run.result.model_output === "string" ? run.result.model_output : "";
  if (!modelOutput) {
    return null;
  }
  return (
    <details className="detail-box">
      <summary>模型摘要</summary>
      <p className="detail-text">{modelOutput}</p>
    </details>
  );
}

export function DiagnosticsPanel({ diagnostics }: { diagnostics: DiagnosticsPayload | null }) {
  if (!diagnostics) {
    return null;
  }
  return (
    <section className="stack-card">
      <div className="section-bar">
        <div>
          <h3>学术诊断卡片</h3>
          <p>{diagnostics.overview.summary}</p>
        </div>
        <div className="score-badge">
          <span>平均分</span>
          <strong>{diagnostics.overview.average_score}</strong>
        </div>
      </div>
      <div className="diagnostic-grid">
        {diagnostics.overview.cards.map((card) => (
          <article className={`diagnostic-card severity-${card.severity}`} key={card.key}>
            <div className="diagnostic-top">
              <strong>{card.label}</strong>
              <span className={`mini-pill severity-${card.severity}`}>{formatSeverity(card.severity)}</span>
            </div>
            <div className="diagnostic-score">score {card.score}</div>
            <p>{card.headline}</p>
          </article>
        ))}
      </div>
      <details className="detail-box">
        <summary>诊断 JSON 详情</summary>
        <pre>{JSON.stringify(diagnostics, null, 2)}</pre>
      </details>
    </section>
  );
}

export function RunResultPanel({
  run,
  diagnostics,
  title,
  emptyText,
}: {
  run: AppRun | null;
  diagnostics: DiagnosticsPayload | null;
  title: string;
  emptyText: string;
}) {
  if (!run) {
    return <section className="stack-card empty-card">{emptyText}</section>;
  }

  const logLines = run.events
    .filter((event) => event.type === "run.log" || event.type.startsWith("run."))
    .map((event) => `[${event.ts}] ${event.message || event.type}`);

  return (
    <section className="stack-card">
      <div className="section-bar">
        <div>
          <span className="section-eyebrow">{formatMode(run.mode)}</span>
          <h3>{title}</h3>
          <p>{run.title}</p>
        </div>
        <span className={`status-pill status-${run.status}`}>{formatStatus(run.status)}</span>
      </div>
      {run.error ? <div className="error-banner">{run.error}</div> : null}
      <div className="meta-grid">
        <div className="meta-tile">
          <span>创建时间</span>
          <strong>{run.created_at || "-"}</strong>
        </div>
        <div className="meta-tile">
          <span>输入对象</span>
          <strong>{run.input_filename || "-"}</strong>
        </div>
        <div className="meta-tile">
          <span>产物数量</span>
          <strong>{run.artifacts.length}</strong>
        </div>
      </div>
      {run.artifacts.length ? (
        <div className="artifact-grid">
          {run.artifacts.map((artifact) => (
            <a className="artifact-card" href={artifactUrl(artifact.download_url)} key={artifact.name} rel="noreferrer" target="_blank">
              <strong>{artifact.label}</strong>
              <span>{artifact.filename}</span>
            </a>
          ))}
        </div>
      ) : (
        <div className="empty-inline">当前还没有产物文件。</div>
      )}
      <DiagnosticsPanel diagnostics={diagnostics} />
      {renderModelOutput(run)}
      <div className="log-shell">
        <div className="section-bar compact">
          <strong>运行日志</strong>
          <span>{logLines.length} lines</span>
        </div>
        <pre>{logLines.length ? logLines.join("\n") : "等待日志..."}</pre>
      </div>
    </section>
  );
}

export function RunListPanel({
  runs,
  currentRunId,
  onSelect,
  title,
}: {
  runs: AppRun[];
  currentRunId?: string;
  onSelect: (run: AppRun) => void;
  title: string;
}) {
  return (
    <section className="stack-card">
      <div className="section-bar compact">
        <h3>{title}</h3>
        <span>{runs.length}</span>
      </div>
      <div className="run-list">
        {runs.length ? (
          runs.map((run) => (
            <button
              className={`run-list-item ${currentRunId === run.id ? "run-list-item-active" : ""}`}
              key={run.id}
              onClick={() => onSelect(run)}
              type="button"
            >
              <div className="run-list-top">
                <strong>{run.title}</strong>
                <span className={`status-pill status-${run.status}`}>{formatStatus(run.status)}</span>
              </div>
              <div className="run-list-meta">
                <span>{formatMode(run.mode)}</span>
                <span>{run.created_at}</span>
              </div>
            </button>
          ))
        ) : (
          <div className="empty-inline">暂无运行记录。</div>
        )}
      </div>
    </section>
  );
}
