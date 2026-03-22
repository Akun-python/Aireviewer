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

export type ReviewRun = {
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
    engines: Array<{ key: string; label: string; available: boolean; reason: string }>;
    format_profiles: Array<{ key: string; label: string; available: boolean; reason: string }>;
    memory_scopes: Array<{ key: string; label: string }>;
    inline_context_modes: Array<{ key: string; label: string }>;
    expansion_levels: Array<{ key: string; label: string }>;
  };
};
