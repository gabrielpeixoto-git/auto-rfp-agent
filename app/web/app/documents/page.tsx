"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
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
  FileText,
  Loader2,
  AlertCircle,
  Clock,
  CheckCircle2,
  XCircle,
  RefreshCw,
  FileUp,
  ArrowUpRight,
  FolderOpen,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useProjects } from "@/hooks/useProjects";
import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { documentsApi } from "@/lib/api/client";
import type { Document } from "@/types/api";

const getStatusBadge = (status: string) => {
  const variants: Record<string, {
    variant: "default" | "secondary" | "destructive" | "outline";
    label: string;
    className: string;
    icon: React.ComponentType<{ className?: string }>;
  }> = {
    // Status iniciais/pendentes
    pending: {
      variant: "outline",
      label: "Pendente",
      className: "bg-slate-100 text-slate-600 border-slate-200",
      icon: FileText,
    },
    uploaded: {
      variant: "outline",
      label: "Enviado",
      className: "bg-slate-100 text-slate-600 border-slate-200",
      icon: FileText,
    },
    // Status intermediários de processamento
    extracting: {
      variant: "secondary",
      label: "Extraindo",
      className: "bg-amber-100 text-amber-800 border-amber-200",
      icon: Loader2,
    },
    chunking: {
      variant: "secondary",
      label: "Processando",
      className: "bg-amber-100 text-amber-800 border-amber-200",
      icon: Loader2,
    },
    indexing: {
      variant: "secondary",
      label: "Indexando",
      className: "bg-amber-100 text-amber-800 border-amber-200",
      icon: Loader2,
    },
    processing: {
      variant: "secondary",
      label: "Processando",
      className: "bg-amber-100 text-amber-800 border-amber-200",
      icon: Loader2,
    },
    // Status finais
    processed: {
      variant: "default",
      label: "Processado",
      className: "bg-emerald-100 text-emerald-800 border-emerald-200",
      icon: CheckCircle2,
    },
    failed: {
      variant: "destructive",
      label: "Falhou",
      className: "bg-red-100 text-red-800 border-red-200",
      icon: XCircle,
    },
    error: {
      variant: "destructive",
      label: "Erro",
      className: "bg-red-100 text-red-800 border-red-200",
      icon: XCircle,
    },
  };
  return variants[status] || variants.pending;
};

interface DocumentWithProject extends Document {
  projectName?: string;
}

function DocumentCard({ document }: { document: DocumentWithProject }) {
  const router = useRouter();
  const statusConfig = getStatusBadge(document.status);
  const StatusIcon = statusConfig.icon;

  const handleClick = () => {
    if (document.project_id) {
      router.push(`/projects/${document.project_id}`);
    }
  };

  return (
    <Card
      className="group relative overflow-hidden cursor-pointer border-border/50 bg-card hover:bg-accent/50 hover:border-primary/20 hover:shadow-lg hover:shadow-primary/5 transition-all duration-300"
      onClick={handleClick}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

      <CardHeader className="relative pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-base font-semibold line-clamp-1 group-hover:text-primary transition-colors">
                {document.original_filename || document.filename}
              </CardTitle>
              {document.projectName && (
                <p className="text-xs text-muted-foreground">{document.projectName}</p>
              )}
            </div>
          </div>
          <Badge variant={statusConfig.variant} className={statusConfig.className}>
            <StatusIcon className="h-3 w-3 mr-1" />
            {statusConfig.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="relative pt-0">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Clock className="h-3.5 w-3.5" />
            <span>{new Date(document.created_at).toLocaleDateString("pt-BR")}</span>
          </div>
          {document.question_count !== undefined && document.question_count > 0 && (
            <span>{document.question_count} perguntas</span>
          )}
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 text-primary opacity-0 group-hover:opacity-100 transition-all duration-200 transform translate-x-2 group-hover:translate-x-0">
            <ArrowUpRight className="h-3.5 w-3.5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function DocumentsPage() {
  const { isAuthenticated, isInitialized, logout, user } = useAuth();
  const { projects, isLoading: projectsLoading } = useProjects();
  const router = useRouter();

  const [documents, setDocuments] = useState<DocumentWithProject[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAllDocuments = useCallback(async () => {
    if (!projects || projects.length === 0) {
      setDocuments([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const allDocs: DocumentWithProject[] = [];

      for (const project of projects) {
        try {
          const response = await documentsApi.list(project.id);
          const docs: Document[] = Array.isArray(response) ? response : (response as { items?: Document[] }).items || [];

          const docsWithProject = docs.map((doc: Document) => ({
            ...doc,
            projectName: project.name,
          }));

          allDocs.push(...docsWithProject);
        } catch (err) {
          console.error(`Erro ao buscar documentos do projeto ${project.id}:`, err);
        }
      }

      allDocs.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

      setDocuments(allDocs);
    } catch (err: any) {
      setError(err.message || "Erro ao carregar documentos");
    } finally {
      setIsLoading(false);
    }
  }, [projects]);

  useEffect(() => {
    if (isInitialized && !isAuthenticated) {
      router.push("/login");
    }
  }, [isInitialized, isAuthenticated, router]);

  useEffect(() => {
    if (projects && !projectsLoading) {
      fetchAllDocuments();
    }
  }, [projects, projectsLoading, fetchAllDocuments]);

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

  // Contadores de status - inclui todos os estados intermediários
  const processingStatuses = ["pending", "uploaded", "extracting", "chunking", "indexing", "processing"];
  const finalErrorStatuses = ["failed", "error"];

  const processingCount = documents.filter((d) => processingStatuses.includes(d.status)).length;
  const processedCount = documents.filter((d) => d.status === "processed").length;
  const errorCount = documents.filter((d) => finalErrorStatuses.includes(d.status)).length;

  return (
    <AppShell
      userName={user?.email?.split("@")[0]}
      userEmail={user?.email}
      onLogout={handleLogout}
    >
      <div className="container py-8 px-4 lg:px-8">
        <div className="mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
                <FileText className="h-8 w-8 text-primary" />
                Documentos
              </h1>
              <p className="text-muted-foreground mt-1.5">
                Visualize todos os documentos enviados em seus projetos
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                onClick={fetchAllDocuments}
                disabled={isLoading}
                className="gap-2"
              >
                <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
                Atualizar
              </Button>
              <Link href="/projects/new">
                <Button
                  size="lg"
                  className="bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary shadow-lg shadow-primary/25 transition-all duration-200 hover:shadow-xl hover:shadow-primary/20"
                >
                  <FileUp className="h-4 w-4 mr-2" />
                  Novo Projeto
                </Button>
              </Link>
            </div>
          </div>
        </div>

        {!isLoading && !error && documents.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
            <Card className="bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Total</p>
                    <p className="text-2xl font-bold">{documents.length}</p>
                  </div>
                  <div className="h-10 w-10 rounded-lg bg-primary/20 flex items-center justify-center">
                    <FileText className="h-5 w-5 text-primary" />
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Processados</p>
                    <p className="text-2xl font-bold text-emerald-600">{processedCount}</p>
                  </div>
                  <div className="h-10 w-10 rounded-lg bg-emerald-100 flex items-center justify-center">
                    <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Processando</p>
                    <p className="text-2xl font-bold text-amber-600">{processingCount}</p>
                  </div>
                  <div className="h-10 w-10 rounded-lg bg-amber-100 flex items-center justify-center">
                    <Loader2 className="h-5 w-5 text-amber-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Com Erro</p>
                    <p className="text-2xl font-bold text-red-600">{errorCount}</p>
                  </div>
                  <div className="h-10 w-10 rounded-lg bg-red-100 flex items-center justify-center">
                    <XCircle className="h-5 w-5 text-red-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {isLoading || projectsLoading ? (
          <div className="flex items-center justify-center py-16">
            <div className="flex flex-col items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
              </div>
              <p className="text-sm text-muted-foreground">Carregando documentos...</p>
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
                  <p className="font-medium">Erro ao carregar documentos</p>
                  <p className="text-sm text-destructive/80">{error}</p>
                </div>
              </div>
              <Button onClick={fetchAllDocuments} variant="outline" className="mt-4">
                Tentar novamente
              </Button>
            </CardContent>
          </Card>
        ) : documents.length === 0 ? (
          <EmptyState
            icon={FolderOpen}
            title="Nenhum documento ainda"
            description="Crie um projeto e faça upload de documentos RFP para começar. Os documentos serão processados automaticamente para extrair perguntas."
            actionLabel="Criar Projeto"
            actionHref="/projects/new"
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {documents.map((document) => (
              <DocumentCard key={document.id} document={document} />
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
