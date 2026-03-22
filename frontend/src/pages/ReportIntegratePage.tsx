import { useState } from "react";
import { createReportIntegrateRun } from "../api/client";
import { RunListPanel, RunResultPanel } from "../components/RunPresentation";
import { useRunWorkspace } from "../hooks/useRunWorkspace";

export default function ReportIntegratePage() {
  const [files, setFiles] = useState<File[]>([]);
  const [topic, setTopic] = useState("");
  const [tocPosition, setTocPosition] = useState("after_title");
  const [formatProfile, setFormatProfile] = useState("thesis_standard");
  const [allowLlm, setAllowLlm] = useState(true);
  const [autoCaptions, setAutoCaptions] = useState(true);
  const [fixedOrderText, setFixedOrderText] = useState("");
  const [modelOverride, setModelOverride] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const { currentRun, recentRuns, selectRun, trackRun } = useRunWorkspace("report-integrate");

  async function handleSubmit() {
    if (!files.length) {
      setSubmitError("请至少上传一个章节文件。");
      return;
    }
    setSubmitting(true);
    setSubmitError("");
    try {
      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));
      formData.append("topic", topic);
      formData.append("toc_position", tocPosition);
      formData.append("format_profile", formatProfile);
      formData.append("allow_llm", String(allowLlm));
      formData.append("auto_captions", String(autoCaptions));
      formData.append("fixed_order_text", fixedOrderText);
      formData.append("model_override", modelOverride);
      const run = await createReportIntegrateRun(formData);
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
          <span className="hero-eyebrow">Integration Workflow</span>
          <h1>多章整合</h1>
          <p>上传多个章节 Word 文件，统一生成引言、过渡段和排版结果。</p>
        </div>
      </section>
      <section className="workspace-grid">
        <div className="form-stack">
          <section className="stack-card">
            <div className="section-bar"><h3>整合参数</h3></div>
            <label className="upload-dropzone">
              <input accept=".docx,.docm,.dotx,.dotm" className="visually-hidden" multiple onChange={(event) => setFiles(Array.from(event.target.files || []))} type="file" />
              <span>{files.length ? `已选择 ${files.length} 个章节` : "上传多个章节文稿"}</span>
              <small>文件名可作为固定顺序参考</small>
            </label>
            <div className="file-list">
              {files.map((file) => (
                <div className="file-chip" key={file.name}>{file.name}</div>
              ))}
            </div>
            <div className="field-grid two-col">
              <label className="field"><span>整合主题</span><input onChange={(event) => setTopic(event.target.value)} value={topic} /></label>
              <label className="field"><span>模型覆盖</span><input onChange={(event) => setModelOverride(event.target.value)} value={modelOverride} /></label>
            </div>
            <div className="field-grid three-col">
              <label className="field"><span>目录位置</span><select onChange={(event) => setTocPosition(event.target.value)} value={tocPosition}><option value="after_title">标题后</option><option value="before_outline">大纲前</option><option value="none">不生成目录</option></select></label>
              <label className="field"><span>排版风格</span><select onChange={(event) => setFormatProfile(event.target.value)} value={formatProfile}><option value="thesis_standard">论文标准格式</option><option value="a4_strict">A4 规范格式</option><option value="none">不排版</option></select></label>
              <label className="field"><span>固定顺序</span><textarea onChange={(event) => setFixedOrderText(event.target.value)} placeholder="每行一个文件名或章节名" rows={4} value={fixedOrderText} /></label>
            </div>
            <div className="toggle-grid">
              <label className="toggle-row"><input checked={allowLlm} onChange={(event) => setAllowLlm(event.target.checked)} type="checkbox" /><span>启用 LLM 总结与重排</span></label>
              <label className="toggle-row"><input checked={autoCaptions} onChange={(event) => setAutoCaptions(event.target.checked)} type="checkbox" /><span>自动补图表题注</span></label>
            </div>
            {submitError ? <div className="error-banner">{submitError}</div> : null}
            <button className="primary-button" disabled={submitting} onClick={() => void handleSubmit()} type="button">
              {submitting ? "提交中..." : "开始整合章节"}
            </button>
          </section>
        </div>
        <div className="side-stack">
          <RunResultPanel diagnostics={null} emptyText="整合结果会显示在这里。" run={currentRun} title="当前整合任务" />
          <RunListPanel currentRunId={currentRun?.id} onSelect={selectRun} runs={recentRuns} title="最近整合运行" />
        </div>
      </section>
    </div>
  );
}
