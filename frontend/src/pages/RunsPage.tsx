import { useState } from "react";
import { RunResultPanel, formatMode, formatStatus } from "../components/RunPresentation";
import { useReviewDiagnostics } from "../hooks/useReviewDiagnostics";
import { useRunWorkspace } from "../hooks/useRunWorkspace";

const modeOptions = [
  { key: "", label: "全部任务" },
  { key: "review", label: "智能校稿" },
  { key: "report", label: "课题报告" },
  { key: "report-complete", label: "报告完善" },
  { key: "report-integrate", label: "多章整合" },
];

export default function RunsPage() {
  const [modeFilter, setModeFilter] = useState("");
  const { currentRun, recentRuns, selectRun } = useRunWorkspace(modeFilter || undefined);
  const { diagnostics } = useReviewDiagnostics(currentRun);

  return (
    <div className="page-grid">
      <section className="hero-panel compact-hero">
        <div>
          <span className="hero-eyebrow">Run Center</span>
          <h1>运行中心</h1>
          <p>这里集中查看所有运行历史、产物、失败原因和 review 诊断卡片。</p>
        </div>
      </section>
      <section className="workspace-grid">
        <div className="form-stack">
          <section className="stack-card">
            <div className="section-bar">
              <h3>任务列表</h3>
              <select className="inline-select" onChange={(event) => setModeFilter(event.target.value)} value={modeFilter}>
                {modeOptions.map((option) => (
                  <option key={option.key} value={option.key}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="run-list">
              {recentRuns.map((run) => (
                <button className={`run-list-item ${currentRun?.id === run.id ? "run-list-item-active" : ""}`} key={run.id} onClick={() => selectRun(run)} type="button">
                  <div className="run-list-top">
                    <strong>{run.title}</strong>
                    <span className={`status-pill status-${run.status}`}>{formatStatus(run.status)}</span>
                  </div>
                  <div className="run-list-meta">
                    <span>{formatMode(run.mode)}</span>
                    <span>{run.created_at}</span>
                  </div>
                </button>
              ))}
            </div>
          </section>
        </div>
        <div className="side-stack">
          <RunResultPanel diagnostics={diagnostics} emptyText="选择左侧任务查看详情。" run={currentRun} title="任务详情" />
          {currentRun ? (
            <section className="stack-card">
              <div className="section-bar compact">
                <h3>参数快照</h3>
              </div>
              <pre>{JSON.stringify(currentRun.params, null, 2)}</pre>
            </section>
          ) : null}
        </div>
      </section>
    </div>
  );
}
