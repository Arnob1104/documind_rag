export interface Tag {
  id: string;
  name: string;
  color: string | null;
  /** auth user id of the creator; only they can delete the tag (null for legacy tags) */
  created_by?: string | null;
}

export interface DocumentTag {
  tag: Tag;
}

export interface PdfData {
  id: string;
  filename: string;
  fileSize: number;
  extractedText: string;
}

export interface DocumentVersion {
  id: string;
  documentId: string;
  content: string;
  createdAt: string;
}

export interface Document {
  id: string;
  title: string;
  content: string;
  excerpt: string | null;
  isPublic: boolean;
  authorId: string;
  createdAt: string;
  updatedAt: string;
  tags: DocumentTag[];
  pdfData: PdfData | null;
}

export interface SearchHit {
  documentId: string;
  title: string;
  excerpt: string | null;
  snippet: string;
  score: number;
  source: "vector" | "keyword";
}

export interface ChatSession {
  id: string;
  title: string | null;
  createdAt: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "tool";
  content: string;
  createdAt: string;
}

export interface ChatSource {
  chunk_id?: string;
  document_id: string;
  title: string;
  content: string;
  similarity: number;
}

export interface ChatReply {
  sessionId: string;
  reply: string;
  actionsTaken: string[];
  /** which specialist agents handled the request, e.g. ["retriever", "tagger"] */
  agentsUsed: string[];
  sources: ChatSource[];
}
