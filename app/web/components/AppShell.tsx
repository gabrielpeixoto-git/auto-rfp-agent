"use client";

import { Sidebar } from "./Sidebar";
import { cn } from "@/lib/utils";

interface AppShellProps {
  children: React.ReactNode;
  userName?: string;
  userEmail?: string;
  onLogout?: () => void;
  className?: string;
}

export function AppShell({
  children,
  userName,
  userEmail,
  onLogout,
  className,
}: AppShellProps) {
  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar */}
      <Sidebar
        userName={userName}
        userEmail={userEmail}
        onLogout={onLogout}
      />

      {/* Main Content */}
      <main
        className={cn(
          "transition-all duration-300 ease-out",
          "lg:ml-[260px]", // Default expanded sidebar width
          "pt-16 lg:pt-0", // Mobile header spacing
          className
        )}
      >
        <div className="min-h-screen">
          {children}
        </div>
      </main>
    </div>
  );
}
