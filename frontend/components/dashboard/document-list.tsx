"use client";

import { useState } from "react";
import Link from "next/link";
import { formatDate } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { MoreHorizontal, Eye, EyeOff, Clock, Plus, PlusCircle, Tag, FileText } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import { documentsApi } from "@/lib/api";
import type { Document, Tag as TagType } from "@/lib/types";
import { useRouter } from "next/navigation";

interface DocumentListProps {
  documents: Document[];
  tags: TagType[];
  onChange?: () => void;
}

export default function DocumentList({ documents, tags, onChange }: DocumentListProps) {
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const router = useRouter();

  // Filter documents by selected tag
  const filteredDocuments = selectedTag
    ? documents.filter((doc) => 
        doc.tags.some((tag) => tag.tag.id === selectedTag)
      )
    : documents;

  const deleteDocument = async (id: string) => {
    try {
      await documentsApi.remove(id);
      
      toast.success("Document deleted successfully");
      onChange?.();
    } catch (error) {
      console.error("Error deleting document:", error);
      toast.error("Failed to delete document");
    }
  };

  const toggleVisibility = async (id: string, isCurrentlyPublic: boolean) => {
    try {
      await documentsApi.update(id, { isPublic: !isCurrentlyPublic });

      toast.success(`Document is now ${!isCurrentlyPublic ? 'public' : 'private'}`);
      onChange?.();
    } catch (error) {
      console.error("Error updating document visibility:", error);
      toast.error("Failed to update document visibility");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2">
        <Button
          variant={selectedTag === null ? "secondary" : "outline"}
          size="sm"
          onClick={() => setSelectedTag(null)}
          className="flex items-center"
        >
          <FileText className="mr-1 h-3.5 w-3.5" />
          All
        </Button>
        {tags.map((tag) => (
          <Button
            key={tag.id}
            variant={selectedTag === tag.id ? "secondary" : "outline"}
            size="sm"
            onClick={() => setSelectedTag(tag.id)}
            className="flex items-center"
            style={{
              backgroundColor: selectedTag === tag.id ? tag.color || undefined : undefined,
              color: selectedTag === tag.id && tag.color ? 'white' : undefined
            }}
          >
            <Tag className="mr-1 h-3.5 w-3.5" />
            {tag.name}
          </Button>
        ))}
      </div>
      
      <Separator />

      {filteredDocuments.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredDocuments.map((document) => (
            <Card key={document.id} className="transition-all hover:shadow-md">
              <CardHeader className="p-4 pb-2">
                <div className="flex justify-between items-start">
                  <CardTitle className="line-clamp-1 text-lg font-medium">
                    {document.title}
                  </CardTitle>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreHorizontal className="h-4 w-4" />
                        <span className="sr-only">Actions</span>
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem asChild>
                        <Link href={`/documents/${document.id}`}>Edit</Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => toggleVisibility(document.id, document.isPublic)}
                      >
                        {document.isPublic ? "Make Private" : "Make Public"}
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        className="text-destructive focus:text-destructive"
                        onClick={() => deleteDocument(document.id)}
                      >
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </CardHeader>
              <CardContent className="p-4 pt-2">
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {document.excerpt || document.content.slice(0, 100)}
                </p>
              </CardContent>
              <CardFooter className="p-4 pt-0 flex flex-col items-start">
                <div className="flex items-center text-xs text-muted-foreground mb-2">
                  <Clock className="mr-1 h-3.5 w-3.5" />
                  <span>Updated {formatDate(document.updatedAt)}</span>
                  <Separator orientation="vertical" className="mx-2 h-3" />
                  {document.isPublic ? (
                    <div className="flex items-center text-green-600 dark:text-green-400">
                      <Eye className="mr-1 h-3.5 w-3.5" />
                      <span>Public</span>
                    </div>
                  ) : (
                    <div className="flex items-center">
                      <EyeOff className="mr-1 h-3.5 w-3.5" />
                      <span>Private</span>
                    </div>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {document.tags.map((tagItem) => (
                    <Badge 
                      key={tagItem.tag.id} 
                      variant="secondary"
                      style={{
                        backgroundColor: tagItem.tag.color || undefined,
                        color: tagItem.tag.color ? 'white' : undefined
                      }}
                    >
                      {tagItem.tag.name}
                    </Badge>
                  ))}
                  {document.tags.length === 0 && (
                    <Badge variant="outline" className="border-dashed cursor-pointer">
                      <Plus className="mr-1 h-3 w-3" />
                      Add tags
                    </Badge>
                  )}
                </div>
              </CardFooter>
            </Card>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <FileText className="mx-auto h-12 w-12 text-muted-foreground opacity-50" />
          <h3 className="mt-4 text-lg font-medium">No documents found</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Create your first document to get started
          </p>
          <Button className="mt-4" onClick={() => router.push("/documents/new")}>
            <PlusCircle className="mr-2 h-4 w-4" />
            Create Document
          </Button>
        </div>
      )}
    </div>
  );
}