import { useState } from "react";
import { createReportRun } from "../api/client";
import { RunListPanel, RunResultPanel } from "../components/RunPresentation";
import { useRunWorkspace } from "../hooks/useRunWorkspace";

const DEFAULT_FRAMEWORK = `1. [选题说明] 选题所研究的具体问题、研究视角和核心概念。
2. [选题依据] 国内外相关研究的学术史梳理及研究进展。
3. [研究内容] 主要目标、重点难点、整体框架、研究计划及可行性。
4. [创新之处] 学术观点与研究方法上的特色。
5. [预期成果] 成果形式、学术价值与社会效益。
6. [研究基础] 相关研究积累与前期成果。
7. [参考文献] 主要中外参考文献。`;

export default function ReportPage() {
  const [topic, setTopic] = useState("");
  const [frameworkText, setFrameworkText] = useState(DEFAULT_FRAMEWORK);
  const [totalChars, setTotalChars] = useState(10000);
  const [allowWebSearch, setAllowWebSearch] = useState(true);
  const [maxResults, setMaxResults] = useState(5);
  const [sectionTimeout, setSectionTimeout] = useState(300);
  const [maxRetries, setMaxRetries] = useState(2);
  const [sectionWorkers, setSectionWorkers] = useState(3);
  const [reportDocxEngine, setReportDocxEngine] = useState("auto");
  const [formatProfile, setFormatProfile] = useState("thesis_standard");
  const [tocPosition, setTocPosition] = useState("before_outline");
  const [modelOverride, setModelOverride] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const { currentRun, recentRuns, selectRun, trackRun } = useRunWorkspace("report");

  async function handleSubmit() {
    if (!topic.trim()) {
      setSubmitError("请先填写选题。");
      return;
    }
    setSubmitting(true);
    setSubmitError("");
    try {
      const formData = new FormData();
      formData.append("topic", topic);
      formData.append("framework_text", frameworkText);
      formData.append("total_chars", String(totalChars));
      formData.append("allow_web_search", String(allowWebSearch));
      formData.append("max_results_per_query", String(maxResults));
      formData.append("section_timeout", String(sectionTimeout));
      formData.append("max_section_retries", String(maxRetries));
      formData.append("section_workers", String(sectionWorkers));
      formData.append("report_docx_engine", reportDocxEngine);
      formData.append("format_profile", formatProfile);
      formData.append("toc_position", tocPosition);
      formData.append("model_override", modelOverride);
      const run = await createReportRun(formData);
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
          <span className="hero-eyebrow">Report Workflow</span>
          <h1>课题报告生成</h1>
          <p>以统一 run center 为中心，直接从 React 发起生成式报告任务，产物仍由后端统一归档。</p>
        </div>
      </section>
      <section className="workspace-grid">
        <div className="form-stack">
          <section className="stack-card">
            <div className="section-bar"><h3>报告参数</h3></div>
            <label className="field">
              <span>选题</span>
              <input onChange={(event) => setTopic(event.target.value)} value={topic} />
            </label>
            <label className="field">
              <span>报告框架</span>
              <textarea onChange={(event) => setFrameworkText(event.target.value)} rows={10} value={frameworkText} />
            </label>
            <div className="field-grid four-col">
              <label className="field"><span>目标字数</span><input min={3000} onChange={(event) => setTotalChars(Number(event.target.value))} type="number" value={totalChars} /></label>
              <label className="field"><span>检索返回数</span><input min={1} onChange={(event) => setMaxResults(Number(event.target.value))} type="number" value={maxResults} /></label>
              <label className="field"><span>章节超时</span><input min={60} onChange={(event) => setSectionTimeout(Number(event.target.value))} type="number" value={sectionTimeout} /></label>
              <label className="field"><span>重试次数</span><input min={0} onChange={(event) => setMaxRetries(Number(event.target.value))} type="number" value={maxRetries} /></label>
            </div>
            <div className="field-grid four-col">
              <label className="field"><span>并行章节数</span><input min={1} onChange={(event) => setSectionWorkers(Number(event.target.value))} type="number" value={sectionWorkers} /></label>
              <label className="field"><span>Word 引擎</span><select onChange={(event) => setReportDocxEngine(event.target.value)} value={reportDocxEngine}><option value="auto">自动</option><option value="win32com">Win32 Word</option><option value="python-docx">python-docx</option></select></label>
              <label className="field"><span>排版风格</span><select onChange={(event) => setFormatProfile(event.target.value)} value={formatProfile}><option value="thesis_standard">论文标准格式</option><option value="a4_strict">A4 规范格式</option><option value="none">不排版</option></select></label>
              <label className="field"><span>目录位置</span><select onChange={(event) => setTocPosition(event.target.value)} value={tocPosition}><option value="before_outline">大纲前</option><option value="after_title">标题后</option><option value="none">不生成目录</option></select></label>
            </div>
            <div className="toggle-grid">
              <label className="toggle-row"><input checked={allowWebSearch} onChange={(event) => setAllowWebSearch(event.target.checked)} type="checkbox" /><span>启用联网检索</span></label>
              <label className="field"><span>模型覆盖</span><input onChange={(event) => setModelOverride(event.target.value)} value={modelOverride} /></label>
            </div>
            {submitError ? <div className="error-banner">{submitError}</div> : null}
            <button className="primary-button" disabled={submitting} onClick={() => void handleSubmit()} type="button">
              {submitting ? "提交中..." : "开始生成报告"}
            </button>
          </section>
        </div>
        <div className="side-stack">
          <RunResultPanel diagnostics={null} emptyText="报告运行结果会显示在这里。" run={currentRun} title="当前报告任务" />
          <RunListPanel currentRunId={currentRun?.id} onSelect={selectRun} runs={recentRuns} title="最近报告运行" />
        </div>
      </section>
    </div>
  );
}
