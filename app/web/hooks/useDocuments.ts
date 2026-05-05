"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { documentsApi } from "@/lib/api/client";
import type { Document } from "@/types/api";

export function useDocuments(projectId: string) {
  const [state, setState] = useState<{
    documents: Document[];
    isLoading: boolean;
    error: string | null;
  }>({
    documents: [],
    isLoading: false,
    error: null,
  });

  // 🔴 REFS CRÍTICOS: Evitar loops e concorrência
  const isFetchingRef = useRef(false); // Evita múltiplos fetches simultâneos
  const lastFetchTimeRef = useRef(0); // Debounce de fetchs
  const uploadInProgressRef = useRef(false); // Pausa polling durante upload

  const fetchDocuments = useCallback(async (force = false) => {
    // PROTEÇÃO: Validar projectId
    if (!projectId || projectId.trim() === "" || projectId === "undefined" || projectId === "null") {
      console.log("[GUARD] projectId inválido - skip fetch:", projectId);
      return;
    }

    // 🔴 PROTEÇÃO: Evitar múltiplos fetches simultâneos (a menos que seja forçado)
    if (!force && isFetchingRef.current) {
      console.log("[GUARD] Fetch já em progresso, ignorando");
      return;
    }

    // 🔴 PROTEÇÃO: Debounce - mínimo 500ms entre fetchs
    const now = Date.now();
    if (!force && now - lastFetchTimeRef.current < 500) {
      console.log("[GUARD] Debounce: fetch muito recente");
      return;
    }

    isFetchingRef.current = true;
    lastFetchTimeRef.current = now;

    console.log("[FETCH] Iniciando fetch:", projectId);

    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await documentsApi.list(projectId);

      // CORREÇÃO: API retorna array direto OU { items: [...] }
      let docs: Document[] = [];
      const resp = response as any;
      if (Array.isArray(resp)) {
        docs = resp;
      } else if (resp && typeof resp === 'object' && Array.isArray(resp.items)) {
        docs = resp.items;
      }

      // 🔴 RASTREAMENTO CRÍTICO: Log do que foi recebido da API
      console.log("\n[TRACKING-FRONTEND] ============================================")
      console.log("[TRACKING-FRONTEND] event: DOCUMENTS_RECEIVED")
      console.log("[TRACKING-FRONTEND] count:", docs.length)
      docs.forEach(d => {
        console.log(`[TRACKING-FRONTEND] doc: id=${d.id} status=${d.status}`)
      })
      console.log("[TRACKING-FRONTEND] ============================================\n")

      // 🔴 LÓGICA PROTETIVA - NUNCA sobrescrever dados válidos com vazio
      setState((prev) => {
        // REGRA 1: Nunca sobrescrever dados válidos com vazio
        if (docs.length === 0 && prev.documents.length > 0) {
          console.log("[PROTECT] Ignorando resposta vazia - mantendo dados existentes");
          return {
            ...prev,
            isLoading: false,
          };
        }

        // 🔴 REGRA 2: Sempre aceitar dados não vazios
        if (docs.length > 0) {
          console.log("[UPDATE] Atualizando com", docs.length, "documentos");
          return {
            documents: docs,
            isLoading: false,
            error: null,
          };
        }

        // 🔴 REGRA 3: Primeira carga (permitir vazio)
        return {
          documents: docs,
          isLoading: false,
          error: null,
        };
      });
      
    } catch (error: any) {
      console.error("[FETCH] FAILED:", error.message);
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: error.message || "Failed to fetch documents",
      }));
    } finally {
      // 🔴 SEMPRE liberar o lock, mesmo em caso de erro
      isFetchingRef.current = false;
    }
  }, [projectId]);

  // EFEITO PRINCIPAL: Só executa quando projectId muda para valor válido
  useEffect(() => {
    if (!projectId || projectId.trim() === "" || projectId === "undefined" || projectId === "null") {
      console.log("[INIT] projectId inválido, resetando estado");
      setState({ documents: [], isLoading: false, error: null });
      return;
    }
    
    console.log("[INIT] projectId válido, fetch inicial:", projectId);
    fetchDocuments();
  }, [projectId, fetchDocuments]);

  // 🔴 VISIBILITY REFETCH TEMPORARIAMENTE DESATIVADO
  // useEffect(() => {
  //   const handleVisibilityChange = () => {
  //     if (document.visibilityState === "visible" && projectId && projectId.trim() !== "") {
  //       fetchDocuments();
  //     }
  //   };
  //   document.addEventListener("visibilitychange", handleVisibilityChange);
  //   return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  // }, [fetchDocuments, projectId]);

  // 🔴 POLLING TEMPORARIAMENTE DESATIVADO para investigação
  // useEffect(() => {
  //   if (uploadInProgressRef.current) {
  //     console.log("[POLL] Upload em progresso, polling pausado");
  //     return;
  //   }
  //   const pendingStatuses = ["pending", "uploaded", "extracting", "chunking", "indexing", "processing"];
  //   const hasPendingDocs = state.documents.some(
  //     (d) => pendingStatuses.includes(d.status)
  //   );
  //   if (!hasPendingDocs || !projectId) return;
  //   console.log("[POLL] Iniciando polling para documentos pendentes");
  //   const interval = setInterval(() => {
  //     if (!uploadInProgressRef.current) {
  //       fetchDocuments();
  //     }
  //   }, 3000);
  //   return () => clearInterval(interval);
  // }, [state.documents, fetchDocuments, projectId]);

  // REFETCH COM RETRY - usa fetchDocuments com delay
  const refetchWithRetry = useCallback(async (delay = 1500) => {
    console.log("[RETRY] Aguardando", delay, "ms antes do refetch");
    await new Promise(resolve => setTimeout(resolve, delay));
    // 🔴 Usar force=true para garantir que execute mesmo com debounce
    await fetchDocuments(true);
  }, [fetchDocuments]);

  const uploadDocument = useCallback(async (file: File, onProgress?: (progress: number) => void) => {
    if (!projectId || projectId.trim() === "") {
      throw new Error("ID do projeto não encontrado. Recarregue a página.");
    }

    // 🔴 MARCAR upload em progresso (pausa polling)
    uploadInProgressRef.current = true;
    console.log("[UPLOAD] Iniciando upload, polling pausado");

    try {
      console.log("==========================================");
      console.log("[UPLOAD] projectId usado no upload:", projectId);
      console.log("[UPLOAD] file:", file.name, "size:", file.size, "type:", file.type);
      console.log("==========================================");

      const newDoc = await documentsApi.upload(projectId, file, onProgress);
      // 🔴 RASTREAMENTO CRÍTICO: Upload completado
      console.log("\n[TRACKING-FRONTEND] ============================================")
      console.log("[TRACKING-FRONTEND] event: UPLOAD_SUCCESS")
      console.log("[TRACKING-FRONTEND] document_id:", newDoc.id)
      console.log("[TRACKING-FRONTEND] status:", newDoc.status)
      console.log("[TRACKING-FRONTEND] timestamp:", new Date().toISOString())
      console.log("[TRACKING-FRONTEND] ============================================\n")

      // Adiciona ao estado local IMEDIATAMENTE
      setState((prev) => {
        const updated = {
          ...prev,
          documents: [...prev.documents, newDoc],
        };
        console.log("[UPLOAD] Estado local atualizado:", updated.documents.length, "documentos");
        return updated;
      });

      // 🔴 REFETCH APÓS UPLOAD TEMPORARIAMENTE DESATIVADO para investigação
      // console.log("[SYNC] Aguardando 1500ms antes de sincronizar...");
      // await refetchWithRetry(1500);
      // console.log("[SYNC] Sincronização completada");
      console.log("[SYNC] Refetch automático DESATIVADO - use refresh manual");

      return newDoc;
    } catch (error: any) {
      console.error("[UPLOAD] FAILED:", error);
      throw error;
    } finally {
      // 🔴 SEMPRE liberar o flag de upload, mesmo em erro
      uploadInProgressRef.current = false;
      console.log("[UPLOAD] Upload finalizado, polling liberado");
    }
  }, [projectId, refetchWithRetry]);

  const processDocument = useCallback(async (documentId: string) => {
    try {
      const result = await documentsApi.process(documentId);
      // Update document status in list
      setState((prev) => ({
        ...prev,
        documents: prev.documents.map((d) =>
          d.id === documentId ? { ...d, status: "extracting" } : d
        ),
      }));
      return result;
    } catch (error: any) {
      throw error;
    }
  }, []);

  const deleteDocument = useCallback(async (documentId: string) => {
    try {
      await documentsApi.delete(documentId);
      setState((prev) => ({
        ...prev,
        documents: prev.documents.filter((d) => d.id !== documentId),
      }));
    } catch (error: any) {
      throw error;
    }
  }, []);

  return {
    ...state,
    refetch: fetchDocuments,
    uploadDocument,
    processDocument,
    deleteDocument,
  };
}

export function useDocument(documentId: string) {
  const [state, setState] = useState<{
    document: Document | null;
    isLoading: boolean;
    error: string | null;
  }>({
    document: null,
    isLoading: true,
    error: null,
  });

  const fetchDocument = useCallback(async () => {
    if (!documentId) return;
    
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    
    try {
      const document = await documentsApi.get(documentId);
      setState({ document, isLoading: false, error: null });
    } catch (error: any) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: error.message || "Failed to fetch document",
      }));
    }
  }, [documentId]);

  useEffect(() => {
    fetchDocument();
  }, [fetchDocument]);

  return {
    ...state,
    refetch: fetchDocument,
  };
}
