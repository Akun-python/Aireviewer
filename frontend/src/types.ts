export type Artifact = {
  name: string;
  label: string;
  path: string;
  filename: string;
  size_bytes: number;
  content_type: string;
  download_url: string;
};

export type RunEvent = {
  id: number;
  ts: string;
  type: string;
  message: string;
  data: Record<string, unknown>;
};

export type RunMode = "review" | "report" | "report-complete" | "report-integrate";

export type AppRun = {
  id: string;
  mode: string;
  title: string;
  status: string;
  input_filename: string;
  params: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  started_at: string;
  finished_at: string;
  error: string;
  run_dir: string;
  result: Record<string, unknown>;
  artifacts: Artifact[];
  event_count: number;
  events: RunEvent[];
  conversation_id: string;
  version_no?: number | null;
  base_run_id: string;
  source_artifact: string;
};

export type CapabilityOption = {
  key: string;
  label: string;
  available: boolean;
  reason: string;
};

export type Capabilities = {
  root_dir: string;
  workspace_dir: string;
  features: {
    win32: boolean;
    python_docx: boolean;
    langgraph_sqlite: boolean;
    openai_key: boolean;
    tavily_key: boolean;
    apiyi_key: boolean;
  };
  review: {
    engines: CapabilityOption[];
    format_profiles: CapabilityOption[];
    memory_scopes: Array<{ key: string; label: string }>;
    inline_context_modes: Array<{ key: string; label: string }>;
    expansion_levels: Array<{ key: string; label: string }>;
  };
};

export type ReviewPreset = {
  key: string;
  label: string;
  description: string;
  expert_view: string;
  default_constraints: string[];
  diagnostics_dimensions: string[];
  section_expectations: Array<{
    key: string;
    label: string;
    keywords: string[];
    min_paragraphs: number;
  }>;
  skip_rules: string[];
  recommended_format_profile: string;
  sample_use_cases: string[];
  system_prompt_scaffold: string;
};

export type DiagnosticsCard = {
  key: string;
  label: string;
  severity: string;
  headline: string;
  score: number;
};

export type DiagnosticsPayload = {
  generated_at: string;
  preset: ReviewPreset;
  input_path: string;
  output_path: string;
  overview: {
    cards: DiagnosticsCard[];
    critical_count: number;
    warning_count: number;
    average_score: number;
    summary: string;
  };
  pre_review: Record<string, Record<string, unknown>>;
  post_review: Record<string, Record<string, unknown>>;
  change_risk: Record<string, unknown>;
};

export type ReviewConversationMode = "chat" | "apply";
export type ReviewConversationBaseSource = "latest" | "original" | "run";

export type ReviewConversationMessage = {
  id: string;
  role: string;
  mode: ReviewConversationMode;
  content: string;
  status: string;
  base_source: string;
  base_run_id: string;
  linked_run_id: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ReviewConversationVersion = {
  version_no: number;
  run_id: string;
  base_run_id: string;
  artifact_name: string;
  source_artifact: string;
  label: string;
  diagnostics_run_id: string;
  download_url: string;
  created_at: string;
};

export type ReviewConversationSummary = {
  id: string;
  title: string;
  input_filename: string;
  preset_key: string;
  created_at: string;
  updated_at: string;
  head_run_id: string;
  head_version_no: number;
  active_run_id: string;
  message_count: number;
  version_count: number;
  last_message_excerpt: string;
};

export type ReviewConversation = {
  id: string;
  title: string;
  input_filename: string;
  preset_key: string;
  defaults: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  head_run_id: string;
  head_version_no: number;
  active_run_id: string;
  original_artifact: Artifact;
  messages: ReviewConversationMessage[];
  versions: ReviewConversationVersion[];
  head_run: AppRun | null;
};

export type ReviewConversationAction = {
  user_message: ReviewConversationMessage;
  assistant_message: ReviewConversationMessage;
  linked_run: AppRun | null;
};
