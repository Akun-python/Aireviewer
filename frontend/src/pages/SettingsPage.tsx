import { useEffect, useState } from "react";
import { fetchCapabilities, getApiBase } from "../api/client";
import type { Capabilities } from "../types";

export default function SettingsPage() {
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);

  useEffect(() => {
    fetchCapabilities().then(setCapabilities).catch(() => undefined);
  }, []);

  return (
    <div className="page-grid">
      <section className="hero-panel compact-hero">
        <div>
          <span className="hero-eyebrow">Settings & Ops</span>
          <h1>设置</h1>
          <p>公开主入口是 React，Streamlit 继续保留为控制台 / 兼容入口，API 与 CLI 用于自动化集成。</p>
        </div>
      </section>
      <section className="preset-grid">
        <article className="preset-card">
          <h3>接口与入口</h3>
          <ul className="plain-list">
            <li>React 主入口：`/`、`/reports`、`/report-complete`、`/report-integrate`、`/runs`、`/presets`、`/settings`</li>
            <li>API Base：{getApiBase()}</li>
            <li>Streamlit 控制台：`http://127.0.0.1:8501`</li>
            <li>推荐体验主产品时使用 React，排查或兜底时使用 Streamlit。</li>
          </ul>
        </article>
        <article className="preset-card">
          <h3>环境能力</h3>
          <ul className="plain-list">
            <li>Win32 Word：{capabilities?.features.win32 ? "可用" : "不可用"}</li>
            <li>python-docx：{capabilities?.features.python_docx ? "可用" : "不可用"}</li>
            <li>Tavily：{capabilities?.features.tavily_key ? "已配置" : "未配置"}</li>
            <li>OpenAI/API Key：{capabilities?.features.openai_key ? "已配置" : "未配置"}</li>
            <li>SQLite Checkpoint：{capabilities?.features.langgraph_sqlite ? "可用" : "不可用"}</li>
          </ul>
        </article>
        <article className="preset-card">
          <h3>运行建议</h3>
          <ul className="plain-list">
            <li>中文社科、课题申报、文献综述优先选择对应预设。</li>
            <li>只做内部一致性核查时可以使用“仅学术诊断”。</li>
            <li>需要 Word 修订痕迹与高保真排版时优先使用 Win32 Word。</li>
            <li>无 Word 环境时仍可运行诊断与 python-docx 降级流程。</li>
          </ul>
        </article>
      </section>
    </div>
  );
}
