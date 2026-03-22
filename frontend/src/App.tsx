import { NavLink, Route, Routes } from "react-router-dom";
import PlaceholderPage from "./pages/PlaceholderPage";
import SmartReviewPage from "./pages/SmartReviewPage";

const navItems = [
  { to: "/", label: "智能校稿" },
  { to: "/reports", label: "课题报告" },
  { to: "/report-complete", label: "报告完善" },
  { to: "/report-integrate", label: "多章整合" },
];

export default function App() {
  return (
    <div className="app-shell">
      <aside className="app-rail">
        <div className="brand-block">
          <div className="brand-mark">WR</div>
          <div>
            <div className="brand-title">Word Revision Agent</div>
            <div className="brand-subtitle">React workflow frontend</div>
          </div>
        </div>
        <nav className="nav-stack">
          {navItems.map((item) => (
            <NavLink className={({ isActive }) => `nav-link ${isActive ? "nav-link-active" : ""}`} end={item.to === "/"} key={item.to} to={item.to}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="rail-note">Streamlit 仍保留。React 先承接更强调流程感的主路径，避免所有参数挤在同一屏。</div>
      </aside>

      <main className="app-main">
        <Routes>
          <Route element={<SmartReviewPage />} path="/" />
          <Route element={<PlaceholderPage description="生成式报告能力后续会迁到统一服务层。当前建议继续使用 Streamlit 版本。" title="课题报告生成" />} path="/reports" />
          <Route element={<PlaceholderPage description="已有报告补全功能将在统一 run center 上承接。当前建议继续使用 Streamlit 版本。" title="完善已有报告" />} path="/report-complete" />
          <Route element={<PlaceholderPage description="多章节整合依赖较长链路，先留在 Streamlit，后续迁移到同一批量任务框架。" title="多章节整合" />} path="/report-integrate" />
        </Routes>
      </main>
    </div>
  );
}
