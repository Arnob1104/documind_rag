"use client";

import { useEffect, useState } from "react";
import { notFound, useParams, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import DocumentEditor from "@/components/documents/document-editor";
import { ApiError, documentsApi } from "@/lib/api";
import type { Document } from "@/lib/types";

export default function DocumentPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [document, setDocument] = useState<Document | null>(null);
  const [missing, setMissing] = useState(false);

  const isNew = id === "new";

  useEffect(() => {
    if (authLoading) return;

    // New documents need an account
    if (isNew) {
      if (!user) router.replace("/login?callbackUrl=/documents/new");
      return;
    }

    let active = true;
    documentsApi
      .get(id)
      .then((doc) => active && setDocument(doc))
      .catch((error) => {
        if (!active) return;
        if (error instanceof ApiError && error.status === 404) {
          setMissing(true);
        } else if (error instanceof ApiError && error.status === 403) {
          // Private document that isn't yours
          router.replace(user ? "/dashboard" : `/login?callbackUrl=/documents/${id}`);
        } else {
          console.error("Error loading document:", error);
          setMissing(true);
        }
      });

    return () => {
      active = false;
    };
  }, [id, isNew, authLoading, user, router]);

  if (missing) notFound();

  if (authLoading || (!isNew && !document) || (isNew && !user)) {
    return (
      <div className="flex justify-center items-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (isNew && user) {
    const now = new Date().toISOString();
    return (
      <div className="container mx-auto p-4">
        <DocumentEditor
          initialDocument={{
            id: "",
            title: "Untitled Document",
            content: "# Untitled Document\n\nStart writing your document here...",
            excerpt: null,
            isPublic: false,
            createdAt: now,
            updatedAt: now,
            authorId: user.id,
            tags: [],
            pdfData: null,
          }}
          isNew
        />
      </div>
    );
  }

  const doc = document!;
  const isAuthor = !!user && doc.authorId === user.id;

  return (
    <div className="container mx-auto p-4">
      <DocumentEditor key={doc.id} initialDocument={doc} readOnly={!isAuthor} />
    </div>
  );
}
