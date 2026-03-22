import { useEffect, useRef, useState } from "react";
import { artifactUrl, createReviewRun, createRunEventSource, fetchCapabilities, fetchRun, fetchRuns } from "../api/client";
import type { Capabilities, ReviewRun, RunEvent } from "../types";

type StepId = 1 | 2 | 3 | 4;

const stepLabels: Array<{ id: StepId; title: string; subtitle: string }> = [
  { id: 1, title: "上传文档", subtitle: "导入 Word 文件并确认引擎能力" },
  { id: 2, title: "审阅意图", subtitle: "描述角色、目标和附加约束" },
  { id: 3, title: "执行策略", subtitle: "选择引擎、记忆和高级选项" },
  { id: 4, title: "运行结果", subtitle: "实时查看日志、产物和状态" },
];

type FormState = {
  expert_view: string;
  intent: string;
  constraints: string;
  revision_engine: string;
  format_profile: string;
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

const defaultFormState: FormState = {
  expert_view: "文档审阅员",
  intent: "",
  constraints: "",
  revision_engine: "auto",
  format_profile: "none",
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

function formatStatus(status: string): string {
  return (
    {
      created: "已创建",
      queued: "排队中",
      running: "运行中",
      completed: "已完成",
      failed: "失败",
    }[status] || status
  );
}

function uniqueEvents(primary: RunEvent[], extra: RunEvent[]): RunEvent[] {
  const merged: RunEvent[] = [];
  for (const item of [...primary, ...extra]) {
    if (!merged.some((existing) => existing.id === item.id)) {
      merged.push(item);
    }
  }
  return merged.sort((left, right) => left.id - right.id);
}

export default function SmartReviewPage() {
  const [activeStep, setActiveStep] = useState<StepId>(1);
  const [file, setFile] = useState<File | null>(null);
  const [form, setForm] = useState<FormState>(defaultFormState);
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [capabilityError, setCapabilityError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [currentRun, setCurrentRun] = useState<ReviewRun | null>(null);
  const [recentRuns, setRecentRuns] = useState<ReviewRun[]>([]);
  const [liveEvents, setLiveEvents] = useState<RunEvent[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchCapabilities()
      .then((payload) => {
        if (cancelled) {
          return;
        }
        setCapabilities(payload);
      })
      .catch((error: Error) => {
        if (!cancelled) {
          setCapabilityError(error.message);
        }
      });
    fetchRuns()
      .then((payload) => {
        if (!cancelled) {
          setRecentRuns(payload);
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => () => eventSourceRef.current?.close(), []);

  useEffect(() => {
    if (!currentRun || !["created", "queued", "running"].includes(currentRun.status)) {
      return;
    }
    const timer = window.setInterval(() => {
      fetchRun(currentRun.id).then(setCurrentRun).catch(() => undefined);
      fetchRuns().then(setRecentRuns).catch(() => undefined);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [currentRun]);

  function updateForm<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function openEventStream(runId: string, after: number) {
    eventSourceRef.current?.close();
    const source = createRunEventSource(runId, after);
    source.onmessage = (event) => {
      const payload = JSON.parse(event.data) as RunEvent;
      setLiveEvents((prev) => uniqueEvents(prev, [payload]));
    };
    source.addEventListener("run.completed", () => {
      fetchRun(runId).then(setCurrentRun).catch(() => undefined);
      fetchRuns().then(setRecentRuns).catch(() => undefined);
      source.close();
    });
    source.addEventListener("run.failed", () => {
      fetchRun(runId).then(setCurrentRun).catch(() => undefined);
      fetchRuns().then(setRecentRuns).catch(() => undefined);
      source.close();
    });
    source.onerror = () => {
      source.close();
    };
    eventSourceRef.current = source;
  }

  async function handleSubmit() {
    if (!file) {
      setSubmitError("请先选择 Word 文件。");
      setActiveStep(1);
      return;
    }
    if (!form.intent.trim()) {
      setSubmitError("请填写审阅目标/需求。");
      setActiveStep(2);
      return;
    }
    setSubmitting(true);
    setSubmitError("");
    setLiveEvents([]);
    setActiveStep(4);
    try {
      const data = new FormData();
      data.append("file", file);
      data.append("intent", form.intent);
      data.append("expert_view", form.expert_view);
      data.append(
        "constraints_json",
        JSON.stringify(
          form.constraints
            .split("\n")
            .map((item) => item.trim())
            .filter(Boolean),
        ),
      );
      data.append("revision_engine", form.revision_engine);
      data.append("format_profile", form.format_profile);
      data.append("allow_python_docx_fallback", String(form.allow_python_docx_fallback));
      data.append("strip_existing_comments", String(form.strip_existing_comments));
      data.append("prefer_replace", String(form.prefer_replace));
      data.append("allow_expansion", String(form.allow_expansion));
      data.append("expansion_level", form.expansion_level);
      data.append("allow_web_search", String(form.allow_web_search));
      data.append("focus_only", String(form.focus_only));
      data.append("memory_scope", form.memory_scope);
      data.append("inline_context", form.inline_context);
      data.append("chunk_context", String(form.chunk_context));
      data.append("context_max_chars", String(form.context_max_chars));
      data.append("extract_docx_images", String(form.extract_docx_images));
      data.append("extract_tables", String(form.extract_tables));
      data.append("table_image_understanding", String(form.table_image_understanding));
      data.append("table_image_prompt", form.table_image_prompt);
      data.append("parallel_review", String(form.parallel_review));
      data.append("parallel_workers", String(form.parallel_workers));
      data.append("chunk_size", String(form.chunk_size));
      data.append("parallel_min_paragraphs", String(form.parallel_min_paragraphs));
      data.append("comment_author", form.comment_author);
      data.append("model_override", form.model_override);

      const run = await createReviewRun(data);
      setCurrentRun(run);
      setRecentRuns((prev) => [run, ...prev.filter((item) => item.id !== run.id)]);
      openEventStream(run.id, run.event_count);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "提交失败");
    } finally {
      setSubmitting(false);
    }
  }

  const logEvents = uniqueEvents(currentRun?.events || [], liveEvents);
  const logLines = logEvents
    .filter((item) => item.type === "run.log" || item.type.startsWith("run."))
    .map((item) => `[${item.ts}] ${item.message || item.type}`);

  return (
    <div className="screen-grid">
      <section className="hero-panel">
        <div className="hero-copy">
          <div className="eyebrow">Workflow UI</div>
          <h1>Word审阅助手</h1>
          <p>把原来拥挤的一页式配置拆成分步流程。上传、定目标、选策略、看结果，主路径更清晰，保留 Streamlit 作为兼容入口。</p>
        </div>
        <div className="hero-meta">
          <div className="metric-card">
            <span>Win32 Word</span>
            <strong>{capabilities?.features.win32 ? "Ready" : "Unavailable"}</strong>
          </div>
          <div className="metric-card">
            <span>python-docx</span>
            <strong>{capabilities?.features.python_docx ? "Ready" : "Unavailable"}</strong>
          </div>
          <div className="metric-card">
            <span>检索能力</span>
            <strong>{capabilities?.features.tavily_key ? "Enabled" : "Missing Key"}</strong>
          </div>
        </div>
      </section>

      <section className="stepper-panel">
        {stepLabels.map((step) => (
          <button className={`step-chip ${activeStep === step.id ? "step-active" : ""}`} key={step.id} onClick={() => setActiveStep(step.id)} type="button">
            <span className="step-index">0{step.id}</span>
            <span className="step-text">
              <strong>{step.title}</strong>
              <small>{step.subtitle}</small>
            </span>
          </button>
        ))}
      </section>

      <section className="main-panel">
        {activeStep === 1 ? (
          <div className="panel-body">
            <div className="panel-head">
              <h2>上传文档</h2>
              <p>先确定文件和本机可用能力，再进入审阅配置。</p>
            </div>
            <label className="upload-dropzone">
              <input accept=".docx,.docm,.dotx,.dotm" className="visually-hidden" onChange={(event) => setFile(event.target.files?.[0] ?? null)} type="file" />
              <span>拖放或点击选择 Word 文件</span>
              <small>支持 .docx / .docm / .dotx / .dotm</small>
            </label>
            {file ? (
              <div className="file-card">
                <strong>{file.name}</strong>
                <span>{(file.size / 1024 / 1024).toFixed(2)} MB</span>
              </div>
            ) : (
              <div className="hint-card">还没有选择文件。</div>
            )}
            <div className="capability-grid">
              {capabilities?.review.engines.map((engine) => (
                <div className={`capability-card ${engine.available ? "capability-ok" : "capability-off"}`} key={engine.key}>
                  <strong>{engine.label}</strong>
                  <p>{engine.available ? "当前可用" : engine.reason || "当前不可用"}</p>
                </div>
              ))}
            </div>
            {capabilityError ? <div className="error-banner">{capabilityError}</div> : null}
            <div className="panel-actions">
              <button className="primary-button" disabled={!file} onClick={() => setActiveStep(2)} type="button">
                下一步：审阅意图
              </button>
            </div>
          </div>
        ) : null}

        {activeStep === 2 ? (
          <div className="panel-body">
            <div className="panel-head">
              <h2>审阅意图</h2>
              <p>把角色、目标和附加约束写清楚，这一步决定输出质量上限。</p>
            </div>
            <div className="field-grid">
              <label className="field">
                <span>审阅角色</span>
                <input onChange={(event) => updateForm("expert_view", event.target.value)} value={form.expert_view} />
              </label>
              <label className="field">
                <span>批注作者名称</span>
                <input onChange={(event) => updateForm("comment_author", event.target.value)} value={form.comment_author} />
              </label>
            </div>
            <label className="field">
              <span>审阅目标 / 需求</span>
              <textarea onChange={(event) => updateForm("intent", event.target.value)} placeholder="说明需要改进或检查的内容" rows={8} value={form.intent} />
            </label>
            <label className="field">
              <span>附加约束</span>
              <textarea onChange={(event) => updateForm("constraints", event.target.value)} placeholder="每行一条" rows={6} value={form.constraints} />
            </label>
            <label className="toggle-row">
              <input checked={form.focus_only} onChange={(event) => updateForm("focus_only", event.target.checked)} type="checkbox" />
              <span>仅审阅需求中点到的段落/标题</span>
            </label>
            <div className="panel-actions">
              <button className="ghost-button" onClick={() => setActiveStep(1)} type="button">
                返回
              </button>
              <button className="primary-button" disabled={!form.intent.trim()} onClick={() => setActiveStep(3)} type="button">
                下一步：执行策略
              </button>
            </div>
          </div>
        ) : null}

        {activeStep === 3 ? (
          <div className="panel-body">
            <div className="panel-head">
              <h2>执行策略</h2>
              <p>高频参数直达，低频参数收进高级区，避免一上来就是整屏配置。</p>
            </div>
            <div className="field-grid three-col">
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
            <div className="field-grid three-col">
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
                <span>上下文内联</span>
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
                <input onChange={(event) => updateForm("model_override", event.target.value)} placeholder="可选" value={form.model_override} />
              </label>
            </div>
            <div className="toggle-grid">
              <label className="toggle-row"><input checked={form.allow_python_docx_fallback} onChange={(event) => updateForm("allow_python_docx_fallback", event.target.checked)} type="checkbox" /><span>允许 python-docx 兜底</span></label>
              <label className="toggle-row"><input checked={form.strip_existing_comments} onChange={(event) => updateForm("strip_existing_comments", event.target.checked)} type="checkbox" /><span>开始前删除原文批注</span></label>
              <label className="toggle-row"><input checked={form.prefer_replace} onChange={(event) => updateForm("prefer_replace", event.target.checked)} type="checkbox" /><span>更积极直接改文</span></label>
              <label className="toggle-row"><input checked={form.allow_expansion} onChange={(event) => updateForm("allow_expansion", event.target.checked)} type="checkbox" /><span>允许扩充完善</span></label>
              <label className="toggle-row"><input checked={form.allow_web_search} onChange={(event) => updateForm("allow_web_search", event.target.checked)} type="checkbox" /><span>允许联网检索</span></label>
              <label className="toggle-row"><input checked={form.extract_docx_images} onChange={(event) => updateForm("extract_docx_images", event.target.checked)} type="checkbox" /><span>提取文档图片</span></label>
              <label className="toggle-row"><input checked={form.extract_tables} onChange={(event) => updateForm("extract_tables", event.target.checked)} type="checkbox" /><span>提取表格元素</span></label>
              <label className="toggle-row"><input checked={form.table_image_understanding} onChange={(event) => updateForm("table_image_understanding", event.target.checked)} type="checkbox" /><span>表格图片理解</span></label>
            </div>
            <details className="advanced-panel">
              <summary>高级参数</summary>
              <div className="field-grid three-col">
                <label className="field"><span>跨段上下文</span><input max={10} min={0} onChange={(event) => updateForm("chunk_context", Number(event.target.value))} type="number" value={form.chunk_context} /></label>
                <label className="field"><span>上下文截断字符</span><input max={4000} min={0} onChange={(event) => updateForm("context_max_chars", Number(event.target.value))} type="number" value={form.context_max_chars} /></label>
                <label className="field"><span>图片理解提示词</span><input onChange={(event) => updateForm("table_image_prompt", event.target.value)} value={form.table_image_prompt} /></label>
              </div>
              <div className="field-grid three-col">
                <label className="field"><span>并行审阅</span><select onChange={(event) => updateForm("parallel_review", event.target.value === "true")} value={String(form.parallel_review)}><option value="true">开启</option><option value="false">关闭</option></select></label>
                <label className="field"><span>并行线程数</span><input max={8} min={1} onChange={(event) => updateForm("parallel_workers", Number(event.target.value))} type="number" value={form.parallel_workers} /></label>
                <label className="field"><span>每段最大段落数</span><input max={80} min={10} onChange={(event) => updateForm("chunk_size", Number(event.target.value))} type="number" value={form.chunk_size} /></label>
              </div>
              <label className="field"><span>并行启用阈值(段落数)</span><input max={1000} min={1} onChange={(event) => updateForm("parallel_min_paragraphs", Number(event.target.value))} type="number" value={form.parallel_min_paragraphs} /></label>
            </details>
            <div className="panel-actions">
              <button className="ghost-button" onClick={() => setActiveStep(2)} type="button">返回</button>
              <button className="primary-button" onClick={() => setActiveStep(4)} type="button">下一步：运行结果</button>
            </div>
          </div>
        ) : null}

        {activeStep === 4 ? (
          <div className="panel-body">
            <div className="panel-head">
              <h2>运行结果</h2>
              <p>执行入口、实时状态、产物下载和历史复用都收敛在这里。</p>
            </div>
            {submitError ? <div className="error-banner">{submitError}</div> : null}
            <div className="run-summary-bar">
              <div>
                <strong>{file?.name || "未选择文件"}</strong>
                <span>{form.intent.trim() ? `${form.intent.trim().slice(0, 48)}${form.intent.length > 48 ? "..." : ""}` : "尚未填写审阅意图"}</span>
              </div>
              <button className="primary-button" disabled={submitting} onClick={() => void handleSubmit()} type="button">
                {submitting ? "提交中..." : "开始审阅"}
              </button>
            </div>
            {currentRun ? (
              <>
                <div className="current-run-card">
                  <div className="current-run-top">
                    <div>
                      <strong>{currentRun.title}</strong>
                      <div className="run-card-meta">创建于 {currentRun.created_at}</div>
                    </div>
                    <span className={`status-pill status-${currentRun.status}`}>{formatStatus(currentRun.status)}</span>
                  </div>
                  {currentRun.error ? <div className="error-banner">{currentRun.error}</div> : null}
                  <div className="artifact-row">
                    {currentRun.artifacts.map((artifact) => (
                      <a className="artifact-card" href={artifactUrl(artifact.download_url)} key={artifact.name} rel="noreferrer" target="_blank">
                        <strong>{artifact.label}</strong>
                        <span>{artifact.filename}</span>
                      </a>
                    ))}
                  </div>
                </div>
                <div className="log-panel">
                  <div className="log-head">
                    <strong>实时日志</strong>
                    <span>{logLines.length} lines</span>
                  </div>
                  <pre>{logLines.length ? logLines.join("\n") : "等待任务日志..."}</pre>
                </div>
              </>
            ) : (
              <div className="hint-card">还没有运行记录。确认前三步后直接在这里发起执行。</div>
            )}
          </div>
        ) : null}
      </section>

      <aside className="side-panel">
        <div className="side-block">
          <div className="side-title">环境能力</div>
          <ul className="plain-list">
            <li>OpenAI Key: {capabilities?.features.openai_key ? "已配置" : "未配置"}</li>
            <li>Tavily: {capabilities?.features.tavily_key ? "已配置" : "未配置"}</li>
            <li>SQLite Checkpoint: {capabilities?.features.langgraph_sqlite ? "可用" : "缺失"}</li>
            <li>APIYI: {capabilities?.features.apiyi_key ? "已配置" : "未配置"}</li>
          </ul>
        </div>
        <div className="side-block">
          <div className="side-title">最近运行</div>
          <div className="run-list">
            {recentRuns.length ? (
              recentRuns.slice(0, 6).map((run) => (
                <button
                  className={`run-card ${currentRun?.id === run.id ? "run-card-active" : ""}`}
                  key={run.id}
                  onClick={() => {
                    setCurrentRun(run);
                    setLiveEvents(run.events || []);
                    setActiveStep(4);
                    if (["created", "queued", "running"].includes(run.status)) {
                      openEventStream(run.id, run.event_count);
                    }
                  }}
                  type="button"
                >
                  <div className="run-card-top">
                    <strong>{run.title}</strong>
                    <span className={`status-pill status-${run.status}`}>{formatStatus(run.status)}</span>
                  </div>
                  <div className="run-card-meta">{run.created_at}</div>
                </button>
              ))
            ) : (
              <div className="hint-card">暂无记录</div>
            )}
          </div>
        </div>
      </aside>
    </div>
  );
}
