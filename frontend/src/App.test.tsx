import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./api/client", () => ({
  fetchCapabilities: vi.fn().mockResolvedValue({
    features: {
      win32: false,
      python_docx: true,
      langgraph_sqlite: false,
      openai_key: false,
      tavily_key: false,
      apiyi_key: false,
    },
    review: {
      engines: [
        { key: "auto", label: "自动", available: true, reason: "" },
        { key: "python-docx", label: "python-docx", available: true, reason: "" },
      ],
      format_profiles: [{ key: "none", label: "无", available: true, reason: "" }],
      memory_scopes: [{ key: "document", label: "按文档" }],
      inline_context_modes: [{ key: "boundary", label: "boundary" }],
      expansion_levels: [{ key: "none", label: "none" }],
    },
  }),
  fetchReviewPresets: vi.fn().mockResolvedValue([
    {
      key: "general_academic",
      label: "通用学术论文/综述",
      description: "desc",
      expert_view: "expert",
      default_constraints: [],
      diagnostics_dimensions: [],
      section_expectations: [],
      skip_rules: [],
      recommended_format_profile: "none",
      sample_use_cases: [],
      system_prompt_scaffold: "",
    },
  ]),
  fetchRuns: vi.fn().mockResolvedValue([]),
  fetchRun: vi.fn(),
  createRunEventSource: vi.fn(() => ({ close: vi.fn(), addEventListener: vi.fn() })),
  fetchRunDiagnostics: vi.fn(),
  createReviewRun: vi.fn(),
  createReportRun: vi.fn(),
  createReportCompleteRun: vi.fn(),
  createReportIntegrateRun: vi.fn(),
  getApiBase: vi.fn(() => "http://127.0.0.1:8011"),
  artifactUrl: vi.fn((value: string) => value),
}));

describe("App routes", () => {
  it("renders review workspace on root route", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "智能校稿" })).toBeInTheDocument();
    expect(screen.getByText("学术文稿助手")).toBeInTheDocument();
  });

  it("renders presets page", async () => {
    render(
      <MemoryRouter initialEntries={["/presets"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("预设规则 / 模板")).toBeInTheDocument();
    expect(await screen.findByText("通用学术论文/综述")).toBeInTheDocument();
  });
});
