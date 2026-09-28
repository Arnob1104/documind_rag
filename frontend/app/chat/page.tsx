"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  Bot,
  FileText,
  Loader2,
  MessageSquarePlus,
  Send,
  Sparkles,
  Wrench,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useRequireAuth } from "@/components/auth-provider";
import MarkdownPreview from "@/components/documents/markdown-preview";
import { chatApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ChatSession, ChatSource } from "@/lib/types";

interface UiMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  actions?: string[];
  agents?: string[];
  sources?: ChatSource[];
}

const ACTION_LABELS: Record<string, string> = {
  search_knowledge_base: "Searched knowledge base",
  list_documents: "Listed documents",
  get_document: "Read a document",
  list_my_documents: "Listed your documents",
  list_tags: "Checked existing tags",
  apply_tags: "Applied tags",
};

const AGENT_LABELS: Record<string, string> = {
  retriever: "Retriever agent",
  tagger: "Tagger agent",
};

const SUGGESTIONS = [
  "What documents do I have?",
  "Summarize my most recently updated document",
  "Find everything related to onboarding",
  "Read my latest document and suggest tags for it",
];

export default function ChatPage() {
  const { user, loading: authLoading } = useRequireAuth();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadSessions = useCallback(async () => {
    try {
      setSessions(await chatApi.sessions());
    } catch (error) {
      console.error("Error loading chat sessions:", error);
    }
  }, []);

  useEffect(() => {
    if (user) loadSessions();
  }, [user, loadSessions]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, sending]);

  const openSession = async (id: string) => {
    if (sending || id === activeId) return;
    setActiveId(id);
    setLoadingHistory(true);
    try {
      const rows = await chatApi.messages(id);
      setMessages(
        rows
          .filter((m) => m.role === "user" || m.role === "assistant")
          .map((m) => ({
            id: m.id,
            role: m.role as "user" | "assistant",
            content: m.content,
          }))
      );
    } catch (error) {
      console.error("Error loading messages:", error);
      toast.error("Failed to load conversation");
    } finally {
      setLoadingHistory(false);
    }
  };

  const newChat = () => {
    if (sending) return;
    setActiveId(null);
    setMessages([]);
    setInput("");
  };

  const send = async (text: string) => {
    const message = text.trim();
    if (!message || sending) return;

    const tempId = `tmp-${Date.now()}`;
    setMessages((prev) => [...prev, { id: tempId, role: "user", content: message }]);
    setInput("");
    setSending(true);

    try {
      const reply = await chatApi.send(message, activeId);
      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: "assistant",
          content: reply.reply,
          actions: reply.actionsTaken,
          agents: reply.agentsUsed,
          sources: reply.sources,
        },
      ]);
      if (!activeId) {
        setActiveId(reply.sessionId);
        loadSessions();
      }
    } catch (error) {
      console.error("Chat error:", error);
      toast.error(error instanceof Error ? error.message : "Chat request failed");
      // Roll back the optimistic message so the user can retry
      setMessages((prev) => prev.filter((m) => m.id !== tempId));
      setInput(message);
    } finally {
      setSending(false);
    }
  };

  if (authLoading || !user) {
    return (
      <div className="flex justify-center items-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="grid grid-cols-1 md:grid-cols-[260px_1fr] gap-6 h-[calc(100vh-9rem)]">
        {/* Sessions */}
        <aside className="hidden md:flex flex-col border rounded-lg overflow-hidden">
          <div className="p-3 border-b">
            <Button onClick={newChat} variant="outline" className="w-full" disabled={sending}>
              <MessageSquarePlus className="mr-2 h-4 w-4" />
              New chat
            </Button>
          </div>
          <ScrollArea className="flex-1">
            <div className="p-2 space-y-1">
              {sessions.length === 0 && (
                <p className="text-xs text-muted-foreground p-2">No conversations yet</p>
              )}
              {sessions.map((s) => (
                <button
                  key={s.id}
                  onClick={() => openSession(s.id)}
                  className={cn(
                    "w-full text-left text-sm px-3 py-2 rounded-md truncate transition-colors",
                    s.id === activeId ? "bg-primary/10 text-primary" : "hover:bg-accent"
                  )}
                >
                  {s.title || "Untitled chat"}
                </button>
              ))}
            </div>
          </ScrollArea>
        </aside>

        {/* Conversation */}
        <section className="flex flex-col border rounded-lg overflow-hidden min-h-0">
          <div className="flex items-center justify-between px-4 py-3 border-b">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <h1 className="font-semibold">Ask your knowledge base</h1>
            </div>
            <Button onClick={newChat} variant="ghost" size="sm" className="md:hidden" disabled={sending}>
              <MessageSquarePlus className="h-4 w-4" />
            </Button>
          </div>

          <ScrollArea className="flex-1">
            <div className="p-4 space-y-6">
              {loadingHistory && (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </div>
              )}

              {!loadingHistory && messages.length === 0 && (
                <div className="text-center py-12 space-y-4">
                  <Bot className="mx-auto h-12 w-12 text-muted-foreground opacity-50" />
                  <div>
                    <h2 className="text-lg font-medium">What would you like to know?</h2>
                    <p className="text-sm text-muted-foreground">
                      The assistant can search, read and tag your documents.
                    </p>
                  </div>
                  <div className="flex flex-wrap justify-center gap-2 max-w-xl mx-auto">
                    {SUGGESTIONS.map((s) => (
                      <Button key={s} variant="outline" size="sm" onClick={() => send(s)}>
                        {s}
                      </Button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((m) => (
                <MessageBubble key={m.id} message={m} />
              ))}

              {sending && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Thinking...
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          </ScrollArea>

          <form
            className="border-t p-3 flex gap-2 items-end"
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
          >
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send(input);
                }
              }}
              placeholder="Ask a question or give an instruction..."
              className="min-h-[44px] max-h-40 resize-none"
              rows={1}
              disabled={sending}
            />
            <Button type="submit" size="icon" disabled={sending || !input.trim()}>
              <Send className="h-4 w-4" />
              <span className="sr-only">Send</span>
            </Button>
          </form>
        </section>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: UiMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary text-primary-foreground px-4 py-2 text-sm whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    );
  }

  // Unique source documents (the agent may return several chunks per document)
  const seen = new Set<string>();
  const sources = (message.sources ?? []).filter((s) => {
    if (seen.has(s.document_id)) return false;
    seen.add(s.document_id);
    return true;
  });

  return (
    <div className="flex gap-3">
      <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
        <Bot className="h-4 w-4 text-primary" />
      </div>
      <div className="min-w-0 max-w-[85%] space-y-2">
        {message.agents && message.agents.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {message.agents.map((a) => (
              <Badge key={a} variant="outline" className="text-[10px] font-normal">
                <Bot className="mr-1 h-3 w-3" />
                {AGENT_LABELS[a] ?? a}
              </Badge>
            ))}
          </div>
        )}
        {message.actions && message.actions.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {message.actions.map((a, i) => (
              <Badge key={`${a}-${i}`} variant="secondary" className="text-[10px] font-normal">
                <Wrench className="mr-1 h-3 w-3" />
                {ACTION_LABELS[a] ?? a}
              </Badge>
            ))}
          </div>
        )}
        <div className="rounded-2xl rounded-tl-sm bg-muted px-4 py-2 text-sm">
          <MarkdownPreview content={message.content} allowHtml={false} />
        </div>
        {sources.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>Sources:</span>
            {sources.map((s) => (
              <Link
                key={s.document_id}
                href={`/documents/${s.document_id}`}
                className="inline-flex items-center gap-1 rounded-md border px-2 py-0.5 hover:bg-accent"
              >
                <FileText className="h-3 w-3" />
                {s.title}
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
