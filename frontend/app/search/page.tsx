"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Loader2, Search as SearchIcon, Tag, Clock, File, X, Sparkles } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useRequireAuth } from "@/components/auth-provider";
import { documentsApi, search } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { Document, SearchHit, Tag as TagType } from "@/lib/types";

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// Wraps query terms in <mark> using React nodes (no dangerouslySetInnerHTML)
function Highlight({ text, query }: { text: string; query: string }) {
  const terms = query
    .trim()
    .split(/\s+/)
    .filter((t) => t.length > 1)
    .map(escapeRegExp);
  if (terms.length === 0) return <>{text}</>;

  const parts = text.split(new RegExp(`(${terms.join("|")})`, "gi"));
  return (
    <>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <mark key={i} className="bg-yellow-200 dark:bg-yellow-800 rounded px-1 py-0.5">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

function SearchView() {
  const { user, loading: authLoading } = useRequireAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [query, setQuery] = useState<string>(searchParams.get("q") || "");
  const [results, setResults] = useState<SearchHit[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [docsById, setDocsById] = useState<Record<string, Document>>({});
  const requestId = useRef(0);

  // Search results don't carry tags/dates, so look them up from the document list
  useEffect(() => {
    if (!user) return;
    documentsApi
      .list()
      .then((docs) => setDocsById(Object.fromEntries(docs.map((d) => [d.id, d]))))
      .catch((error) => console.error("Error loading documents:", error));
  }, [user]);

  // Debounced search; stale responses are ignored
  useEffect(() => {
    if (!user) return;
    const q = query.trim();
    if (!q) {
      setResults([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    const id = ++requestId.current;
    const timer = setTimeout(async () => {
      try {
        const hits = await search(q);
        if (id !== requestId.current) return;
        setResults(hits);
        router.replace(`/search?q=${encodeURIComponent(q)}`, { scroll: false });
      } catch (error) {
        console.error("Search error:", error);
      } finally {
        if (id === requestId.current) setLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query, user, router]);

  const availableTags = useMemo<TagType[]>(() => {
    const seen = new Map<string, TagType>();
    results.forEach((r) =>
      docsById[r.documentId]?.tags.forEach(({ tag }) => seen.set(tag.id, tag))
    );
    return Array.from(seen.values());
  }, [results, docsById]);

  const filteredResults =
    selectedTags.length > 0
      ? results.filter((r) =>
          docsById[r.documentId]?.tags.some(({ tag }) => selectedTags.includes(tag.id))
        )
      : results;

  const toggleTag = (tagId: string) =>
    setSelectedTags((prev) =>
      prev.includes(tagId) ? prev.filter((id) => id !== tagId) : [...prev, tagId]
    );

  if (authLoading || !user) {
    return (
      <div className="flex justify-center items-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="container max-w-5xl mx-auto py-8 px-4">
      <h1 className="text-3xl font-bold mb-2">Document Search</h1>
      <p className="text-sm text-muted-foreground mb-6">
        Semantic search over your documents, plus exact title matches.
      </p>

      <div className="relative mb-6">
        <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search documents..."
          className="pl-10"
        />
      </div>

      {loading && (
        <div className="flex justify-center items-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}

      {!loading && query.trim() && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4 gap-4 flex-wrap">
            <h2 className="text-lg font-medium">
              {filteredResults.length} result{filteredResults.length !== 1 ? "s" : ""} for &quot;{query}&quot;
            </h2>

            {availableTags.length > 0 && (
              <div className="flex items-center space-x-2">
                <span className="text-sm text-muted-foreground">Filter by:</span>
                <div className="flex flex-wrap gap-2">
                  {availableTags.map((tag) => (
                    <Badge
                      key={tag.id}
                      variant={selectedTags.includes(tag.id) ? "default" : "outline"}
                      className="cursor-pointer"
                      style={{
                        backgroundColor: selectedTags.includes(tag.id) ? tag.color || undefined : undefined,
                        color: selectedTags.includes(tag.id) && tag.color ? "white" : undefined,
                      }}
                      onClick={() => toggleTag(tag.id)}
                    >
                      {tag.name}
                    </Badge>
                  ))}
                  {selectedTags.length > 0 && (
                    <Button size="sm" variant="ghost" onClick={() => setSelectedTags([])} className="h-6 px-2 text-xs">
                      <X className="h-3 w-3 mr-1" />
                      Clear
                    </Button>
                  )}
                </div>
              </div>
            )}
          </div>

          <div className="space-y-4">
            {filteredResults.length > 0 ? (
              filteredResults.map((hit) => {
                const doc = docsById[hit.documentId];
                return (
                  <Card key={hit.documentId} className="overflow-hidden hover:shadow-md transition-shadow">
                    <CardContent className="p-4">
                      <Link href={`/documents/${hit.documentId}`} className="block">
                        <div className="flex items-center gap-2 mb-2">
                          <File className="h-4 w-4 text-muted-foreground" />
                          <h3 className="text-lg font-medium">
                            <Highlight text={hit.title} query={query} />
                          </h3>
                          <Badge variant="outline" className="ml-auto text-[10px] font-normal">
                            {hit.source === "vector" ? (
                              <>
                                <Sparkles className="mr-1 h-3 w-3" />
                                Semantic {Math.round(hit.score * 100)}%
                              </>
                            ) : (
                              "Title match"
                            )}
                          </Badge>
                        </div>

                        {hit.snippet && (
                          <p className="text-sm text-muted-foreground mb-3 line-clamp-3">
                            <Highlight text={hit.snippet} query={query} />
                          </p>
                        )}

                        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
                          {doc && (
                            <div className="flex items-center">
                              <Clock className="mr-1 h-3.5 w-3.5" />
                              <span>{formatDate(doc.updatedAt)}</span>
                            </div>
                          )}
                          {doc && doc.tags.length > 0 && (
                            <div className="flex flex-wrap items-center gap-1">
                              <Tag className="h-3.5 w-3.5" />
                              {doc.tags.map(({ tag }) => (
                                <Badge
                                  key={tag.id}
                                  variant="secondary"
                                  className="px-1.5 py-0 text-[10px]"
                                  style={{
                                    backgroundColor: tag.color ? `${tag.color}30` : undefined,
                                    color: tag.color || undefined,
                                  }}
                                >
                                  {tag.name}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>
                      </Link>
                    </CardContent>
                  </Card>
                );
              })
            ) : (
              <div className="text-center py-12">
                <SearchIcon className="mx-auto h-12 w-12 text-muted-foreground opacity-50" />
                <h3 className="mt-4 text-lg font-medium">No results found</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  Try adjusting your search or filter to find what you&apos;re looking for
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {!loading && !query.trim() && (
        <div className="text-center py-12">
          <SearchIcon className="mx-auto h-12 w-12 text-muted-foreground opacity-50" />
          <h3 className="mt-4 text-lg font-medium">Start searching</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Enter a search term to find documents in your knowledge base
          </p>
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={null}>
      <SearchView />
    </Suspense>
  );
}
