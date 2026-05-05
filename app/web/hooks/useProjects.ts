"use client";

import { useState, useEffect, useCallback } from "react";
import { projectsApi } from "@/lib/api/client";
import type { Project } from "@/types/api";

interface ProjectsState {
  projects: Project[];
  isLoading: boolean;
  error: string | null;
}

// Input sanitization helper - prevents XSS in user inputs
function sanitizeInput(input: string): string {
  // Remove potentially dangerous characters while preserving basic punctuation
  return input
    .replace(/[<>]/g, '') // Remove < and > to prevent HTML tags
    .trim();
}

export function useProjects() {
  const [state, setState] = useState<ProjectsState>({
    projects: [],
    isLoading: true,
    error: null,
  });

  const fetchProjects = useCallback(async () => {
    const token = localStorage.getItem("token");
    console.log("useProjects - Token:", token ? "existe" : "não existe");
    
    if (!token) {
      setState((prev) => ({ 
        ...prev, 
        isLoading: false, 
        error: "Not authenticated" 
      }));
      return;
    }
    
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const response = await projectsApi.list();
      console.log("[DEBUG] useProjects - Projetos retornados:", response.items.map((p: any) => ({ id: p.id, name: p.name })));
      setState({
        projects: response.items,
        isLoading: false,
        error: null,
      });
    } catch (error: any) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: error.message || "Failed to fetch projects",
      }));
    }
  }, []);

  useEffect(() => {
    // Pequeno delay para garantir que o localStorage está sincronizado
    const timer = setTimeout(() => {
      fetchProjects();
    }, 100);
    return () => clearTimeout(timer);
  }, [fetchProjects]);

  const createProject = useCallback(async (data: { name: string; description?: string }) => {
    try {
      // Sanitize inputs before sending to API (defense in depth)
      const sanitizedData = {
        name: sanitizeInput(data.name),
        description: data.description ? sanitizeInput(data.description) : undefined,
      };
      const newProject = await projectsApi.create(sanitizedData);
      setState((prev) => ({
        ...prev,
        projects: [...prev.projects, newProject],
      }));
      return newProject;
    } catch (error: any) {
      throw error;
    }
  }, []);

  const deleteProject = useCallback(async (id: string) => {
    try {
      await projectsApi.delete(id);
      setState((prev) => ({
        ...prev,
        projects: prev.projects.filter((p) => p.id !== id),
      }));
    } catch (error: any) {
      throw error;
    }
  }, []);

  return {
    ...state,
    refetch: fetchProjects,
    createProject,
    deleteProject,
  };
}

export function useProject(id: string) {
  console.log("[DEBUG] useProject - id:", id);
  
  const [state, setState] = useState<{
    project: Project | null;
    isLoading: boolean;
    error: string | null;
  }>({
    project: null,
    isLoading: true,
    error: null,
  });

  useEffect(() => {
    console.log("[DEBUG] useProject useEffect - id:", id);
    
    const fetchProject = async () => {
      console.log("[DEBUG] useProject - fetching project:", id);
      try {
        const project = await projectsApi.get(id);
        console.log("[DEBUG] useProject - SUCCESS:", project?.name);
        setState({ project, isLoading: false, error: null });
      } catch (error: any) {
        console.error("[DEBUG] useProject - FAILED:", error.message);
        setState({
          project: null,
          isLoading: false,
          error: error.message || "Failed to fetch project",
        });
      }
    };

    if (id) {
      console.log("[DEBUG] useProject - has id, scheduling fetch");
      // Delay para garantir que o localStorage está sincronizado
      const timer = setTimeout(() => {
        fetchProject();
      }, 100);
      return () => clearTimeout(timer);
    } else {
      console.log("[DEBUG] useProject - NO id, skipping fetch");
      setState({ project: null, isLoading: false, error: null });
    }
  }, [id]);

  console.log("[DEBUG] useProject - returning state:", { isLoading: state.isLoading, hasProject: !!state.project, error: state.error });
  return state;
}
