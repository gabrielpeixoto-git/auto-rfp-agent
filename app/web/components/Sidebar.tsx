"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  LayoutDashboard,
  FolderKanban,
  FileText,
  Settings,
  LogOut,
  User,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
} from "lucide-react";
import { useState } from "react";

interface SidebarProps {
  userName?: string;
  userEmail?: string;
  onLogout?: () => void;
}

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  description?: string;
}

const mainNavItems: NavItem[] = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
    description: "Visão geral dos projetos",
  },
  {
    label: "Projetos",
    href: "/projects",
    icon: FolderKanban,
    description: "Gerenciar RFPs e RFIs",
  },
];

const secondaryNavItems: NavItem[] = [
  {
    label: "Documentos",
    href: "/documents",
    icon: FileText,
    description: "Todos os documentos",
  },
  {
    label: "Configurações",
    href: "/settings",
    icon: Settings,
    description: "Preferências da conta",
  },
];

function NavLink({
  item,
  isCollapsed,
  isActive,
}: {
  item: NavItem;
  isCollapsed: boolean;
  isActive: boolean;
}) {
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      className={cn(
        "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 ease-out",
        "hover:shadow-sm relative",
        isActive
          ? "bg-gradient-to-r from-primary/10 to-primary/5 text-primary shadow-sm ring-1 ring-primary/20"
          : "text-muted-foreground hover:bg-accent hover:text-foreground",
        isCollapsed && "justify-center px-2"
      )}
      title={isCollapsed ? item.label : undefined}
    >
      <span
        className={cn(
          "flex h-8 w-8 items-center justify-center rounded-lg transition-all duration-200",
          isActive
            ? "bg-primary text-primary-foreground shadow-sm"
            : "bg-muted group-hover:bg-background group-hover:shadow-sm"
        )}
      >
        <Icon className="h-4 w-4" />
      </span>
      {!isCollapsed && (
        <span className="flex-1 truncate">{item.label}</span>
      )}
      {!isCollapsed && isActive && (
        <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
      )}
      {/* Active indicator bar */}
      {isActive && (
        <span className="absolute left-0 top-1/2 -translate-y-1/2 h-6 w-0.5 rounded-full bg-primary" />
      )}
    </Link>
  );
}

export function Sidebar({ userName, userEmail, onLogout }: SidebarProps) {
  const pathname = usePathname();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  return (
    <>
      {/* Mobile Header */}
      <header className="fixed top-0 left-0 right-0 z-50 h-16 border-b bg-background/95 backdrop-blur-xl lg:hidden">
        <div className="flex h-full items-center justify-between px-4">
          <Link href="/dashboard" className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-md shadow-primary/25">
              <Sparkles className="h-4 w-4" />
            </div>
            <span className="text-sm font-bold tracking-tight">Auto-RFP</span>
          </Link>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsMobileOpen(!isMobileOpen)}
            className="h-9 w-9 rounded-lg"
          >
            {isMobileOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </Button>
        </div>
      </header>

      {/* Mobile Menu Overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed left-0 top-0 z-40 flex h-screen flex-col border-r bg-background/95 backdrop-blur-xl transition-all duration-300 ease-out",
          isCollapsed ? "lg:w-[72px]" : "lg:w-[260px]",
          isMobileOpen
            ? "translate-x-0 w-[280px]"
            : "-translate-x-full lg:translate-x-0 w-[260px]"
        )}
      >
        {/* Logo Section */}
        <div className="flex h-16 items-center justify-between border-b px-4">
          <Link
            href="/dashboard"
            className={cn(
              "flex items-center gap-2.5 transition-all duration-300",
              isCollapsed && "justify-center"
            )}
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-lg shadow-primary/25">
              <Sparkles className="h-5 w-5" />
            </div>
            {!isCollapsed && (
              <div className="flex flex-col">
                <span className="text-sm font-bold tracking-tight text-foreground">
                  Auto-RFP
                </span>
                <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                  Agent
                </span>
              </div>
            )}
          </Link>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className={cn(
              "h-7 w-7 rounded-lg opacity-0 transition-all duration-200 hover:bg-accent group-hover:opacity-100",
              isCollapsed && "opacity-100"
            )}
          >
            {isCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* Navigation */}
        <div className="flex-1 overflow-y-auto py-4">
          <nav className={cn("space-y-1", isCollapsed ? "px-2" : "px-3")}>
            {!isCollapsed && (
              <p className="mb-2 px-3 text-xs font-semibold text-muted-foreground/60 uppercase tracking-wider">
                Principal
              </p>
            )}
            {mainNavItems.map((item) => (
              <NavLink
                key={item.href}
                item={item}
                isCollapsed={isCollapsed}
                isActive={pathname === item.href || (item.href !== "/dashboard" && pathname?.startsWith(item.href + "/"))}
              />
            ))}
          </nav>

          <nav
            className={cn(
              "mt-6 space-y-1",
              isCollapsed ? "px-2" : "px-3"
            )}
          >
            {!isCollapsed && (
              <p className="mb-2 px-3 text-xs font-semibold text-muted-foreground/60 uppercase tracking-wider">
                Outros
              </p>
            )}
            {secondaryNavItems.map((item) => (
              <NavLink
                key={item.href}
                item={item}
                isCollapsed={isCollapsed}
                isActive={pathname === item.href || pathname?.startsWith(item.href + "/")}
              />
            ))}
          </nav>
        </div>

        {/* User Section */}
        <div
          className={cn(
            "border-t bg-muted/30 p-4",
            isCollapsed && "lg:px-2"
          )}
        >
          <div
            className={cn(
              "flex items-center gap-3",
              isCollapsed && "lg:flex-col"
            )}
          >
            <div
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-secondary to-muted shadow-sm ring-1 ring-border/50 cursor-pointer transition-all duration-200 hover:shadow-md hover:ring-border"
              title={userName || "Usuário"}
            >
              <User className="h-5 w-5 text-muted-foreground" />
            </div>

            <div className={cn(
              "flex-1 min-w-0",
              isCollapsed && "lg:hidden"
            )}>
              <p className="text-sm font-medium text-foreground truncate">
                {userName || "Usuário"}
              </p>
              <p className="text-xs text-muted-foreground truncate">
                {userEmail || "usuario@email.com"}
              </p>
            </div>

            <Button
              variant="ghost"
              size="icon"
              onClick={onLogout}
              title="Sair"
              className={cn(
                "h-8 w-8 shrink-0 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all duration-200",
                isCollapsed && "lg:mt-2"
              )}
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </aside>
    </>
  );
}
