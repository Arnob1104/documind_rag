"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { useRequireAuth } from "@/components/auth-provider";
import DashboardHeader from "@/components/dashboard/dashboard-header";
import DocumentList from "@/components/dashboard/document-list";
import RecentActivity from "@/components/dashboard/recent-activity";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { documentsApi } from "@/lib/api";
import type { Document, Tag } from "@/lib/types";

export default function DashboardPage() {
  const { user, loading: authLoading, displayName } = useRequireAuth();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const all = await documentsApi.list();
      setDocuments(all);
    } catch (error) {
      console.error("Error loading documents:", error);
      toast.error("Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  // The API returns own + public documents; the dashboard only shows your own.
  const mine = useMemo(
    () => documents.filter((d) => d.authorId === user?.id),
    [documents, user?.id]
  );

  const tags = useMemo<Tag[]>(() => {
    const seen = new Map<string, Tag>();
    mine.forEach((d) => d.tags.forEach(({ tag }) => seen.set(tag.id, tag)));
    return Array.from(seen.values());
  }, [mine]);

  if (authLoading || !user) return <PageSpinner />;

  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;

  return (
    <div className="container mx-auto px-4 py-8">
      <DashboardHeader username={displayName} />

      {loading ? (
        <PageSpinner />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mt-8">
          <div className="lg:col-span-2">
            <Tabs defaultValue="all" className="w-full">
              <div className="flex justify-between items-center mb-6">
                <TabsList>
                  <TabsTrigger value="all">All Documents</TabsTrigger>
                  <TabsTrigger value="recent">Recent</TabsTrigger>
                  <TabsTrigger value="private">Private</TabsTrigger>
                  <TabsTrigger value="public">Public</TabsTrigger>
                </TabsList>
              </div>

              <TabsContent value="all" className="mt-0">
                <DocumentList documents={mine} tags={tags} onChange={load} />
              </TabsContent>
              <TabsContent value="recent" className="mt-0">
                <DocumentList
                  documents={mine.filter((d) => new Date(d.updatedAt).getTime() > weekAgo)}
                  tags={tags}
                  onChange={load}
                />
              </TabsContent>
              <TabsContent value="private" className="mt-0">
                <DocumentList
                  documents={mine.filter((d) => !d.isPublic)}
                  tags={tags}
                  onChange={load}
                />
              </TabsContent>
              <TabsContent value="public" className="mt-0">
                <DocumentList
                  documents={mine.filter((d) => d.isPublic)}
                  tags={tags}
                  onChange={load}
                />
              </TabsContent>
            </Tabs>
          </div>

          <div className="space-y-8">
            <RecentActivity documents={mine.slice(0, 5)} />
          </div>
        </div>
      )}
    </div>
  );
}

function PageSpinner() {
  return (
    <div className="flex justify-center items-center py-24">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}
