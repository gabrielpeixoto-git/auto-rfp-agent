"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  Plus, 
  Clock, 
  Loader2, 
  AlertCircle, 
  ArrowUpRight, 
  FolderOpen,
  LayoutDashboard,
  FolderKanban,
  FileText,
  Sparkles,
  TrendingUp,
  Activity,
  CheckCircle2,
  Clock4,
  ArrowRight
} from "lucide-react";
import { useProjects } from "@/hooks/useProjects";
import { useAuth } from "@/hooks/useAuth";
import { EmptyState } from "@/components/EmptyState";
import { AppShell } from "@/components/AppShell";
import type { Project } from "@/types/api";

// Componente de card de métrica
function MetricCard({ 
  title, 
  value, 
  description, 
  icon: Icon, 
  trend,
  trendUp 
}: { 
  title: string; 
  value: string | number; 
  description: string; 
  icon: React.ComponentType<{ className?: string }>;
  trend?: string;
  trendUp?: boolean;
}) {
  return (
    <Card className="border-border/50 bg-card hover:border-primary/20 hover:shadow-md transition-all duration-300">
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold tracking-tight">{value}</p>
            <p className="text-xs text-muted-foreground">{description}</p>
          </div>
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Icon className="h-5 w-5" />
          </div>
        </div>
        {trend && (
          <div className="mt-4 flex items-center gap-1.5">
            <TrendingUp className={`h-3.5 w-3.5 ${trendUp ? 'text-emerald-500' : 'text-amber-500'}`} />
            <span className={`text-xs font-medium ${trendUp ? 'text-emerald-600' : 'text-amber-600'}`}>
              {trend}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Componente de atalho rápido
function QuickAction({ 
  title, 
  description, 
  icon: Icon, 
  href,
  color = "primary"
}: { 
  title: string; 
  description: string; 
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  color?: "primary" | "blue" | "emerald" | "amber";
}) {
  const colorClasses = {
    primary: "bg-primary/10 text-primary hover:bg-primary/20",
    blue: "bg-blue-500/10 text-blue-600 hover:bg-blue-500/20",
    emerald: "bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20",
    amber: "bg-amber-500/10 text-amber-600 hover:bg-amber-500/20"
  };

  return (
    <Link href={href} className="group block">
      <Card className="border-border/50 bg-card hover:border-primary/20 hover:shadow-md transition-all duration-300 h-full">
        <CardContent className="p-5">
          <div className="flex items-start gap-4">
            <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-colors ${colorClasses[color]}`}>
              <Icon className="h-5 w-5" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-sm group-hover:text-primary transition-colors">
                {title}
              </h3>
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                {description}
              </p>
            </div>
            <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

const getStatusBadge = (status: string) => {
  const variants: Record<string, { 
    variant: "default" | "secondary" | "destructive" | "outline"; 
    label: string;
    className: string;
  }> = {
    draft: { 
      variant: "secondary", 
      label: "Rascunho",
      className: "bg-amber-100 text-amber-800 border-amber-200 hover:bg-amber-100"
    },
    active: { 
      variant: "default", 
      label: "Ativo",
      className: "bg-emerald-100 text-emerald-800 border-emerald-200 hover:bg-emerald-100"
    },
    archived: { 
      variant: "outline", 
      label: "Arquivado",
      className: "bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-100"
    },
  };
  const config = variants[status] || variants.draft;
  return <Badge variant={config.variant} className={config.className}>{config.label}</Badge>;
};

function RecentProjectCard({ project }: { project: Project }) {
  const router = useRouter();
  const href = `/projects/${project.id}`;
  
  const handleClick = () => {
    router.push(href);
  };
  
  return (
    <Card 
      className="group relative overflow-hidden cursor-pointer border-border/50 bg-card hover:bg-accent/50 hover:border-primary/20 hover:shadow-md transition-all duration-300"
      onClick={handleClick}
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <FolderKanban className="h-4 w-4 text-muted-foreground shrink-0" />
              <h3 className="font-medium text-sm truncate group-hover:text-primary transition-colors">
                {project.name}
              </h3>
            </div>
            <p className="text-xs text-muted-foreground mt-1 truncate">
              {project.description || "Sem descrição"}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {getStatusBadge(project.status)}
            <ArrowUpRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </div>
        <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          <span>Atualizado {new Date(project.updated_at).toLocaleDateString("pt-BR")}</span>
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { projects, isLoading, error, refetch } = useProjects();
  const { isAuthenticated, isInitialized, logout, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isInitialized && !isAuthenticated) {
      router.push("/login");
    }
  }, [isInitialized, isAuthenticated, router]);

  // Calcular métricas
  const metrics = useMemo(() => {
    if (!projects.length) return null;
    
    const total = projects.length;
    const active = projects.filter(p => p.status === "active").length;
    const draft = projects.filter(p => p.status === "draft").length;
    const archived = projects.filter(p => p.status === "archived").length;
    
    // Projetos atualizados nos últimos 7 dias
    const lastWeek = new Date();
    lastWeek.setDate(lastWeek.getDate() - 7);
    const recentUpdates = projects.filter(p => new Date(p.updated_at) >= lastWeek).length;
    
    return { total, active, draft, archived, recentUpdates };
  }, [projects]);

  // Projetos recentes (últimos 4)
  const recentProjects = useMemo(() => {
    return [...projects]
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      .slice(0, 4);
  }, [projects]);

  if (!isInitialized || !isAuthenticated) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const handleLogout = () => {
    logout("/login");
  };

  return (
    <AppShell
      userName={user?.email?.split("@")[0]}
      userEmail={user?.email}
      onLogout={handleLogout}
    >
      <div className="container py-8 px-4 lg:px-8">
        {/* Header de boas-vindas */}
        <div className="mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <LayoutDashboard className="h-4 w-4" />
                <span className="text-sm font-medium">Visão Geral</span>
              </div>
              <h1 className="text-3xl font-bold tracking-tight text-foreground">
                Dashboard
              </h1>
              <p className="text-muted-foreground mt-1.5">
                Bem-vindo de volta! Aqui está o resumo da sua atividade.
              </p>
            </div>
            <Link href="/projects/new">
              <Button 
                size="lg"
                className="bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary shadow-lg shadow-primary/25 transition-all duration-200 hover:shadow-xl hover:shadow-primary/20"
              >
                <Plus className="h-4 w-4 mr-2" />
                Novo Projeto
              </Button>
            </Link>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <div className="flex flex-col items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
              </div>
              <p className="text-sm text-muted-foreground">Carregando dashboard...</p>
            </div>
          </div>
        ) : error ? (
          <Card className="border-destructive/20 bg-destructive/5">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3 text-destructive">
                <div className="h-10 w-10 rounded-xl bg-destructive/10 flex items-center justify-center">
                  <AlertCircle className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-medium">Erro ao carregar dados</p>
                  <p className="text-sm text-destructive/80">{error}</p>
                </div>
              </div>
              <Button onClick={refetch} variant="outline" className="mt-4">
                Tentar novamente
              </Button>
            </CardContent>
          </Card>
        ) : projects.length === 0 ? (
          <EmptyState
            icon={FolderOpen}
            title="Bem-vindo ao Auto-RFP Agent"
            description="Comece criando seu primeiro projeto para processar RFPs. Você poderá fazer upload de documentos, extrair perguntas automaticamente e gerar respostas com IA."
            actionLabel="Criar Primeiro Projeto"
            actionHref="/projects/new"
          />
        ) : (
          <div className="space-y-8">
            {/* Métricas */}
            <section>
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Activity className="h-5 w-5 text-primary" />
                Métricas do Sistema
              </h2>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <MetricCard
                  title="Total de Projetos"
                  value={metrics?.total || 0}
                  description="Todos os projetos criados"
                  icon={FolderKanban}
                  trend="+2 este mês"
                  trendUp={true}
                />
                <MetricCard
                  title="Projetos Ativos"
                  value={metrics?.active || 0}
                  description="Em andamento"
                  icon={CheckCircle2}
                  trend="75% do total"
                  trendUp={true}
                />
                <MetricCard
                  title="Rascunhos"
                  value={metrics?.draft || 0}
                  description="Aguardando finalização"
                  icon={Clock4}
                />
                <MetricCard
                  title="Atualizações Recentes"
                  value={metrics?.recentUpdates || 0}
                  description="Nos últimos 7 dias"
                  icon={TrendingUp}
                  trend="Ativo"
                  trendUp={true}
                />
              </div>
            </section>

            {/* Grid de conteúdo principal */}
            <div className="grid gap-8 lg:grid-cols-3">
              {/* Projetos Recentes */}
              <section className="lg:col-span-2">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold flex items-center gap-2">
                    <Clock className="h-5 w-5 text-primary" />
                    Projetos Recentes
                  </h2>
                  <Link href="/projects">
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-primary">
                      Ver todos
                      <ArrowRight className="h-4 w-4 ml-1" />
                    </Button>
                  </Link>
                </div>
                <div className="space-y-3">
                  {recentProjects.map((project) => (
                    <RecentProjectCard key={project.id} project={project} />
                  ))}
                </div>
              </section>

              {/* Atalhos Rápidos */}
              <section>
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-primary" />
                  Atalhos Rápidos
                </h2>
                <div className="space-y-3">
                  <QuickAction
                    title="Todos os Projetos"
                    description="Ver lista completa e gerenciar projetos"
                    icon={FolderKanban}
                    href="/projects"
                    color="blue"
                  />
                  <QuickAction
                    title="Novo Projeto"
                    description="Criar um novo RFP ou RFI"
                    icon={Plus}
                    href="/projects/new"
                    color="emerald"
                  />
                  <QuickAction
                    title="Documentos"
                    description="Acessar todos os documentos"
                    icon={FileText}
                    href="/documents"
                    color="amber"
                  />
                </div>

                {/* Card de status */}
                <Card className="mt-6 border-border/50 bg-gradient-to-br from-primary/5 to-transparent">
                  <CardContent className="p-5">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                        <CheckCircle2 className="h-5 w-5" />
                      </div>
                      <div>
                        <p className="font-semibold text-sm">Sistema Operacional</p>
                        <p className="text-xs text-muted-foreground">Todos os serviços ativos</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </section>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
