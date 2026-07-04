import { useState } from "react";

import { AdminOverview } from "./components/AdminOverview";
import { ChatPanel } from "./components/ChatPanel";

export default function App() {
  const [adminRevision, setAdminRevision] = useState(0);

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">Vietnamese e-commerce support demo</p>
          <h1>A.S.I.A</h1>
        </div>
        <span className="status-badge">Local · Synthetic data</span>
      </header>

      <main className="app-grid">
        <ChatPanel
          onActivity={() => setAdminRevision((revision) => revision + 1)}
        />
        <AdminOverview refreshToken={adminRevision} />
      </main>
    </div>
  );
}
