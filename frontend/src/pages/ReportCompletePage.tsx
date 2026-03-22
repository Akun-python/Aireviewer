import { useState } from "react";
import { createReportCompleteRun } from "../api/client";
import { RunListPanel, RunResultPanel } from "../components/RunPresentation";
import { useRunWorkspace } from "../hooks/useRunWorkspace";

export default function ReportCompletePage() {
  const [file, setFile] = useState<File | null>(null);
  const [topic, setTopic] = useState("");
  const [allowWebSearch, setAllowWebSearch] = useState(true);
  const [maxResults, setMaxResults] = useState(5);
  const [sectionTimeout, setSectionTimeout] = useState(300);
  const [fillEmptyHeadings, setFillEmptyHeadings] = useState(true);
  const [formatProfile, setFormatProfile] = useState("thesis_standard");
  const [tocPosition, setTocPosition] = useState("before_outline");
  const [modelOverride, setModelOverride] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const { currentRun, recentRuns, selectRun, trackRun } = useRunWorkspace("report-complete");

  async function handleSubmit() {
    if (!file) {
      setSubmitError("请先上传待完善的报告。");
      return;
    }
    setSubmitting(true);
    setSubmitError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("topic", topic);
      formData.append("allow_web_search", String(allowWebSearch));
      formData.append("max_results_per_query", String(maxResults));
      formData.append("section_timeout", String(sectionTimeout));
      formData.append("fill_empty_headings", String(fillEmptyHeadings));
      formData.append("format_profile", formatProfile);
      formData.append("toc_position", tocPosition);
      formData.append("model_override", modelOverride);
      const run = await createReportCompleteRun(formData);
      trackRun(run);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "提交失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page-grid">
      <section className="hero-panel compact-hero">
        <div>
          <span className="hero-eyebrow">Completion Workflow</span>
          <h1>报告完善</h1>
          <p>上传已有 Word 报告，按目录或空章节补全内容，仍统一归档到运行中心。</p>
        </div>
      </section>
      <section className="workspace-grid">
        <div className="form-stack">
          <section className="stack-card">
            <div className="section-bar"><h3>完善参数</h3></div>
            <label className="upload-dropzone">
              <input accept=".docx,.docm,.dotx,.dotm" className="visually-hidden" onChange={(event) => setFile(event.target.files?.[0] ?? null)} type="file" />
              <span>{file ? file.name : "上传已有报告"}</span>
              <small>支持 .docx / .docm / .dotx / .dotm</small>
            </label>
            <div className="field-grid two-col">
              <label className="field"><span>主题（可选）</span><input onChange={(event) => setTopic(event.target.value)} value={topic} /></label>
              <label className="field"><span>模型覆盖</span><input onChange={(event) => setModelOverride(event.target.value)} value={modelOverride} /></label>
            </div>
            <div className="field-grid four-col">
              <label className="field"><span>检索返回数</span><input min={1} onChange={(event) => setMaxResults(Number(event.target.value))} type="number" value={maxResults} /></label>
              <label className="field"><span>章节超时</span><input min={60} onChange={(event) => setSectionTimeout(Number(event.target.value))} type="number" value={sectionTimeout} /></label>
              <label className="field"><span>排版风格</span><select onChange={(event) => setFormatProfile(event.target.value)} value={formatProfile}><option value="thesis_standard">论文标准格式</option><option value="a4_strict">A4 规范格式</option><option value="none">不排版</option></select></label>
              <label className="field"><span>目录位置</span><select onChange={(event) => setTocPosition(event.target.value)} value={tocPosition}><option value="before_outline">大纲前</option><option value="after_title">标题后</option><option value="none">不生成目录</option></select></label>
            </div>
            <div className="toggle-grid">
              <label className="toggle-row"><input checked={allowWebSearch} onChange={(event) => setAllowWebSearch(event.target.checked)} type="checkbox" /><span>启用联网检索</span></label>
              <label className="toggle-row"><input checked={fillEmptyHeadings} onChange={(event) => setFillEmptyHeadings(event.target.checked)} type="checkbox" /><span>补全空标题章节</span></label>
            </div>
            {submitError ? <div className="error-banner">{submitError}</div> : null}
            <button className="primary-button" disabled={submitting} onClick={() => void handleSubmit()} type="button">
              {submitting ? "提交中..." : "开始完善报告"}
            </button>
          </section>
        </div>
        <div className="side-stack">
          <RunResultPanel diagnostics={null} emptyText="完善结果会显示在这里。" run={currentRun} title="当前完善任务" />
          <RunListPanel currentRunId={currentRun?.id} onSelect={selectRun} runs={recentRuns} title="最近完善运行" />
        </div>
      </section>
    </div>
  );
}
