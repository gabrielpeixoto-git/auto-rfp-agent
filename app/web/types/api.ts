// Types para a API Auto-RFP

export interface Project {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  status: "draft" | "active" | "archived";
  created_by_id: string;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  project_id: string;
  filename: string;
  original_filename?: string;
  file_type: string;
  // Status EXATOS do backend - NOTE: não existe 'processing', backend usa 'extracting'/'chunking'/'indexing'
  status: "pending" | "uploaded" | "extracting" | "chunking" | "indexing" | "processed" | "failed";
  error_message: string | null;
  question_count?: number;
  created_at: string;
  updated_at: string;
}

export interface Question {
  id: string;
  document_id: string;
  project_id: string;
  question_text: string;
  category: "security" | "technical" | "general" | "compliance" | "other";
  status: "pending" | "reviewed" | "approved" | "generated";
  deadline: string | null;
  order_index: number;
  created_at: string;
  answer?: Answer;
}

export interface Answer {
  id: string;
  question_id: string;
  suggested_text: string;
  final_text: string | null;
  status: "pending" | "reviewed" | "approved";
  confidence: number;
  citations: string[];
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "analyst" | "viewer";
  tenant_id: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
}

export interface UploadDocumentResponse {
  id: string;
  filename: string;
  status: string;
}
