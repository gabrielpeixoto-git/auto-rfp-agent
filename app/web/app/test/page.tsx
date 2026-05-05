"use client";

import { AuthGuard } from "@/components/AuthGuard";

function TestContent() {
  return (
    <div style={{ padding: 40 }}>
      <h1>Test Page Works!</h1>
      <p>If you see this, routing is OK and you are authenticated.</p>
    </div>
  );
}

export default function TestPage() {
  return (
    <AuthGuard>
      <TestContent />
    </AuthGuard>
  );
}
