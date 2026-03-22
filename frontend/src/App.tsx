import { NavLink, Route, Routes } from "react-router-dom";
import PresetsPage from "./pages/PresetsPage";
import ReportCompletePage from "./pages/ReportCompletePage";
import ReportIntegratePage from "./pages/ReportIntegratePage";
import ReportPage from "./pages/ReportPage";
import RunsPage from "./pages/RunsPage";
import SettingsPage from "./pages/SettingsPage";
import SmartReviewPage from "./pages/SmartReviewPage";

const navItems = [
  { to: "/", label: "智能校稿" },
  { to: "/reports", label: "课题报告" },
  { to: "/report-complete", label: "报告完善" },
  { to: "/report-integrate", label: "多章整合" },
  { to: "/runs", label: "运行中心" },
  { to: "/presets", label: "预设规则" },
  { to: "/settings", label: "设置" },
];

export default function App() {
  return (
    <div className="app-shell">
      <aside className="app-rail">
        <div className="brand-block">
          <div className="brand-mark">AA</div>
          <div>
            <div className="brand-title">学术文稿助手</div>
            <div className="brand-subtitle">React 主入口 / Streamlit 控制台 / API 统一运行中心</div>
          </div>
        </div>
        <nav className="nav-stack">
          {navItems.map((item) => (
            <NavLink className={({ isActive }) => `nav-link ${isActive ? "nav-link-active" : ""}`} end={item.to === "/"} key={item.to} to={item.to}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="rail-note">
          React 负责主产品流程与运行中心，Streamlit 继续保留为内部控制台与兼容入口。
        </div>
      </aside>

      <main className="app-main">
        <Routes>
          <Route element={<SmartReviewPage />} path="/" />
          <Route element={<ReportPage />} path="/reports" />
          <Route element={<ReportCompletePage />} path="/report-complete" />
          <Route element={<ReportIntegratePage />} path="/report-integrate" />
          <Route element={<RunsPage />} path="/runs" />
          <Route element={<PresetsPage />} path="/presets" />
          <Route element={<SettingsPage />} path="/settings" />
        </Routes>
      </main>
    </div>
  );
}
