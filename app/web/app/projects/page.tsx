"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { 
  Plus, 
  Clock, 
  Loader2, 
  AlertCircle, 
  ArrowUpRight, 
  FolderOpen, 
  FolderKanban,
  Search,
  Filter,
  LayoutGrid,
  List,
  SortAsc,
  X
} from "lucide-react";
import { useProjects } from "@/hooks/useProjects";
import { useAuth } from "@/hooks/useAuth";
import { EmptyState } from "@/components/EmptyState";
import { AppShell } from "@/components/AppShell";
import { cn } from "@/lib/utils";
import type { Project } from "@/types/api";

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

function ProjectCard({ project }: { project: Project }) {
  const router = useRouter();
  const href = `/projects/${project.id}`;
  
  const handleClick = () => {
    router.push(href);
  };
  
  return (
    <Card 
      className="group relative overflow-hidden cursor-pointer border-border/50 bg-card hover:bg-accent/50 hover:border-primary/20 hover:shadow-lg hover:shadow-primary/5 transition-all duration-300 h-full"
      onClick={handleClick}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
      
      <CardHeader className="relative">
        <div className="flex items-start justify-between gap-3">
          <CardTitle className="text-lg font-semibold line-clamp-1 group-hover:text-primary transition-colors">
            {project.name}
          </CardTitle>
          {getStatusBadge(project.status)}
        </div>
        <CardDescription className="line-clamp-2 mt-2">
          {project.description || "Sem descrição"}
        </CardDescription>
      </CardHeader>
      <CardContent className="relative">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-muted">
              <Clock className="h-3.5 w-3.5" />
            </div>
            <span>Atualizado {new Date(project.updated_at).toLocaleDateString("pt-BR")}</span>
          </div>
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 text-primary opacity-0 group-hover:opacity-100 transition-all duration-200 transform translate-x-2 group-hover:translate-x-0">
            <ArrowUpRight className="h-3.5 w-3.5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// Componente de linha de projeto para visualização em lista
function ProjectListItem({ project }: { project: Project }) {
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
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4 flex-1 min-w-0">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
              <FolderKanban className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold truncate group-hover:text-primary transition-colors">
                  {project.name}
                </h3>
                {getStatusBadge(project.status)}
              </div>
              <p className="text-sm text-muted-foreground truncate mt-0.5">
                {project.description || "Sem descrição"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground shrink-0">
            <div className="flex items-center gap-1.5">
              <Clock className="h-4 w-4" />
              <span>{new Date(project.updated_at).toLocaleDateString("pt-BR")}</span>
            </div>
            <ArrowUpRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function ProjectsPage() {
  const { projects, isLoading, error, refetch } = useProjects();
  const { isAuthenticated, isInitialized, logout, user } = useAuth();
  const router = useRouter();
  
  // Estados para filtros
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<string>("updated");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  useEffect(() => {
    if (isInitialized && !isAuthenticated) {
      router.push("/login");
    }
  }, [isInitialized, isAuthenticated, router]);

  // Filtrar e ordenar projetos
  const filteredProjects = useMemo(() => {
    let result = [...projects];
    
    // Filtro por busca
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(p => 
        p.name.toLowerCase().includes(query) || 
        (p.description && p.description.toLowerCase().includes(query))
      );
    }
    
    // Filtro por status
    if (statusFilter !== "all") {
      result = result.filter(p => p.status === statusFilter);
    }
    
    // Ordenação
    result.sort((a, b) => {
      switch (sortBy) {
        case "name":
          return a.name.localeCompare(b.name);
        case "created":
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        case "updated":
        default:
          return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
      }
    });
    
    return result;
  }, [projects, searchQuery, statusFilter, sortBy]);

  // Contadores por status
  const statusCounts = useMemo(() => {
    return {
      all: projects.length,
      active: projects.filter(p => p.status === "active").length,
      draft: projects.filter(p => p.status === "draft").length,
      archived: projects.filter(p => p.status === "archived").length,
    };
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

  const clearFilters = () => {
    setSearchQuery("");
    setStatusFilter("all");
    setSortBy("updated");
  };

  const hasFilters = searchQuery || statusFilter !== "all";

  return (
    <AppShell
      userName={user?.email?.split("@")[0]}
      userEmail={user?.email}
      onLogout={handleLogout}
    >
      <div className="container py-8 px-4 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
                <FolderKanban className="h-8 w-8 text-primary" />
                Projetos
              </h1>
              <p className="text-muted-foreground mt-1.5">
                Gerencie todos os seus RFPs, RFIs e questionários de segurança
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

        {/* Barra de filtros */}
        <div className="mb-6 space-y-4">
          <div className="flex flex-col sm:flex-row gap-3">
            {/* Busca */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar projetos..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                >
                  <X className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                </button>
              )}
            </div>
            
            {/* Filtro de status */}
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-[180px]">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Filtrar por status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">
                  Todos ({statusCounts.all})
                </SelectItem>
                <SelectItem value="active">
                  Ativos ({statusCounts.active})
                </SelectItem>
                <SelectItem value="draft">
                  Rascunhos ({statusCounts.draft})
                </SelectItem>
                <SelectItem value="archived">
                  Arquivados ({statusCounts.archived})
                </SelectItem>
              </SelectContent>
            </Select>
            
            {/* Ordenação */}
            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger className="w-full sm:w-[180px]">
                <SortAsc className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Ordenar por" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="updated">Mais recentes</SelectItem>
                <SelectItem value="created">Data de criação</SelectItem>
                <SelectItem value="name">Nome</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          {/* Filtros ativos e view toggle */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {hasFilters && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearFilters}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <X className="h-4 w-4 mr-1" />
                  Limpar filtros
                </Button>
              )}
              <span className="text-sm text-muted-foreground">
                {filteredProjects.length} {filteredProjects.length === 1 ? "projeto" : "projetos"}
                {hasFilters && " encontrado(s)"}
              </span>
            </div>
            
            {/* View toggle */}
            <div className="flex items-center gap-1 bg-muted rounded-lg p-1">
              <button
                onClick={() => setViewMode("grid")}
                className={cn(
                  "p-2 rounded-md transition-all",
                  viewMode === "grid" 
                    ? "bg-background shadow-sm text-foreground" 
                    : "text-muted-foreground hover:text-foreground"
                )}
                title="Visualização em grade"
              >
                <LayoutGrid className="h-4 w-4" />
              </button>
              <button
                onClick={() => setViewMode("list")}
                className={cn(
                  "p-2 rounded-md transition-all",
                  viewMode === "list" 
                    ? "bg-background shadow-sm text-foreground" 
                    : "text-muted-foreground hover:text-foreground"
                )}
                title="Visualização em lista"
              >
                <List className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <div className="flex flex-col items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
              </div>
              <p className="text-sm text-muted-foreground">Carregando projetos...</p>
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
                  <p className="font-medium">Erro ao carregar projetos</p>
                  <p className="text-sm text-destructive/80">{error}</p>
                </div>
              </div>
              <Button onClick={refetch} variant="outline" className="mt-4">
                Tentar novamente
              </Button>
            </CardContent>
          </Card>
        ) : filteredProjects.length === 0 ? (
          <EmptyState
            icon={FolderOpen}
            title={hasFilters ? "Nenhum projeto encontrado" : "Nenhum projeto ainda"}
            description={
              hasFilters 
                ? "Tente ajustar os filtros de busca para encontrar o que procura."
                : "Crie seu primeiro projeto para começar a processar RFPs. Você poderá fazer upload de documentos, extrair perguntas automaticamente e gerar respostas com IA."
            }
            actionLabel={hasFilters ? "Limpar filtros" : "Criar Projeto"}
            actionHref={hasFilters ? undefined : "/projects/new"}
            onAction={hasFilters ? clearFilters : undefined}
          />
        ) : (
          <div className={cn(
            viewMode === "grid" 
              ? "grid gap-5 sm:grid-cols-2 lg:grid-cols-3" 
              : "space-y-3"
          )}>
            {filteredProjects.map((project) => (
              viewMode === "grid" ? (
                <ProjectCard key={project.id} project={project} />
              ) : (
                <ProjectListItem key={project.id} project={project} />
              )
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
