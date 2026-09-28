"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { PlusCircle, Search, Tag } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import Link from "next/link";
import { documentsApi } from "@/lib/api";
import { generateExcerpt } from "@/lib/utils";

interface DashboardHeaderProps {
  username: string;
}

export default function DashboardHeader({ username }: DashboardHeaderProps) {
  const [isCreating, setIsCreating] = useState(false);
  const [documentTitle, setDocumentTitle] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleCreateDocument = async () => {
    if (!documentTitle.trim()) return;

    setIsLoading(true);
    
    try {
      const content = `# ${documentTitle}\n\nStart writing your document here...`;
      const data = await documentsApi.create({
        title: documentTitle,
        content,
        excerpt: generateExcerpt(content),
      });
      toast.success("Document created successfully");
      router.push(`/documents/${data.id}`);
    } catch (error) {
      console.error("Error creating document:", error);
      toast.error("Failed to create document");
    } finally {
      setIsLoading(false);
      setIsCreating(false);
      setDocumentTitle("");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:justify-between sm:items-center">
        <h1 className="text-3xl font-bold tracking-tight">
          Welcome back, {username}
        </h1>
        <div className="flex items-center space-x-2">
          <Dialog open={isCreating} onOpenChange={setIsCreating}>
            <DialogTrigger asChild>
              <Button>
                <PlusCircle className="mr-2 h-4 w-4" />
                New Document
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create a new document</DialogTitle>
                <DialogDescription>
                  Give your document a title to get started
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <Input
                  placeholder="Enter document title"
                  value={documentTitle}
                  onChange={(e) => setDocumentTitle(e.target.value)}
                />
              </div>
              <DialogFooter>
                <Button 
                  variant="outline" 
                  onClick={() => setIsCreating(false)}
                >
                  Cancel
                </Button>
                <Button 
                  onClick={handleCreateDocument} 
                  disabled={!documentTitle.trim() || isLoading}
                >
                  {isLoading ? "Creating..." : "Create"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <Button variant="outline" asChild>
            <Link href="/tags">
              <Tag className="mr-2 h-4 w-4" />
              Manage Tags
            </Link>
          </Button>
        </div>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search documents..."
          className="pl-10 w-full sm:max-w-md"
          onClick={() => router.push("/search")}
          readOnly
        />
      </div>
    </div>
  );
}