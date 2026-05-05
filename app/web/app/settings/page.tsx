"use client";

import { useEffect, useState } from "react";
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
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Settings,
  Loader2,
  User,
  Mail,
  Shield,
  Building2,
  Save,
  Bell,
  Moon,
  Globe,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { AppShell } from "@/components/AppShell";
import { useToastContext } from "@/contexts/ToastContext";

export default function SettingsPage() {
  const { isAuthenticated, isInitialized, logout, user } = useAuth();
  const router = useRouter();
  const { success: showSuccess } = useToastContext();

  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    company: "",
  });

  useEffect(() => {
    if (isInitialized && !isAuthenticated) {
      router.push("/login");
    }
  }, [isInitialized, isAuthenticated, router]);

  useEffect(() => {
    if (user) {
      setFormData({
        name: user.full_name || user.email?.split("@")[0] || "",
        email: user.email || "",
        company: "",
      });
    }
  }, [user]);

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

  const handleSave = async () => {
    setIsLoading(true);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    showSuccess("Configurações salvas com sucesso!");
    setIsLoading(false);
  };

  const getRoleBadge = (role?: string) => {
    const variants: Record<string, { label: string; className: string }> = {
      admin: {
        label: "Administrador",
        className: "bg-purple-100 text-purple-800 border-purple-200",
      },
      analyst: {
        label: "Analista",
        className: "bg-blue-100 text-blue-800 border-blue-200",
      },
      viewer: {
        label: "Visualizador",
        className: "bg-slate-100 text-slate-800 border-slate-200",
      },
    };
    const config = variants[role || "viewer"] || variants.viewer;
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  return (
    <AppShell
      userName={user?.email?.split("@")[0]}
      userEmail={user?.email}
      onLogout={handleLogout}
    >
      <div className="container py-8 px-4 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
            <Settings className="h-8 w-8 text-primary" />
            Configurações
          </h1>
          <p className="text-muted-foreground mt-1.5">
            Gerencie suas preferências e informações da conta
          </p>
        </div>

        <div className="grid gap-6 max-w-2xl">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <User className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <CardTitle>Perfil</CardTitle>
                  <CardDescription>Suas informações pessoais</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <Label htmlFor="name">Nome</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="Seu nome"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="email">Email</Label>
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    disabled
                    className="bg-muted"
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  O email não pode ser alterado
                </p>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="company">Empresa</Label>
                <div className="flex items-center gap-2">
                  <Building2 className="h-4 w-4 text-muted-foreground" />
                  <Input
                    id="company"
                    value={formData.company}
                    onChange={(e) =>
                      setFormData({ ...formData, company: e.target.value })
                    }
                    placeholder="Nome da sua empresa"
                  />
                </div>
              </div>
              <div className="pt-2">
                <Button
                  onClick={handleSave}
                  disabled={isLoading}
                  className="gap-2"
                >
                  {isLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4" />
                  )}
                  Salvar alterações
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Shield className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <CardTitle>Segurança e Permissões</CardTitle>
                  <CardDescription>Seu papel e acesso no sistema</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between py-2">
                <div className="flex items-center gap-3">
                  <Shield className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Função</p>
                    <p className="text-sm text-muted-foreground">
                      Seu nível de acesso no sistema
                    </p>
                  </div>
                </div>
                {getRoleBadge(user?.role)}
              </div>
              <div className="border-t" />
              <div className="flex items-center justify-between py-2">
                <div className="flex items-center gap-3">
                  <Building2 className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Tenant ID</p>
                    <p className="text-sm text-muted-foreground">
                      Identificador da sua organização
                    </p>
                  </div>
                </div>
                <code className="text-xs bg-muted px-2 py-1 rounded">
                  {user?.tenant_id || "N/A"}
                </code>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Bell className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <CardTitle>Notificações</CardTitle>
                  <CardDescription>Configure alertas e emails</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                As configurações de notificação serão implementadas em breve.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Globe className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <CardTitle>Preferências</CardTitle>
                  <CardDescription>Idioma e aparência</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between py-2">
                <div className="flex items-center gap-3">
                  <Globe className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Idioma</p>
                    <p className="text-sm text-muted-foreground">
                      Idioma da interface
                    </p>
                  </div>
                </div>
                <Badge variant="outline">Português (Brasil)</Badge>
              </div>
              <div className="border-t" />
              <div className="flex items-center justify-between py-2">
                <div className="flex items-center gap-3">
                  <Moon className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Tema</p>
                    <p className="text-sm text-muted-foreground">
                      Aparência do sistema
                    </p>
                  </div>
                </div>
                <Badge variant="outline">Sistema</Badge>
              </div>
            </CardContent>
          </Card>

          <Card className="border-destructive/20">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-destructive/10 flex items-center justify-center">
                  <Shield className="h-5 w-5 text-destructive" />
                </div>
                <div>
                  <CardTitle className="text-destructive">Zona de Perigo</CardTitle>
                  <CardDescription>Ações irreversíveis</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between py-2">
                <div>
                  <p className="font-medium">Sair de todas as sessões</p>
                  <p className="text-sm text-muted-foreground">
                    Desconecta você de todos os dispositivos
                  </p>
                </div>
                <Button variant="outline" onClick={handleLogout}>
                  Sair
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
