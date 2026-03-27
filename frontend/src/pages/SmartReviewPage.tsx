import { useEffect, useState } from "react";
import {
  createReviewConversation,
  createReviewConversationMessage,
  fetchCapabilities,
  fetchReviewConversation,
  fetchReviewConversations,
  fetchReviewPresets,
  fetchRun,
} from "../api/client";
import { MarkdownMessage } from "../components/MarkdownMessage";
import { RunResultPanel, formatStatus } from "../components/RunPresentation";
import { useReviewDiagnostics } from "../hooks/useReviewDiagnostics";
import { useRunWorkspace } from "../hooks/useRunWorkspace";
import type { AppRun, Capabilities, DiagnosticsPayload, ReviewConversation, ReviewConversationBaseSource, ReviewConversationSummary, ReviewPreset } from "../types";

type CreateForm = {
  title: string;
  preset_key: string;
  expert_view: string;
  constraints: string;
  revision_engine: string;
  format_profile: string;
  diagnostics: boolean;
  allow_web_search: boolean;
  model_override: string;
};

type Composer = {
  mode: "chat" | "apply";
  content: string;
  base_source: ReviewConversationBaseSource;
  base_run_id: string;
  expert_view: string;
  constraints: string;
  revision_engine: string;
  format_profile: string;
  allow_web_search: boolean;
  allow_expansion: boolean;
  diagnostics: boolean;
};

type ContextTab = "versions" | "run" | "diagnostics";

const defaultCreateForm: CreateForm = {
  title: "",
  preset_key: "general_academic",
  expert_view: "",
  constraints: "",
  revision_engine: "auto",
  format_profile: "none",
  diagnostics: true,
  allow_web_search: false,
  model_override: "",
};

const defaultComposer: Composer = {
  mode: "chat",
  content: "",
  base_source: "latest",
  base_run_id: "",
  expert_view: "",
  constraints: "",
  revision_engine: "auto",
  format_profile: "none",
  allow_web_search: false,
  allow_expansion: false,
  diagnostics: true,
};

const ACTIVE_RUN_STATUSES = new Set(["created", "queued", "running"]);
const CONTEXT_TABS: Array<{ key: ContextTab; label: string }> = [
  { key: "versions", label: "版本" },
  { key: "run", label: "运行" },
  { key: "diagnostics", label: "诊断" },
];

function isConcreteRunId(value: string) {
  const text = (value || "").trim();
  return Boolean(text) && !text.startsWith("pending:");
}

function constraintLines(value: string) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function bubbleLabel(role: string) {
  return role === "user" ? "你" : "助手";
}

function versionLabel(versionNo: number) {
  return versionNo ? `V${versionNo}` : "原稿";
}

function ConversationRail() {
  return null;
}

function CreateState() {
  return null;
}

function TitleBar() {
  return null;
}

function ComposerPanel() {
  return null;
}

function DiagnosticsTab() {
  return null;
}

function ContextPanel() {
  return null;
}

export default function SmartReviewPage() {
  const [file, setFile] = useState<File | null>(null);
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [presets, setPresets] = useState<ReviewPreset[]>([]);
  const [conversations, setConversations] = useState<ReviewConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState("");
  const [conversation, setConversation] = useState<ReviewConversation | null>(null);
  const [createForm, setCreateForm] = useState<CreateForm>(defaultCreateForm);
  const [composer, setComposer] = useState<Composer>(defaultComposer);
  const [showOverrides, setShowOverrides] = useState(false);
  const [createMode, setCreateMode] = useState(true);
  const [activeContextTab, setActiveContextTab] = useState<ContextTab>("versions");
  const [contextPanelOpen, setContextPanelOpen] = useState(false);
  const [railOpen, setRailOpen] = useState(false);
  const [createError, setCreateError] = useState("");
  const [messageError, setMessageError] = useState("");
  const [creating, setCreating] = useState(false);
  const [sending, setSending] = useState(false);
  const { currentRun, recentRuns, selectRun, trackRun } = useRunWorkspace("review");
  const activeRun = currentRun ?? conversation?.head_run ?? null;
  const { diagnostics, diagnosticsError } = useReviewDiagnostics(activeRun);

  async function refreshConversationList(selectNewest = false) {
    const items = await fetchReviewConversations();
    setConversations(items);
    if (!items.length) {
      setActiveConversationId("");
      setConversation(null);
      setCreateMode(true);
      return;
    }
    if (selectNewest && items[0]) {
      setActiveConversationId(items[0].id);
      setCreateMode(false);
    }
  }

  async function refreshConversation(conversationId: string) {
    const detail = await fetchReviewConversation(conversationId);
    setConversation(detail);
    setCreateMode(false);
    if (isConcreteRunId(detail.active_run_id) && currentRun?.id !== detail.active_run_id) {
      fetchRun(detail.active_run_id).then(selectRun).catch(() => undefined);
    } else if (!detail.active_run_id && detail.head_run && currentRun?.id !== detail.head_run.id) {
      selectRun(detail.head_run);
    }
  }

  useEffect(() => {
    fetchCapabilities().then(setCapabilities).catch(() => undefined);
    fetchReviewPresets().then(setPresets).catch(() => undefined);
    refreshConversationList(true).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!activeConversationId) {
      setConversation(null);
      return;
    }
    refreshConversation(activeConversationId).catch(() => undefined);
  }, [activeConversationId]);

  useEffect(() => {
    if (!activeConversationId || !currentRun || currentRun.conversation_id !== activeConversationId) {
      return;
    }
    refreshConversation(activeConversationId).catch(() => undefined);
  }, [activeConversationId, currentRun?.event_count, currentRun?.id, currentRun?.status]);

  function updateCreate<K extends keyof CreateForm>(key: K, value: CreateForm[K]) {
    setCreateForm((previous) => ({ ...previous, [key]: value }));
  }

  function updateComposer<K extends keyof Composer>(key: K, value: Composer[K]) {
    setComposer((previous) => ({ ...previous, [key]: value }));
  }

  function openCreateMode() {
    setCreateMode(true);
    setCreateError("");
    setRailOpen(false);
  }

  async function handleCreateConversation() {
    if (!file) {
      setCreateError("请先上传 Word 文稿。");
      return;
    }
    setCreating(true);
    setCreateError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", createForm.title);
      formData.append("preset_key", createForm.preset_key);
      formData.append("expert_view", createForm.expert_view);
      formData.append("constraints_json", JSON.stringify(constraintLines(createForm.constraints)));
      formData.append("revision_engine", createForm.revision_engine);
      formData.append("format_profile", createForm.format_profile);
      formData.append("diagnostics", String(createForm.diagnostics));
      formData.append("allow_web_search", String(createForm.allow_web_search));
      formData.append("model_override", createForm.model_override);
      const detail = await createReviewConversation(formData);
      setConversation(detail);
      setActiveConversationId(detail.id);
      setFile(null);
      setCreateMode(false);
      setCreateForm((previous) => ({ ...defaultCreateForm, preset_key: previous.preset_key }));
      setActiveContextTab("versions");
      setContextPanelOpen(false);
      await refreshConversationList();
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : "创建会话失败");
    } finally {
      setCreating(false);
    }
  }

  async function handleSendMessage() {
    if (!conversation) {
      setMessageError("请先创建或选择文稿会话。");
      return;
    }
    if (!composer.content.trim()) {
      setMessageError("请输入内容。");
      return;
    }
    if (composer.mode === "apply" && conversation.active_run_id) {
      setMessageError("当前会话已有执行中的修改任务。");
      return;
    }
    setSending(true);
    setMessageError("");
    try {
      const action = await createReviewConversationMessage(conversation.id, {
        mode: composer.mode,
        content: composer.content,
        base_source: composer.base_source,
        base_run_id: composer.base_source === "run" ? composer.base_run_id : "",
        options_patch:
          composer.mode === "apply" && showOverrides
            ? {
                expert_view: composer.expert_view,
                constraints: constraintLines(composer.constraints),
                revision_engine: composer.revision_engine,
                format_profile: composer.format_profile,
                allow_web_search: composer.allow_web_search,
                allow_expansion: composer.allow_expansion,
                diagnostics: composer.diagnostics,
              }
            : {},
      });
      if (action.linked_run) {
        trackRun(action.linked_run);
        setActiveContextTab("run");
      }
      await refreshConversation(conversation.id);
      await refreshConversationList();
      setComposer((previous) => ({ ...previous, content: "" }));
      setContextPanelOpen(true);
    } catch (error) {
      setMessageError(error instanceof Error ? error.message : "发送失败");
    } finally {
      setSending(false);
    }
  }

  async function openVersion(runId: string) {
    try {
      const run = await fetchRun(runId);
      selectRun(run);
      setComposer((previous) => ({ ...previous, base_source: "run", base_run_id: runId }));
      setActiveContextTab("run");
    } catch (error) {
      setMessageError(error instanceof Error ? error.message : "加载版本失败");
    }
  }

  const overlayOpen = railOpen || contextPanelOpen;

  return (
    <div className="page-grid review-page">
      {overlayOpen ? <button aria-label="Close side panels" className="review-backdrop" onClick={() => { setRailOpen(false); setContextPanelOpen(false); }} type="button" /> : null}
      <section className="review-workspace">
        <div className={`review-pane review-pane-rail ${railOpen ? "review-pane-open" : ""}`}></div>
        <main className="review-main"></main>
        <div className={`review-pane review-pane-context ${contextPanelOpen ? "review-pane-open" : ""}`}></div>
      </section>
    </div>
  );
}
