import { useEffect, useState } from "react";
import { fetchReviewPresets } from "../api/client";
import type { ReviewPreset } from "../types";

export default function PresetsPage() {
  const [presets, setPresets] = useState<ReviewPreset[]>([]);

  useEffect(() => {
    fetchReviewPresets().then(setPresets).catch(() => undefined);
  }, []);

  return (
    <div className="page-grid">
      <section className="hero-panel compact-hero">
        <div>
          <span className="hero-eyebrow">Preset Library</span>
          <h1>预设规则 / 模板</h1>
          <p>React 和 Streamlit 共用同一套稳定枚举，不在界面里硬编码业务逻辑。</p>
        </div>
      </section>
      <section className="preset-grid">
        {presets.map((preset) => (
          <article className="preset-card" key={preset.key}>
            <div className="section-bar compact">
              <div>
                <span className="section-eyebrow">{preset.key}</span>
                <h3>{preset.label}</h3>
              </div>
              <span className="mini-pill">{preset.recommended_format_profile}</span>
            </div>
            <p>{preset.description}</p>
            <div className="preset-block">
              <strong>审阅角色</strong>
              <p>{preset.expert_view}</p>
            </div>
            <div className="preset-block">
              <strong>诊断维度</strong>
              <div className="tag-row">
                {preset.diagnostics_dimensions.map((item) => (
                  <span className="tag" key={item}>{item}</span>
                ))}
              </div>
            </div>
            <div className="preset-block">
              <strong>重点章节</strong>
              <ul className="plain-list">
                {preset.section_expectations.map((item) => (
                  <li key={item.key}>{item.label}</li>
                ))}
              </ul>
            </div>
            <div className="preset-block">
              <strong>默认约束</strong>
              <ul className="plain-list">
                {preset.default_constraints.slice(0, 5).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div className="preset-block">
              <strong>使用建议</strong>
              <ul className="plain-list">
                {preset.sample_use_cases.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
