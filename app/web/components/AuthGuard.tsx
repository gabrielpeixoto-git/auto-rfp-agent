"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { Loader2 } from "lucide-react";

interface AuthGuardProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

/**
 * AuthGuard - Componente de proteção de rotas
 *
 * Garante que apenas usuários autenticados acessem o conteúdo.
 * Mostra loading enquanto verifica autenticação.
 * Redireciona para login apenas quando a verificação terminar.
 */
export function AuthGuard({ children, fallback }: AuthGuardProps) {
  const { isAuthenticated, isInitialized } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Só redireciona quando a verificação inicial de auth terminar (isInitialized = true)
    // e o usuário não estiver autenticado
    if (isInitialized && !isAuthenticated) {
      console.log("[AuthGuard] Usuário não autenticado, redirecionando para login");
      router.push("/login");
    }
  }, [isInitialized, isAuthenticated, router]);

  // Enquanto verifica autenticação (não inicializado), mostra loading
  if (!isInitialized) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Se não está autenticado, não renderiza nada (redirect vai acontecer via useEffect)
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Usuário autenticado, renderiza o conteúdo
  return <>{children}</>;
}
