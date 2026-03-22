import { useEffect, useState } from "react";
import { createReviewRun, fetchCapabilities, fetchReviewPresets } from "../api/client";
import { RunListPanel, RunResultPanel } from "../components/RunPresentation";
import { useReviewDiagnostics } from "../hooks/useReviewDiagnostics";
import { useRunWorkspace } from "../hooks/useRunWorkspace";
import type { Capabilities, ReviewPreset } from "../types";

type ReviewFormState = {
  preset_key: string;
  intent: string;
  constraints: string;
  revision_engine: string;
  format_profile: string;
  diagnostics: boolean;
  diagnostics_only: boolean;
  allow_python_docx_fallback: boolean;
  strip_existing_comments: boolean;
  prefer_replace: boolean;
  allow_expansion: boolean;
  expansion_level: string;
  allow_web_search: boolean;
  focus_only: boolean;
  memory_scope: string;
  inline_context: string;
  chunk_context: number;
  context_max_chars: number;
  extract_docx_images: boolean;
  extract_tables: boolean;
  table_image_understanding: boolean;
  table_image_prompt: string;
  parallel_review: boolean;
  parallel_workers: number;
  chunk_size: number;
  parallel_min_paragraphs: number;
  comment_author: string;
  model_override: string;
};

const defaultFormState: ReviewFormState = {
  preset_key: "general_academic",
  intent: "",
  constraints: "",
  revision_engine: "auto",
  format_profile: "none",
  diagnostics: true,
  diagnostics_only: false,
  allow_python_docx_fallback: false,
  strip_existing_comments: false,
  prefer_replace: false,
  allow_expansion: false,
  expansion_level: "none",
  allow_web_search: false,
  focus_only: false,
  memory_scope: "document",
  inline_context: "boundary",
  chunk_context: 2,
  context_max_chars: 1200,
  extract_docx_images: false,
  extract_tables: false,
  table_image_understanding: false,
  table_image_prompt: "描述分析这张图",
  parallel_review: true,
  parallel_workers: 4,
  chunk_size: 40,
  parallel_min_paragraphs: 80,
  comment_author: "呆塔大师兄",
  model_override: "",
};

export default function SmartReviewPage() {
  const [file, setFile] = useState<File | null>(null);
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [presets, setPresets] = useState<ReviewPreset[]>([]);
  const [form, setForm] = useState<ReviewFormState>(defaultFormState);
  const [submitError, setSubmitError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { currentRun, recentRuns, selectRun, trackRun } = useRunWorkspace("review");
  const { diagnostics, diagnosticsError } = useReviewDiagnostics(currentRun);

  useEffect(() => {
    fetchCapabilities().then(setCapabilities).catch(() => undefined);
    fetchReviewPresets()
      .then((items) => {
        setPresets(items);
        if (items.some((item) => item.key === defaultFormState.preset_key)) {
          return;
        }
        if (items[0]) {
          setForm((previous) => ({ ...previous, preset_key: items[0].key }));
        }
      })
      .catch(() => undefined);
  }, []);

  const selectedPreset = presets.find((item) => item.key === form.preset_key) || null;

  function updateForm<K extends keyof ReviewFormState>(key: K, value: ReviewFormState[K]) {
    setForm((previous) => ({ ...previous, [key]: value }));
  }

  async function handleSubmit() {
    if (!file) {
      setSubmitError("请先上传 Word 文稿。");
      return;
    }
    if (!form.intent.trim() && !form.diagnostics_only) {
      setSubmitError("请填写审阅目标，或切换为仅学术诊断。");
      return;
    }

    setSubmitting(true);
    setSubmitError("");
    try {
      const payload = new FormData();
      payload.append("file", file);
      payload.append("intent", form.intent);
      payload.append("constraints_json", JSON.stringify(form.constraints.split("\n").map((item) => item.trim()).filter(Boolean)));
      payload.append("preset_key", form.preset_key);
      payload.append("revision_engine", form.revision_engine);
      payload.append("format_profile", form.format_profile);
      payload.append("diagnostics", String(form.diagnostics));
      payload.append("diagnostics_only", String(form.diagnostics_only));
      payload.append("allow_python_docx_fallback", String(form.allow_python_docx_fallback));
      payload.append("strip_existing_comments", String(form.strip_existing_comments));
      payload.append("prefer_replace", String(form.prefer_replace));
      payload.append("allow_expansion", String(form.allow_expansion));
      payload.append("expansion_level", form.expansion_level);
      payload.append("allow_web_search", String(form.allow_web_search));
      payload.append("focus_only", String(form.focus_only));
      payload.append("memory_scope", form.memory_scope);
      payload.append("inline_context", form.inline_context);
      payload.append("chunk_context", String(form.chunk_context));
      payload.append("context_max_chars", String(form.context_max_chars));
      payload.append("extract_docx_images", String(form.extract_docx_images));
      payload.append("extract_tables", String(form.extract_tables));
      payload.append("table_image_understanding", String(form.table_image_understanding));
      payload.append("table_image_prompt", form.table_image_prompt);
      payload.append("parallel_review", String(form.parallel_review));
      payload.append("parallel_workers", String(form.parallel_workers));
      payload.append("chunk_size", String(form.chunk_size));
      payload.append("parallel_min_paragraphs", String(form.parallel_min_paragraphs));
      payload.append("comment_author", form.comment_author);
      payload.append("model_override", form.model_override);
      const run = await createReviewRun(payload);
      trackRun(run);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "提交失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page-grid">
      <section className="hero-panel">
        <div>
          <span className="hero-eyebrow">Academic Review Workspace</span>
          <h1>智能校稿</h1>
          <p>
            这里收敛了学术预设、审阅目标、执行策略和运行结果。默认输出修订版文档、运行日志，并可同步生成统一的学术诊断卡片。
          </p>
        </div>
        <div className="hero-stats">
          <div className="stat-card">
            <span>Win32 Word</span>
            <strong>{capabilities?.features.win32 ? "Ready" : "Unavailable"}</strong>
          </div>
          <div className="stat-card">
            <span>python-docx</span>
            <strong>{capabilities?.features.python_docx ? "Ready" : "Unavailable"}</strong>
          </div>
          <div className="stat-card">
            <span>联网检索</span>
            <strong>{capabilities?.features.tavily_key ? "Enabled" : "Missing Key"}</strong>
          </div>
        </div>
      </section>

      <section className="workspace-grid">
        <div className="form-stack">
          <section className="stack-card">
            <div className="section-bar">
              <div>
                <span className="section-eyebrow">Step 1</span>
                <h3>文稿与预设</h3>
              </div>
            </div>
            <label className="upload-dropzone">
              <input accept=".docx,.docm,.dotx,.dotm" className="visually-hidden" onChange={(event) => setFile(event.target.files?.[0] ?? null)} type="file" />
              <span>{file ? file.name : "拖放或点击上传 Word 文稿"}</span>
              <small>支持 .docx / .docm / .dotx / .dotm</small>
            </label>
            <div className="field-grid two-col">
              <label className="field">
                <span>学术预设</span>
                <select onChange={(event) => updateForm("preset_key", event.target.value)} value={form.preset_key}>
                  {presets.map((preset) => (
                    <option key={preset.key} value={preset.key}>
                      {preset.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>审阅引擎</span>
                <select onChange={(event) => updateForm("revision_engine", event.target.value)} value={form.revision_engine}>
                  {capabilities?.review.engines.map((engine) => (
                    <option disabled={!engine.available} key={engine.key} value={engine.key}>
                      {engine.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {selectedPreset ? (
              <article className="preset-highlight">
                <strong>{selectedPreset.label}</strong>
                <p>{selectedPreset.description}</p>
                <div className="tag-row">
                  {selectedPreset.diagnostics_dimensions.slice(0, 6).map((item) => (
                    <span className="tag" key={item}>
                      {item}
                    </span>
                  ))}
                </div>
              </article>
            ) : null}
            <div className="toggle-grid">
              <label className="toggle-row">
                <input checked={form.diagnostics} onChange={(event) => updateForm("diagnostics", event.target.checked)} type="checkbox" />
                <span>生成学术诊断卡片与 JSON</span>
              </label>
              <label className="toggle-row">
                <input
                  checked={form.diagnostics_only}
                  disabled={!form.diagnostics}
                  onChange={(event) => updateForm("diagnostics_only", event.target.checked)}
                  type="checkbox"
                />
                <span>仅做学术诊断，不生成修订文档</span>
              </label>
            </div>
          </section>

          <section className="stack-card">
            <div className="section-bar">
              <div>
                <span className="section-eyebrow">Step 2</span>
                <h3>审阅目标</h3>
              </div>
            </div>
            <label className="field">
              <span>审阅目标 / 需求</span>
              <textarea onChange={(event) => updateForm("intent", event.target.value)} rows={7} value={form.intent} />
            </label>
            <label className="field">
              <span>附加约束</span>
              <textarea onChange={(event) => updateForm("constraints", event.target.value)} placeholder="每行一条" rows={5} value={form.constraints} />
            </label>
            {selectedPreset?.default_constraints.length ? (
              <details className="detail-box">
                <summary>查看预设默认约束</summary>
                <ul className="plain-list">
                  {selectedPreset.default_constraints.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </details>
            ) : null}
          </section>

          <section className="stack-card">
            <div className="section-bar">
              <div>
                <span className="section-eyebrow">Step 3</span>
                <h3>执行策略</h3>
              </div>
            </div>
            <div className="field-grid three-col">
              <label className="field">
                <span>排版风格</span>
                <select onChange={(event) => updateForm("format_profile", event.target.value)} value={form.format_profile}>
                  {capabilities?.review.format_profiles.map((profile) => (
                    <option disabled={!profile.available} key={profile.key} value={profile.key}>
                      {profile.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>记忆模式</span>
                <select onChange={(event) => updateForm("memory_scope", event.target.value)} value={form.memory_scope}>
                  {capabilities?.review.memory_scopes.map((scope) => (
                    <option key={scope.key} value={scope.key}>
                      {scope.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>扩充强度</span>
                <select onChange={(event) => updateForm("expansion_level", event.target.value)} value={form.expansion_level}>
                  {capabilities?.review.expansion_levels.map((level) => (
                    <option key={level.key} value={level.key}>
                      {level.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="toggle-grid">
              <label className="toggle-row"><input checked={form.allow_python_docx_fallback} onChange={(event) => updateForm("allow_python_docx_fallback", event.target.checked)} type="checkbox" /><span>允许 python-docx 兜底</span></label>
              <label className="toggle-row"><input checked={form.strip_existing_comments} onChange={(event) => updateForm("strip_existing_comments", event.target.checked)} type="checkbox" /><span>清理原文批注</span></label>
              <label className="toggle-row"><input checked={form.prefer_replace} onChange={(event) => updateForm("prefer_replace", event.target.checked)} type="checkbox" /><span>更积极直接改文</span></label>
              <label className="toggle-row"><input checked={form.allow_expansion} onChange={(event) => updateForm("allow_expansion", event.target.checked)} type="checkbox" /><span>允许扩充完善</span></label>
              <label className="toggle-row"><input checked={form.allow_web_search} onChange={(event) => updateForm("allow_web_search", event.target.checked)} type="checkbox" /><span>允许联网检索</span></label>
              <label className="toggle-row"><input checked={form.focus_only} onChange={(event) => updateForm("focus_only", event.target.checked)} type="checkbox" /><span>仅审阅聚焦位置</span></label>
              <label className="toggle-row"><input checked={form.extract_docx_images} onChange={(event) => updateForm("extract_docx_images", event.target.checked)} type="checkbox" /><span>提取文档图片</span></label>
              <label className="toggle-row"><input checked={form.extract_tables} onChange={(event) => updateForm("extract_tables", event.target.checked)} type="checkbox" /><span>提取表格元素</span></label>
            </div>
            <details className="detail-box">
              <summary>高级参数</summary>
              <div className="field-grid three-col">
                <label className="field">
                  <span>上下文模式</span>
                  <select onChange={(event) => updateForm("inline_context", event.target.value)} value={form.inline_context}>
                    {capabilities?.review.inline_context_modes.map((mode) => (
                      <option key={mode.key} value={mode.key}>
                        {mode.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>模型覆盖</span>
                  <input onChange={(event) => updateForm("model_override", event.target.value)} value={form.model_override} />
                </label>
                <label className="field">
                  <span>批注作者</span>
                  <input onChange={(event) => updateForm("comment_author", event.target.value)} value={form.comment_author} />
                </label>
              </div>
              <div className="field-grid four-col">
                <label className="field"><span>跨段上下文</span><input min={0} onChange={(event) => updateForm("chunk_context", Number(event.target.value))} type="number" value={form.chunk_context} /></label>
                <label className="field"><span>上下文截断</span><input min={0} onChange={(event) => updateForm("context_max_chars", Number(event.target.value))} type="number" value={form.context_max_chars} /></label>
                <label className="field"><span>并行线程数</span><input min={1} onChange={(event) => updateForm("parallel_workers", Number(event.target.value))} type="number" value={form.parallel_workers} /></label>
                <label className="field"><span>每段最大段落</span><input min={10} onChange={(event) => updateForm("chunk_size", Number(event.target.value))} type="number" value={form.chunk_size} /></label>
              </div>
              <div className="field-grid three-col">
                <label className="toggle-row"><input checked={form.parallel_review} onChange={(event) => updateForm("parallel_review", event.target.checked)} type="checkbox" /><span>并行分段审阅</span></label>
                <label className="toggle-row"><input checked={form.table_image_understanding} onChange={(event) => updateForm("table_image_understanding", event.target.checked)} type="checkbox" /><span>表格图片理解</span></label>
                <label className="field"><span>图片提示词</span><input onChange={(event) => updateForm("table_image_prompt", event.target.value)} value={form.table_image_prompt} /></label>
              </div>
              <label className="field">
                <span>并行启用阈值</span>
                <input min={1} onChange={(event) => updateForm("parallel_min_paragraphs", Number(event.target.value))} type="number" value={form.parallel_min_paragraphs} />
              </label>
            </details>
            {submitError ? <div className="error-banner">{submitError}</div> : null}
            {diagnosticsError ? <div className="error-banner">{diagnosticsError}</div> : null}
            <button className="primary-button" disabled={submitting} onClick={() => void handleSubmit()} type="button">
              {submitting ? "提交中..." : form.diagnostics_only ? "开始学术诊断" : "开始审阅"}
            </button>
          </section>
        </div>

        <div className="side-stack">
          <RunResultPanel diagnostics={diagnostics} emptyText="提交后会在这里显示当前运行。" run={currentRun} title="当前运行" />
          <RunListPanel currentRunId={currentRun?.id} onSelect={selectRun} runs={recentRuns} title="最近校稿运行" />
        </div>
      </section>
    </div>
  );
}
