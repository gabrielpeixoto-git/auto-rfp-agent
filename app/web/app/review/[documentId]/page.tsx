"use client";

import { useState, useMemo, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ArrowLeft,
  Save,
  CheckCircle,
  Clock,
  AlertCircle,
  Search,
  FileDown,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Loader2,
  ArrowUpDown,
  Filter,
  X,
} from "lucide-react";
import { useQuestions } from "@/hooks/useQuestions";
import { useAuth } from "@/hooks/useAuth";
import { exportApi } from "@/lib/api/client";
import { useToastContext } from "@/contexts/ToastContext";
import { ReviewSkeleton } from "@/components/ReviewSkeleton";
import { EmptyState } from "@/components/EmptyState";
import { AuthGuard } from "@/components/AuthGuard";
import { AppShell } from "@/components/AppShell";
import type { Question, Answer } from "@/types/api";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

// Extended type for filtered questions with original index
type QuestionWithIndex = Question & { originalIndex: number };

const getCategoryBadge = (category: string) => {
  const colors: Record<string, string> = {
    security: "bg-red-100 text-red-800",
    technical: "bg-blue-100 text-blue-800",
    general: "bg-gray-100 text-gray-800",
    compliance: "bg-green-100 text-green-800",
  };
  return (
    <Badge className={colors[category] || colors.general}>
      {category.charAt(0).toUpperCase() + category.slice(1)}
    </Badge>
  );
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case "approved":
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    case "reviewed":
      return <Clock className="h-5 w-5 text-yellow-500" />;
    default:
      return <AlertCircle className="h-5 w-5 text-gray-400" />;
  }
};

// Página pública exporta componente envolvido com AuthGuard
export default function ReviewPage({ params }: { params: { documentId: string } }) {
  return (
    <AuthGuard>
      <ReviewPageContent params={params} />
    </AuthGuard>
  );
}

// Componente interno protegido
function ReviewPageContent({ params }: { params: { documentId: string } }) {
  // ==========================================
  // TODOS OS HOOKS PRIMEIRO - ordem estável em todos os renders
  // ==========================================
  
  // Hooks de estado primeiro
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<"default" | "confidence" | "category" | "alphabetical">("default");
  const [editedAnswer, setEditedAnswer] = useState("");
  const [generatingId, setGeneratingId] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  
  // Hooks de contexto/auth sempre no topo - NUNCA depois de early returns!
  const { logout, user } = useAuth();
  const { success, error: showError } = useToastContext();

  // Verificar se documentId é válido (não deve ser '[documentId]' ou vazio)
  const isValidId = params.documentId &&
                    params.documentId !== '[documentId]' &&
                    params.documentId !== 'documentId' &&
                    params.documentId.length > 5;

  const { questions, isLoading, error, refetch, generateAnswer, updateAnswer, approveAnswer } = useQuestions(
    isValidId ? params.documentId : ''
  );

  // Persist filter state - sempre executar, não condicionalmente
  useEffect(() => {
    if (!isValidId) return;
    const savedFilter = localStorage.getItem(`review-filter-${params.documentId}`);
    const savedSort = localStorage.getItem(`review-sort-${params.documentId}`);
    if (savedFilter) setFilter(savedFilter);
    if (savedSort) setSortBy(savedSort as typeof sortBy);
  }, [params.documentId, isValidId]);

  useEffect(() => {
    if (!isValidId) return;
    localStorage.setItem(`review-filter-${params.documentId}`, filter);
  }, [filter, params.documentId, isValidId]);

  useEffect(() => {
    if (!isValidId) return;
    localStorage.setItem(`review-sort-${params.documentId}`, sortBy);
  }, [sortBy, params.documentId, isValidId]);

  // Mostrar erro se ID for inválido - após todos os hooks
  if (!isValidId) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-6 w-6 text-red-500" />
              ID do Documento Inválido
            </CardTitle>
            <CardDescription>
              Você está tentando acessar a página com um ID de documento inválido.
              <br /><br />
              <strong>URL correta:</strong> <code>/review/abc123-def456</code>
              <br />
              <strong>URL incorreta:</strong> <code>/review/[documentId]</code>
            </CardDescription>
          </CardHeader>
          <CardFooter>
            <Link href="/dashboard">
              <Button>
                <ArrowLeft className="h-4 w-4 mr-2" />
                Voltar ao Dashboard
              </Button>
            </Link>
          </CardFooter>
        </Card>
      </div>
    );
  }
  
  // Get projectId from the first question's project_id
  const projectId = questions.length > 0 ? questions[0].project_id : null;

  const totalQuestions = questions.length;
  const reviewedCount = questions.filter((q: Question) => q.status !== "pending").length;
  const approvedCount = questions.filter((q: Question) => q.status === "approved").length;

  // Calculate filter counts for badges
  const filterCounts = useMemo(() => {
    const counts = {
      all: questions.length,
      security: 0,
      technical: 0,
      compliance: 0,
      general: 0,
      pending: 0,
      reviewed: 0,
      approved: 0,
    };
    questions.forEach((q) => {
      if (q.category && counts[q.category as keyof typeof counts] !== undefined) {
        counts[q.category as keyof typeof counts]++;
      }
      if (q.status && counts[q.status as keyof typeof counts] !== undefined) {
        counts[q.status as keyof typeof counts]++;
      }
    });
    return counts;
  }, [questions]);

  // Filter and sort questions while preserving original index
  const filteredQuestions = useMemo<QuestionWithIndex[]>(() => {
    let filtered = questions
      .map((q, originalIndex): QuestionWithIndex => ({ ...q, originalIndex }))
      .filter((q) => {
        const matchesFilter = filter === "all" || q.category === filter || q.status === filter;
        const matchesSearch = q.question_text.toLowerCase().includes(search.toLowerCase());
        return matchesFilter && matchesSearch;
      });

    // Apply sorting
    switch (sortBy) {
      case "confidence":
        filtered.sort((a, b) => (b.answer?.confidence || 0) - (a.answer?.confidence || 0));
        break;
      case "alphabetical":
        filtered.sort((a, b) => a.question_text.localeCompare(b.question_text));
        break;
      case "category":
        filtered.sort((a, b) => a.category.localeCompare(b.category));
        break;
      default:
        // Keep original order
        break;
    }

    return filtered;
  }, [questions, filter, search, sortBy]);

  // Find the current index in the filtered list
  const currentFilteredIndex = useMemo(() => {
    return filteredQuestions.findIndex((q) => q.originalIndex === currentIndex);
  }, [filteredQuestions, currentIndex]);

  const currentQuestion: QuestionWithIndex | null = filteredQuestions.length > 0 
    ? filteredQuestions[currentFilteredIndex >= 0 ? currentFilteredIndex : 0]
    : null;

  if (isLoading) {
    return <ReviewSkeleton />;
  }

  if (error) {
    // Mostrar erro técnico real para facilitar diagnóstico
    let errorTitle = "Erro ao carregar documento";
    let errorDescription = error;
    let actionLabel = "Voltar ao Dashboard";
    let actionHref = "/dashboard";
    let showTechnicalDetails = true;

    if (error.includes("not found") || error.includes("não encontrado") || error.includes("404")) {
      errorTitle = "Documento não encontrado";
      errorDescription = "O documento solicitado não existe ou foi removido. Verifique se o ID está correto ou se o documento ainda está disponível.";
      showTechnicalDetails = false;
    } else if (error.includes("unauthorized") || error.includes("não autorizado") || error.includes("403")) {
      errorTitle = "Acesso negado";
      errorDescription = "Você não tem permissão para acessar este documento. Verifique se está logado com a conta correta.";
      showTechnicalDetails = false;
    } else if (error.includes("500") || error.includes("Internal Server Error")) {
      errorTitle = "Erro interno do servidor";
      errorDescription = "O servidor encontrou um erro inesperado. Os detalhes técnicos abaixo podem ajudar na investigação.";
      actionLabel = "Tentar Novamente";
      showTechnicalDetails = true;
    }

    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="max-w-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-6 w-6" />
              {errorTitle}
            </CardTitle>
            <CardDescription>{errorDescription}</CardDescription>
          </CardHeader>
          {showTechnicalDetails && (
            <CardContent>
              <div className="bg-muted rounded-md p-3">
                <p className="text-xs font-semibold text-muted-foreground mb-1">Detalhes técnicos:</p>
                <code className="text-xs break-all text-red-600">{error}</code>
              </div>
            </CardContent>
          )}
          <CardFooter>
            <Link href={actionHref}>
              <Button>
                <ArrowLeft className="h-4 w-4 mr-2" />
                {actionLabel}
              </Button>
            </Link>
          </CardFooter>
        </Card>
      </div>
    );
  }

  if (questions.length === 0) {
    return (
      <div className="min-h-screen bg-background">
        <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="container flex h-16 items-center gap-4">
            <Link href="/dashboard">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Voltar
              </Button>
            </Link>
            <span className="text-lg font-semibold">Revisão de Respostas</span>
          </div>
        </header>
        <main className="container py-8">
          <EmptyState
            icon={Search}
            title="Nenhuma pergunta encontrada"
            description="O documento ainda está sendo processado pela IA ou não contém perguntas detectáveis. Verifique o status do documento na página do projeto e aguarde alguns instantes."
            actionLabel="Ver Projeto"
            actionHref={`/projects/${projectId || "dashboard"}`}
          />
        </main>
      </div>
    );
  }

  const handlePrevious = () => {
    if (currentFilteredIndex > 0) {
      const prevQuestion = filteredQuestions[currentFilteredIndex - 1];
      setCurrentIndex(prevQuestion.originalIndex);
    }
  };

  const handleNext = () => {
    if (currentFilteredIndex < filteredQuestions.length - 1) {
      const nextQuestion = filteredQuestions[currentFilteredIndex + 1];
      setCurrentIndex(nextQuestion.originalIndex);
    }
  };

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
            <Link href={`/projects/${projectId || "dashboard"}`}>
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
                  <Sparkles className="h-5 w-5 text-primary" />
                </div>
                <div className="min-w-0">
                  <h1 className="text-xl sm:text-2xl font-bold tracking-tight truncate">
                    Revisar Perguntas
                  </h1>
                  <p className="text-sm text-muted-foreground">
                    {approvedCount} de {totalQuestions} aprovadas
                  </p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 self-start sm:self-center">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" disabled={exporting || !projectId}>
                  {exporting ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <FileDown className="h-4 w-4 mr-2" />
                  )}
                  {exporting ? "Exportando..." : "Exportar"}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onClick={async () => {
                    if (!projectId) return;
                    setExporting(true);
                    try {
                      const response = await exportApi.downloadPdf(projectId);
                      if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement("a");
                        a.href = url;
                        a.download = `rfp_response_${new Date().toISOString().split("T")[0]}.pdf`;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                        success("PDF exportado!", "O arquivo PDF foi baixado com sucesso.");
                      } else {
                        showError("Erro na exportação", "Não foi possível exportar o PDF.");
                      }
                    } catch (e) {
                      console.error("Export PDF failed:", e);
                      showError("Erro na exportação", "Falha ao exportar para PDF.");
                    } finally {
                      setExporting(false);
                    }
                  }}
                >
                  Exportar como PDF
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={async () => {
                    if (!projectId) return;
                    setExporting(true);
                    try {
                      const response = await exportApi.downloadWord(projectId);
                      if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement("a");
                        a.href = url;
                        a.download = `rfp_response_${new Date().toISOString().split("T")[0]}.docx`;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                        success("Word exportado!", "O documento Word foi baixado com sucesso.");
                      } else {
                        showError("Erro na exportação", "Não foi possível exportar o Word.");
                      }
                    } catch (e) {
                      console.error("Export Word failed:", e);
                      showError("Erro na exportação", "Falha ao exportar para Word.");
                    } finally {
                      setExporting(false);
                    }
                  }}
                >
                  Exportar como Word
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={async () => {
                    if (!projectId) return;
                    setExporting(true);
                    try {
                      const response = await exportApi.downloadExcel(projectId);
                      if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement("a");
                        a.href = url;
                        a.download = `rfp_response_${new Date().toISOString().split("T")[0]}.xlsx`;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                        success("Excel exportado!", "A planilha Excel foi baixada com sucesso.");
                      } else {
                        showError("Erro na exportação", "Não foi possível exportar o Excel.");
                      }
                    } catch (e) {
                      console.error("Export Excel failed:", e);
                      showError("Erro na exportação", "Falha ao exportar para Excel.");
                    } finally {
                      setExporting(false);
                    }
                  }}
                >
                  Exportar como Excel
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>

      <div className="py-6">
        <div className="grid grid-cols-12 gap-6">
          {/* Sidebar - Question List */}
          <div className="col-span-4 space-y-4">
            <Card>
              <CardHeader className="pb-3 space-y-3">
                {/* Search */}
                <div className="flex items-center gap-2">
                  <Search className="h-4 w-4 text-muted-foreground shrink-0" />
                  <Input
                    placeholder="Buscar perguntas..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="h-8"
                  />
                  {search && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0 shrink-0"
                      onClick={() => setSearch("")}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
                
                {/* Filter by Category/Status */}
                <div className="flex items-center gap-2">
                  <Filter className="h-4 w-4 text-muted-foreground shrink-0" />
                  <Select value={filter} onValueChange={setFilter}>
                    <SelectTrigger className="h-8 flex-1">
                      <SelectValue placeholder="Filtrar por..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">
                        <span className="flex items-center justify-between w-full">
                          <span>Todas</span>
                          <Badge variant="secondary" className="ml-2 text-xs">{filterCounts.all}</Badge>
                        </span>
                      </SelectItem>
                      <SelectItem value="security">
                        <span className="flex items-center justify-between w-full">
                          <span>Segurança</span>
                          <Badge variant="secondary" className="ml-2 text-xs">{filterCounts.security}</Badge>
                        </span>
                      </SelectItem>
                      <SelectItem value="technical">
                        <span className="flex items-center justify-between w-full">
                          <span>Técnico</span>
                          <Badge variant="secondary" className="ml-2 text-xs">{filterCounts.technical}</Badge>
                        </span>
                      </SelectItem>
                      <SelectItem value="compliance">
                        <span className="flex items-center justify-between w-full">
                          <span>Compliance</span>
                          <Badge variant="secondary" className="ml-2 text-xs">{filterCounts.compliance}</Badge>
                        </span>
                      </SelectItem>
                      <SelectItem value="general">
                        <span className="flex items-center justify-between w-full">
                          <span>Geral</span>
                          <Badge variant="secondary" className="ml-2 text-xs">{filterCounts.general}</Badge>
                        </span>
                      </SelectItem>
                      <SelectItem value="pending">
                        <span className="flex items-center justify-between w-full">
                          <span>Pendentes</span>
                          <Badge variant="secondary" className="ml-2 text-xs">{filterCounts.pending}</Badge>
                        </span>
                      </SelectItem>
                      <SelectItem value="reviewed">
                        <span className="flex items-center justify-between w-full">
                          <span>Revisadas</span>
                          <Badge variant="secondary" className="ml-2 text-xs">{filterCounts.reviewed}</Badge>
                        </span>
                      </SelectItem>
                      <SelectItem value="approved">
                        <span className="flex items-center justify-between w-full">
                          <span>Aprovadas</span>
                          <Badge variant="secondary" className="ml-2 text-xs">{filterCounts.approved}</Badge>
                        </span>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                {/* Sort */}
                <div className="flex items-center gap-2">
                  <ArrowUpDown className="h-4 w-4 text-muted-foreground shrink-0" />
                  <Select value={sortBy} onValueChange={(v) => setSortBy(v as typeof sortBy)}>
                    <SelectTrigger className="h-8 flex-1">
                      <SelectValue placeholder="Ordenar por..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="default">Ordem Original</SelectItem>
                      <SelectItem value="confidence">Maior Confiança</SelectItem>
                      <SelectItem value="alphabetical">Ordem Alfabética</SelectItem>
                      <SelectItem value="category">Categoria</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                {/* Results count */}
                <div className="text-xs text-muted-foreground pt-1 border-t">
                  Mostrando {filteredQuestions.length} de {totalQuestions} perguntas
                  {(filter !== "all" || search || sortBy !== "default") && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-auto p-0 ml-2 text-xs underline"
                      onClick={() => {
                        setFilter("all");
                        setSearch("");
                        setSortBy("default");
                      }}
                    >
                      Limpar filtros
                    </Button>
                  )}
                </div>
              </CardHeader>
            </Card>

            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {filteredQuestions.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground text-sm">
                  <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>Nenhuma pergunta corresponde aos filtros.</p>
                </div>
              ) : (
                filteredQuestions.map((q) => (
                  <Card
                    key={q.id}
                    className={`cursor-pointer transition-colors ${
                      currentQuestion?.id === q.id ? "border-primary bg-primary/5" : "hover:bg-muted/50"
                    }`}
                    onClick={() => setCurrentIndex(q.originalIndex)}
                  >
                    <CardContent className="p-3">
                      <div className="flex items-start gap-2">
                        {getStatusIcon(q.status)}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium line-clamp-2">{q.question_text}</p>
                          <div className="flex items-center gap-2 mt-2">
                            {getCategoryBadge(q.category)}
                            <span className="text-xs text-muted-foreground">
                              {Math.round((q.answer?.confidence || 0) * 100)}% confiança
                            </span>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </div>

          {/* Main Content - Question Review */}
          <div className="col-span-8 space-y-4">
            {!currentQuestion ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <p className="text-muted-foreground">Nenhuma pergunta selecionada.</p>
                </CardContent>
              </Card>
            ) : (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {getCategoryBadge(currentQuestion.category)}
                    <span className="text-sm text-muted-foreground">
                      Pergunta {currentFilteredIndex + 1} de {filteredQuestions.length}
                      {(filter !== "all" || search) && ` (filtro ativo)`}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handlePrevious}
                      disabled={currentFilteredIndex <= 0}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleNext}
                      disabled={currentFilteredIndex >= filteredQuestions.length - 1}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <CardTitle className="text-lg mt-2">{currentQuestion.question_text}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {currentQuestion.answer ? (
                  <>
                    <div className="bg-muted/50 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <Sparkles className="h-4 w-4 text-primary" />
                        <span className="text-sm font-medium">Resposta Sugerida pela IA</span>
                        <Badge variant="outline" className="ml-auto">
                          {Math.round((currentQuestion.answer?.confidence || 0) * 100)}% confiança
                        </Badge>
                      </div>
                      <Textarea
                        value={editedAnswer || currentQuestion.answer?.suggested_text || ""}
                        onChange={(e) => setEditedAnswer(e.target.value)}
                        className="min-h-[120px]"
                        placeholder="Edite a resposta sugerida..."
                      />
                    </div>

                    {currentQuestion.answer?.citations && currentQuestion.answer.citations.length > 0 && (
                      <div>
                        <p className="text-sm font-medium mb-2">Fontes:</p>
                        <div className="flex flex-wrap gap-2">
                          {currentQuestion.answer.citations.map((cite, idx) => (
                            <Badge key={idx} variant="secondary">
                              {cite}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <AlertCircle className="h-8 w-8 mx-auto mb-2" />
                    <p>Nenhuma resposta sugerida para esta pergunta.</p>
                    <Button 
                      variant="outline" 
                      className="mt-4"
                      onClick={async () => {
                        if (!currentQuestion) return;
                        console.log("[DEBUG] Iniciando geração de resposta para:", currentQuestion.id);
                        setGeneratingId(currentQuestion.id);
                        try {
                          const result = await generateAnswer(currentQuestion.id);
                          console.log("[DEBUG] Resposta gerada:", result);
                          await refetch();
                          setEditedAnswer("");
                          success("Resposta gerada com sucesso!", "A IA gerou uma resposta para esta pergunta.");
                        } catch (e) {
                          console.error("[DEBUG] Erro ao gerar resposta:", e);
                          const errorMsg = e instanceof Error ? e.message : "Erro desconhecido";
                          console.error("[DEBUG] Mensagem de erro:", errorMsg);
                          showError("Erro ao gerar resposta", `Detalhes: ${errorMsg}. Verifique se o Ollama está rodando.`);
                        } finally {
                          setGeneratingId(null);
                        }
                      }}
                      disabled={generatingId === currentQuestion.id}
                    >
                      {generatingId === currentQuestion.id ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <Sparkles className="h-4 w-4 mr-2" />
                      )}
                      {generatingId === currentQuestion.id ? "Gerando..." : "Gerar Resposta"}
                    </Button>
                  </div>
                )}
              </CardContent>
              <CardFooter className="flex justify-between border-t pt-4">
                <Button 
                  variant="outline"
                  onClick={handleNext}
                  disabled={currentFilteredIndex >= filteredQuestions.length - 1}
                >
                  Próxima
                </Button>
                <div className="flex gap-2">
                  <Button 
                    variant="secondary"
                    onClick={async () => {
                      if (!currentQuestion) return;
                      setSavingId(currentQuestion.id);
                      try {
                        const finalText = editedAnswer || currentQuestion.answer?.suggested_text || "";
                        await updateAnswer(currentQuestion.id, {
                          final_text: finalText,
                          status: "reviewed",
                        });
                        await refetch();
                        success("Rascunho salvo!", "Sua edição foi salva com sucesso.");
                      } catch (e) {
                        console.error("Failed to save draft:", e);
                        showError("Erro ao salvar", "Não foi possível salvar o rascunho.");
                      } finally {
                        setSavingId(null);
                      }
                    }}
                    disabled={savingId === currentQuestion.id || approvingId === currentQuestion.id}
                  >
                    {savingId === currentQuestion.id ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Save className="h-4 w-4 mr-2" />
                    )}
                    Salvar Rascunho
                  </Button>
                  <Button
                    onClick={async () => {
                      if (!currentQuestion) return;
                      setApprovingId(currentQuestion.id);
                      try {
                        const finalText = editedAnswer || currentQuestion.answer?.suggested_text || "";
                        // First update the answer text if edited
                        if (editedAnswer && editedAnswer !== currentQuestion.answer?.suggested_text) {
                          await updateAnswer(currentQuestion.id, {
                            final_text: finalText,
                            status: "reviewed",
                          });
                        }
                        // Then approve
                        await approveAnswer(currentQuestion.id);
                        await refetch();
                        setEditedAnswer("");
                        success("Resposta aprovada!", "A resposta foi marcada como aprovada.");
                      } catch (e) {
                        console.error("Failed to approve answer:", e);
                        showError("Erro ao aprovar", "Não foi possível aprovar a resposta.");
                      } finally {
                        setApprovingId(null);
                      }
                    }}
                    disabled={savingId === currentQuestion.id || approvingId === currentQuestion.id || !currentQuestion.answer}
                  >
                    {approvingId === currentQuestion.id ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <CheckCircle className="h-4 w-4 mr-2" />
                    )}
                    Aprovar Resposta
                  </Button>
                </div>
              </CardFooter>
            </Card>
            )}
          </div>
        </div>
      </div>
    </div>
    </AppShell>
  );
}
