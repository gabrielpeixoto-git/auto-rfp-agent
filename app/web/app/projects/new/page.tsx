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
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ArrowLeft, Plus, Loader2, FolderPlus } from "lucide-react";
import { projectsApi } from "@/lib/api/client";
import { useAuth } from "@/hooks/useAuth";
import { AuthGuard } from "@/components/AuthGuard";
import { AppShell } from "@/components/AppShell";

// Componente protegido que só renderiza quando autenticado
function NewProjectContent() {
  const router = useRouter();
  const { logout, user } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    project_type: "",
    description: "",
    deadline: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      if (!formData.name.trim()) {
        throw new Error("Nome do projeto é obrigatório");
      }

      const project = await projectsApi.create({
        name: formData.name,
        description: formData.description,
        project_type: formData.project_type || "rfp",
        deadline: formData.deadline || undefined,
      });

      router.push(`/projects/${project.id}`);
    } catch (err: any) {
      setError(err.message || "Erro ao criar projeto. Tente novamente.");
      setIsLoading(false);
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
      <div className="container max-w-2xl py-6 px-4 lg:px-8">
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
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                <FolderPlus className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h1 className="text-xl sm:text-2xl font-bold tracking-tight">
                  Novo Projeto
                </h1>
                <p className="text-sm text-muted-foreground">
                  Crie um novo projeto de RFP/RFI
                </p>
              </div>
            </div>
          </div>
        </div>

        <Card className="border-border/50 shadow-sm">
          <CardHeader className="space-y-1">
            <CardTitle className="text-xl">Detalhes do Projeto</CardTitle>
            <CardDescription>
              Preencha as informações para começar a processar seu documento
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {error && (
                <Alert variant="destructive" className="border-destructive/20">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                <Label htmlFor="name">Nome do Projeto *</Label>
                <Input
                  id="name"
                  placeholder="Ex: RFP Acme Corporation 2024"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="type">Tipo de Documento</Label>
                <Select
                  value={formData.project_type}
                  onValueChange={(value) => setFormData({ ...formData, project_type: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Selecione o tipo" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="rfp">RFP (Request for Proposal)</SelectItem>
                    <SelectItem value="rfi">RFI (Request for Information)</SelectItem>
                    <SelectItem value="ddq">DDQ (Due Diligence Questionnaire)</SelectItem>
                    <SelectItem value="security">Security Questionnaire</SelectItem>
                    <SelectItem value="other">Outro</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Descrição</Label>
                <Textarea
                  id="description"
                  placeholder="Descreva o objetivo deste projeto..."
                  rows={4}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="deadline">Data Limite (opcional)</Label>
                <Input
                  id="deadline"
                  type="date"
                  value={formData.deadline}
                  onChange={(e) => setFormData({ ...formData, deadline: e.target.value })}
                />
              </div>

              <div className="flex flex-col sm:flex-row gap-3 pt-4">
                <Link href="/dashboard" className="sm:flex-1">
                  <Button 
                    variant="outline" 
                    className="w-full" 
                    type="button"
                  >
                    Cancelar
                  </Button>
                </Link>
                <Button 
                  className="sm:flex-1 bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary shadow-lg shadow-primary/25 transition-all duration-200" 
                  type="submit" 
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Criando...
                    </>
                  ) : (
                    <>
                      <Plus className="h-4 w-4 mr-2" />
                      Criar Projeto
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

// Exporta página envolvida com AuthGuard
export default function NewProjectPage() {
  return (
    <AuthGuard>
      <NewProjectContent />
    </AuthGuard>
  );
}
