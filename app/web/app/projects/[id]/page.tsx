"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Upload,
  FileText,
  CheckCircle,
  Clock,
  AlertCircle,
  Brain,
  Loader2,
  ArrowLeft,
  FolderKanban,
} from "lucide-react";
import { useProject } from "@/hooks/useProjects";
import { useDocuments } from "@/hooks/useDocuments";
import { useAuth } from "@/hooks/useAuth";
import { EmptyStateCompact } from "@/components/EmptyState";
import { useToastContext } from "@/contexts/ToastContext";
import { AuthGuard } from "@/components/AuthGuard";
import { AppShell } from "@/components/AppShell";
import type { Document } from "@/types/api";

const getStatusBadge = (status: string) => {
  const variants: Record<string, { variant: "default" | "secondary" | "destructive" | "outline"; label: string; icon: React.ReactNode }> = {
    // Status finais
    processed: { variant: "outline", label: "Processado", icon: <CheckCircle className="h-3 w-3" /> },
    failed: { variant: "destructive", label: "Falhou", icon: <AlertCircle className="h-3 w-3" /> },
    error: { variant: "destructive", label: "Erro", icon: <AlertCircle className="h-3 w-3" /> },
    // Status intermediários de processamento
    processing: { variant: "default", label: "Processando", icon: <Brain className="h-3 w-3 animate-pulse" /> },
    extracting: { variant: "default", label: "Extraindo", icon: <Brain className="h-3 w-3 animate-pulse" /> },
    chunking: { variant: "default", label: "Processando", icon: <Brain className="h-3 w-3 animate-pulse" /> },
    indexing: { variant: "default", label: "Indexando", icon: <Brain className="h-3 w-3 animate-pulse" /> },
    // Status iniciais/pendentes
    uploaded: { variant: "secondary", label: "Enviado", icon: <Clock className="h-3 w-3" /> },
    pending: { variant: "secondary", label: "Pendente", icon: <Clock className="h-3 w-3" /> },
  };
  const config = variants[status] || variants.pending;
  return (
    <Badge variant={config.variant} className="flex items-center gap-1">
      {config.icon}
      {config.label}
    </Badge>
  );
};

// Página pública exporta componente envolvido com AuthGuard
export default function ProjectPage({ params }: { params: { id: string } }) {
  return (
    <AuthGuard>
      <ProjectPageContent params={params} />
    </AuthGuard>
  );
}

// Componente interno que recebe os params
function ProjectPageContent({ params }: { params: { id: string } }) {
  // FONTE ÚNICA DE VERDADE: apenas params.id da rota /projects/[id]
  const projectId = params?.id;

  console.log("==========================================");
  console.log("[PAGE] params.id:", projectId);
  console.log("[PAGE] FONTE: params (rota /projects/[id])");
  console.log("==========================================");

  if (!projectId || projectId.trim() === "" || projectId === "undefined" || projectId === "null") {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Alert variant="destructive" className="max-w-md">
          <AlertDescription>ID do projeto inválido ou não fornecido</AlertDescription>
        </Alert>
      </div>
    );
  }

  return <ProjectContent projectId={projectId} />;
}

function ProjectContent({ projectId }: { projectId: string }) {
  // TODOS OS HOOKS DEVEM SER CHAMADOS PRIMEIRO - ordem estável em todos os renders
  const [isDragging, setIsDragging] = useState(false);
  const { project, isLoading: projectLoading, error: projectError } = useProject(projectId);
  const { documents, isLoading: documentsLoading, error: documentsError, uploadDocument } = useDocuments(projectId);
  const { error: showError, success: showSuccess } = useToastContext();
  const { logout, user } = useAuth();
  const router = useRouter();

  // LOG VISÍVEL para confirmar que novo frontend está rodando
  console.log("🚀 FRONTEND NOVO RODANDO - v2024.04.28");
  console.log("📁 ProjectContent projectId:", projectId);

  // Handlers de drag-and-drop
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    for (const file of files) {
      try {
        await uploadDocument(file);
        showSuccess("Upload concluído", `${file.name} foi enviado com sucesso.`);
      } catch (err: any) {
        console.error("[handleDrop] Upload failed:", err);
        showError(
          "Erro no upload",
          err.message || "Falha ao enviar arquivo. Tente novamente."
        );
      }
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    console.log("[FILE SELECT] ============================================");
    console.log("[FILE SELECT] Input change triggered");

    const files = e.target.files ? Array.from(e.target.files) : [];
    console.log("[FILE SELECT] Files selected:", files.length);

    for (const file of files) {
      console.log("[FILE SELECT] ------------------------------------------");
      console.log("[FILE SELECT] File name:", file.name);
      console.log("[FILE SELECT] File size:", file.size, "bytes");
      console.log("[FILE SELECT] File type:", file.type);
      console.log("[FILE SELECT] File lastModified:", new Date(file.lastModified).toISOString());
      console.log("[FILE SELECT] File webkitRelativePath:", file.webkitRelativePath || '(none)');

      // Log file content preview for text files
      if (file.type === 'text/plain' || file.name.endsWith('.txt')) {
        try {
          const reader = new FileReader();
          reader.onload = (e) => {
            const content = e.target?.result as string;
            console.log("[FILE SELECT] File content length:", content.length, "chars");
            console.log("[FILE SELECT] File content preview (first 200 chars):", content.substring(0, 200));
            console.log("[FILE SELECT] File content encoding check - contains Portuguese chars:", /[ãõáéíóúç]/.test(content));
          };
          reader.readAsText(file, 'UTF-8');
        } catch (readError) {
          console.error("[FILE SELECT] Error reading file content:", readError);
        }
      }

      try {
        console.log("[FILE SELECT] Starting upload for:", file.name);
        await uploadDocument(file);
        showSuccess("Upload concluído", `${file.name} foi enviado com sucesso.`);
      } catch (err: any) {
        console.error("[handleFileSelect] Upload failed:", err);
        showError(
          "Erro no upload",
          err.message || "Falha ao enviar arquivo. Tente novamente."
        );
      }
    }
  };

  // Log erro de documents se existir
  if (documentsError) {
    console.error("[ProjectPage] Erro ao carregar documents:", documentsError);
  }

  // LOADING: Bloquear enquanto carrega projeto OU documentos
  if (projectLoading || documentsLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (projectError) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Alert variant="destructive" className="max-w-md">
          <AlertDescription>Erro ao carregar projeto: {projectError}</AlertDescription>
        </Alert>
      </div>
    );
  }

  // Se projeto não existe após carregar, mostra mensagem
  if (!project) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Alert variant="destructive" className="max-w-md">
          <AlertDescription>
            Projeto não encontrado (ID: {projectId}).
            <Link href="/dashboard" className="underline ml-1">Voltar ao dashboard</Link>
          </AlertDescription>
        </Alert>
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
      <div className="container py-6 px-4 lg:px-8">
        {/* Page Header */}
        <div className="mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <Link href="/dashboard">
              <Button 
                variant="ghost" 
                size="sm" 
                className="text-muted-foreground hover:text-foreground -ml-2"
              >
                <ArrowLeft className="h-4 w-4 mr-1.5" />
                Voltar
              </Button>
            </Link>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 flex-wrap">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                  <FolderKanban className="h-5 w-5 text-primary" />
                </div>
                <div className="min-w-0">
                  <h1 className="text-xl sm:text-2xl font-bold tracking-tight truncate">
                    {project?.name || "Projeto"}
                  </h1>
                  <p className="text-sm text-muted-foreground truncate">
                    {project?.description || "Sem descrição"}
                  </p>
                </div>
              </div>
            </div>
            <Badge 
              variant="outline" 
              className="self-start sm:self-center capitalize bg-background"
            >
              {project?.status || "draft"}
            </Badge>
          </div>
        </div>

        <main>
        <Tabs defaultValue="documents" className="w-full">
          <TabsList className="mb-6">
            <TabsTrigger value="documents">Documentos</TabsTrigger>
            <TabsTrigger value="questions">Perguntas ({(documents || []).reduce((acc: number, d: Document) => acc + (d.question_count || 0), 0)})</TabsTrigger>
            <TabsTrigger value="answers">Respostas</TabsTrigger>
            <TabsTrigger value="settings">Configurações</TabsTrigger>
          </TabsList>

          <TabsContent value="documents" className="space-y-6">
            <Card
              className={`border-2 border-dashed transition-colors ${
                isDragging ? "border-primary bg-primary/5" : "border-muted"
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Upload className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-lg font-medium">Arraste arquivos aqui</p>
                <p className="text-sm text-muted-foreground mt-1">
                  ou clique para selecionar PDF, DOCX, XLSX, TXT
                </p>
                <input
                  type="file"
                  id="file-upload"
                  multiple
                  accept=".pdf,.docx,.xlsx,.txt"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <label htmlFor="file-upload">
                  <Button variant="outline" className="mt-4" asChild>
                    <span>
                      <Upload className="h-4 w-4 mr-2" />
                      Selecionar Arquivos
                    </span>
                  </Button>
                </label>
              </CardContent>
            </Card>

            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Documentos ({documents.length})</h3>
              {documents.length === 0 && (
                <Card>
                  <EmptyStateCompact
                    icon={FileText}
                    title="Nenhum documento ainda"
                    description="Faça upload do RFP ou questionário para começar o processamento."
                  />
                </Card>
              )}
              {documents.map((doc: Document) => (
                <Card key={doc.id} className="hover:bg-muted/50 transition-colors">
                  <CardContent className="flex items-center justify-between py-4">
                    <div className="flex items-center gap-4">
                      <FileText className="h-8 w-8 text-primary" />
                      <div>
                        <p className="font-medium">{doc.original_filename || doc.filename}</p>
                        <p className="text-sm text-muted-foreground">
                          {doc.file_type} • {new Date(doc.created_at).toLocaleDateString("pt-BR")}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      {doc.question_count && doc.question_count > 0 && (
                        <Badge variant="secondary">{doc.question_count} perguntas</Badge>
                      )}
                      {getStatusBadge(doc.status)}
                      {doc.status === "processed" ? (
                        <Link href={`/review/${doc.id}`}>
                          <Button variant="outline" size="sm">
                            Revisar
                          </Button>
                        </Link>
                      ) : (
                        <Button variant="outline" size="sm" disabled>
                          Revisar
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="questions">
            <Card>
              <CardHeader>
                <CardTitle>Perguntas Extraídas</CardTitle>
                <CardDescription>
                  Total de {documents.reduce((acc: number, d: Document) => acc + (d.question_count || 0), 0)} perguntas encontradas nos documentos
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">Selecione um documento processado para revisar as perguntas.</p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="answers">
            <Card>
              <CardHeader>
                <CardTitle>Respostas Geradas</CardTitle>
                <CardDescription>
                  Respostas sugeridas pela IA baseadas na base de conhecimento
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">As respostas serão geradas após o processamento dos documentos.</p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="settings">
            <Card>
              <CardHeader>
                <CardTitle>Configurações do Projeto</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">Configurações avançadas do projeto.</p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
        </main>
      </div>
    </AppShell>
  );
}
