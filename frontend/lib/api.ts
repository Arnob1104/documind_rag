import { supabase } from "@/lib/supabase";
import type {
  ChatMessage,
  ChatReply,
  ChatSession,
  ChatSource,
  Document,
  DocumentVersion,
  PdfData,
  SearchHit,
  Tag,
} from "@/lib/types";

export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
).replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers = new Headers(init.headers);
  if (session?.access_token) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }
  // Let the browser set the multipart boundary for FormData
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_URL}${path}`, { ...init, headers });

  if (!res.ok) {
    let detail = res.statusText || "Request failed";
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
      else if (body?.detail) detail = JSON.stringify(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

/* ───────────── mappers: FastAPI snake_case rows -> frontend camelCase ───────────── */

/* eslint-disable @typescript-eslint/no-explicit-any */
function mapPdf(raw: any): PdfData | null {
  const row = Array.isArray(raw) ? raw[0] : raw;
  if (!row) return null;
  return {
    id: row.id,
    filename: row.filename,
    fileSize: row.file_size,
    extractedText: row.extracted_text,
  };
}

export function mapDocument(raw: any): Document {
  return {
    id: raw.id,
    title: raw.title,
    content: raw.content ?? "",
    excerpt: raw.excerpt ?? null,
    isPublic: raw.is_public,
    authorId: raw.author_id,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
    tags: (raw.tags ?? [])
      .filter((t: any) => t?.tag)
      .map((t: any) => ({ tag: t.tag })),
    pdfData: mapPdf(raw.pdf_data),
  };
}

function mapVersion(raw: any): DocumentVersion {
  return {
    id: raw.id,
    documentId: raw.document_id,
    content: raw.content,
    createdAt: raw.created_at,
  };
}

function mapSession(raw: any): ChatSession {
  return { id: raw.id, title: raw.title ?? null, createdAt: raw.created_at };
}

function mapMessage(raw: any): ChatMessage {
  return {
    id: raw.id,
    role: raw.role,
    content: raw.content,
    createdAt: raw.created_at,
  };
}
/* eslint-enable @typescript-eslint/no-explicit-any */

/* ───────────── documents ───────────── */

export interface DocumentInput {
  title?: string;
  content?: string;
  excerpt?: string | null;
  isPublic?: boolean;
}

function toBody(input: DocumentInput) {
  const body: Record<string, unknown> = {};
  if (input.title !== undefined) body.title = input.title;
  if (input.content !== undefined) body.content = input.content;
  if (input.excerpt !== undefined) body.excerpt = input.excerpt;
  if (input.isPublic !== undefined) body.is_public = input.isPublic;
  return JSON.stringify(body);
}

export const documentsApi = {
  // Backend returns every document visible to the caller (own + public).
  list: async () =>
    (await request<unknown[]>("/api/documents")).map(mapDocument),
  get: async (id: string) =>
    mapDocument(await request(`/api/documents/${id}`)),
  create: async (input: DocumentInput & { title: string }) =>
    mapDocument(
      await request("/api/documents", { method: "POST", body: toBody(input) })
    ),
  update: async (id: string, input: DocumentInput) =>
    mapDocument(
      await request(`/api/documents/${id}`, {
        method: "PATCH",
        body: toBody(input),
      })
    ),
  remove: (id: string) =>
    request<{ deleted: boolean }>(`/api/documents/${id}`, { method: "DELETE" }),
  versions: async (id: string) =>
    (await request<unknown[]>(`/api/documents/${id}/versions`)).map(mapVersion),
};

/* ───────────── tags ───────────── */

export const tagsApi = {
  list: () => request<Tag[]>("/api/tags"),
  create: (name: string, color: string | null) =>
    request<Tag>("/api/tags", {
      method: "POST",
      body: JSON.stringify({ name, color }),
    }),
  remove: (id: string) =>
    request<{ deleted: boolean }>(`/api/tags/${id}`, { method: "DELETE" }),
  attach: (documentId: string, tagId: string) =>
    request(`/api/tags/documents/${documentId}/${tagId}`, { method: "POST" }),
  detach: (documentId: string, tagId: string) =>
    request(`/api/tags/documents/${documentId}/${tagId}`, { method: "DELETE" }),
};

/* ───────────── PDF upload ───────────── */

export async function uploadPdf(documentId: string, file: File) {
  const form = new FormData();
  form.append("document_id", documentId);
  form.append("file", file);
  return mapPdf(await request("/api/upload/pdf", { method: "POST", body: form }))!;
}

/* ───────────── search ───────────── */

export async function search(q: string, limit = 20): Promise<SearchHit[]> {
  /* eslint-disable-next-line @typescript-eslint/no-explicit-any */
  const rows = await request<any[]>(
    `/api/search?q=${encodeURIComponent(q)}&limit=${limit}`
  );
  return rows.map((r) => ({
    documentId: r.document_id,
    title: r.title,
    excerpt: r.excerpt ?? null,
    snippet: r.snippet ?? "",
    score: r.score,
    source: r.source,
  }));
}

/* ───────────── RAG agent chat ───────────── */

export const chatApi = {
  send: async (message: string, sessionId?: string | null): Promise<ChatReply> => {
    /* eslint-disable-next-line @typescript-eslint/no-explicit-any */
    const r = await request<any>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, session_id: sessionId ?? null }),
    });
    return {
      sessionId: r.session_id,
      reply: r.reply,
      actionsTaken: r.actions_taken ?? [],
      agentsUsed: r.agents_used ?? [],
      sources: (r.sources ?? []) as ChatSource[],
    };
  },
  sessions: async () =>
    (await request<unknown[]>("/api/chat/sessions")).map(mapSession),
  messages: async (sessionId: string) =>
    (await request<unknown[]>(`/api/chat/sessions/${sessionId}/messages`)).map(
      mapMessage
    ),
};
