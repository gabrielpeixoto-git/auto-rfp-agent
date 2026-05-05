"use client";

import { useState, useEffect, useCallback } from "react";
import { questionsApi } from "@/lib/api/client";
import type { Question, Answer } from "@/types/api";

export function useQuestions(documentId: string) {
  const [state, setState] = useState<{
    questions: Question[];
    isLoading: boolean;
    error: string | null;
  }>({
    questions: [],
    isLoading: true,
    error: null,
  });

  const fetchQuestions = useCallback(async () => {
    if (!documentId) return;
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const response = await questionsApi.list(documentId);
      
      // CORREÇÃO: API pode retornar array direto OU { items: [...] }
      let questions: Question[] = [];
      if (Array.isArray(response)) {
        questions = response;
      } else if (response && Array.isArray(response.items)) {
        questions = response.items;
      }
      
      setState({
        questions,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to fetch questions";
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
    }
  }, [documentId]);

  useEffect(() => {
    fetchQuestions();
  }, [fetchQuestions]);

  const updateAnswer = useCallback(async (questionId: string, data: { final_text: string; status: string }) => {
    try {
      await questionsApi.updateAnswer(questionId, data);
      setState((prev) => ({
        ...prev,
        questions: prev.questions.map((q) =>
          q.id === questionId ? { ...q, status: data.status as "pending" | "reviewed" | "approved" } : q
        ),
      }));
    } catch (error) {
      throw error;
    }
  }, []);

  const approveAnswer = useCallback(async (questionId: string) => {
    try {
      await questionsApi.approveAnswer(questionId);
      setState((prev) => ({
        ...prev,
        questions: prev.questions.map((q) =>
          q.id === questionId ? { ...q, status: "approved" } : q
        ),
      }));
    } catch (error) {
      throw error;
    }
  }, []);

  const generateAnswer = useCallback(async (questionId: string) => {
    try {
      const answer = await questionsApi.generateAnswer(questionId);
      // Atualiza o estado local com a nova resposta
      setState((prev) => ({
        ...prev,
        questions: prev.questions.map((q) =>
          q.id === questionId ? { ...q, answer, status: "generated" } : q
        ),
      }));
      return answer;
    } catch (error) {
      throw error;
    }
  }, []);

  return {
    ...state,
    refetch: fetchQuestions,
    updateAnswer,
    approveAnswer,
    generateAnswer,
  };
}

export function useQuestion(questionId: string) {
  const [state, setState] = useState<{
    question: (Question & { answer?: Answer }) | null;
    isLoading: boolean;
    error: string | null;
  }>({
    question: null,
    isLoading: true,
    error: null,
  });

  useEffect(() => {
    const fetchQuestion = async () => {
      if (!questionId) return;
      try {
        const [question, answer] = await Promise.all([
          questionsApi.get(questionId),
          questionsApi.getAnswer(questionId),
        ]);
        setState({
          question: { ...question, answer },
          isLoading: false,
          error: null,
        });
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to fetch question";
        setState({
          question: null,
          isLoading: false,
          error: message,
        });
      }
    };

    fetchQuestion();
  }, [questionId]);

  return state;
}
