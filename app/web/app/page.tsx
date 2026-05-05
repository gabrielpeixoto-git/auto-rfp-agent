"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FileText, Brain, Shield, CheckCircle, Sparkles, Upload, Cpu, FileCheck } from "lucide-react";

function scrollToSection(e: React.MouseEvent<HTMLAnchorElement>, sectionId: string) {
  e.preventDefault();
  const element = document.getElementById(sectionId);
  if (element) {
    element.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

export default function Home() {
  const currentYear = new Date().getFullYear();
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted">
      <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur-xl supports-[backdrop-filter]:bg-background/80">
        <div className="container flex h-16 items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-md shadow-primary/20 group-hover:shadow-lg group-hover:shadow-primary/30 transition-all duration-300">
              <Brain className="h-5 w-5" />
            </div>
            <div className="flex flex-col">
              <span className="text-base font-bold tracking-tight text-foreground">Auto-RFP</span>
              <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider leading-none">Agent</span>
            </div>
          </Link>
          <nav className="hidden md:flex items-center gap-1">
            <Link href="#features" onClick={(e) => scrollToSection(e, "features")}>
              <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
                Recursos
              </Button>
            </Link>
            <Link href="#how-it-works" onClick={(e) => scrollToSection(e, "how-it-works")}>
              <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
                Como Funciona
              </Button>
            </Link>
          </nav>
          <div className="flex items-center gap-2">
            <Link href="/login">
              <Button variant="ghost" size="sm" className="hidden sm:inline-flex">
                Entrar
              </Button>
            </Link>
            <Link href="/register">
              <Button size="sm" className="bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary shadow-md shadow-primary/25 hover:shadow-lg hover:shadow-primary/30 transition-all duration-300">
                Começar Grátis
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="container py-16 sm:py-24">
        <div className="mx-auto max-w-4xl text-center">
          <div className="inline-flex items-center gap-2 rounded-full border bg-muted/50 px-4 py-1.5 text-sm font-medium text-muted-foreground mb-8">
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            <span>Powered by AI</span>
          </div>
          <h1 className="text-4xl font-bold tracking-tight sm:text-6xl lg:text-7xl">
            Processamento de RFPs com{" "}
            <span className="bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">Inteligência Artificial</span>
          </h1>
          <p className="mt-6 text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            Faça upload de RFPs, RFIs, DDQs e questionários de segurança. 
            Nossa IA extrai perguntas, sugere respostas da sua base de conhecimento 
            e ajuda você a entregar propostas vencedoras mais rápido.
          </p>
        </div>

        <div id="features" className="mt-20 scroll-mt-24">
          <h2 className="text-3xl font-bold text-center mb-12">Recursos</h2>
          <div className="grid gap-8 md:grid-cols-3">
            <Card>
              <CardHeader>
                <FileText className="h-8 w-8 text-primary" />
                <CardTitle className="mt-4">Smart Document Processing</CardTitle>
                <CardDescription>
                  Automatically parse PDFs, Word docs, and Excel files.
                  Extract questions, requirements, and deadlines.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader>
                <Brain className="h-8 w-8 text-primary" />
                <CardTitle className="mt-4">AI Answer Generation</CardTitle>
                <CardDescription>
                  RAG-powered answers from your approved knowledge base.
                  Always cited, always traceable.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader>
                <CheckCircle className="h-8 w-8 text-primary" />
                <CardTitle className="mt-4">Human Review Workflow</CardTitle>
                <CardDescription>
                  Review, edit, and approve AI-generated answers.
                  Full audit trail and version control.
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
        </div>

        <div id="how-it-works" className="mt-24 scroll-mt-24">
          <h2 className="text-3xl font-bold text-center mb-12">Como Funciona</h2>
          <div className="grid gap-8 md:grid-cols-3">
            <Card>
              <CardHeader>
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary mb-4">
                  <Upload className="h-6 w-6" />
                </div>
                <CardTitle>1. Faça Upload</CardTitle>
                <CardDescription>
                  Envie seu RFP, RFI ou questionário em PDF, Word ou Excel. 
                  Nossa IA processa automaticamente o documento.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary mb-4">
                  <Cpu className="h-6 w-6" />
                </div>
                <CardTitle>2. IA Processa</CardTitle>
                <CardDescription>
                  Extraímos todas as perguntas e geramos respostas 
                  inteligentes baseadas na sua base de conhecimento.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary mb-4">
                  <FileCheck className="h-6 w-6" />
                </div>
                <CardTitle>3. Revise e Exporte</CardTitle>
                <CardDescription>
                  Revise as respostas, faça ajustes se necessário 
                  e exporte sua proposta finalizada.
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
        </div>

        <div className="mt-20 text-center">
          <Link href="/dashboard">
            <Button size="lg">Start Your First RFP</Button>
          </Link>
        </div>
      </main>

      <footer className="border-t bg-muted py-8">
        <div className="container text-center text-sm text-muted-foreground">
          © {currentYear} Auto-RFP Agent. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
