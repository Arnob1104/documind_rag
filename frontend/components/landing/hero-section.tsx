import { Button } from "@/components/ui/button";
import Link from "next/link";
import { FileText, Search, Tag, MessageSquare } from "lucide-react";

export function HeroSection() {
  return (
    <section className="relative py-20 overflow-hidden bg-background">
      <div className="absolute inset-0 z-0 bg-[radial-gradient(circle_at_top_right,hsl(var(--primary)/0.1),transparent_40%)]"></div>
      
      <div className="container px-4 mx-auto relative z-10">
        <div className="flex flex-col items-center text-center mb-16">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/60">
            DocuMind
          </h1>
          <p className="text-xl md:text-2xl text-muted-foreground max-w-2xl mx-auto mb-8">
            Write notes and upload PDFs, then search them by meaning or ask questions. An AI assistant answers from your own documents and cites its sources.
          </p>
          <div className="flex flex-col sm:flex-row gap-4">
            <Button size="lg" asChild>
              <Link href="/dashboard">Get Started</Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="/login">Sign In</Link>
            </Button>
          </div>
        </div>

        <div className="relative mx-auto w-full max-w-4xl aspect-video rounded-xl bg-card p-1 shadow-2xl ring-1 ring-border overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-tr from-primary/10 to-secondary/10 animate-pulse"></div>
          <div className="relative h-full w-full rounded-lg bg-background p-4 overflow-hidden">
            <div className="flex flex-col h-full">
              <div className="flex items-center justify-between border-b pb-4">
                <div className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-primary" />
                  <span className="font-medium">My Knowledge Base</span>
                </div>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="ghost">
                    <Search className="h-4 w-4 mr-2" />
                    Search
                  </Button>
                  <Button size="sm" variant="ghost">
                    <Tag className="h-4 w-4 mr-2" />
                    Tags
                  </Button>
                  <Button size="sm" variant="ghost">
                    <MessageSquare className="h-4 w-4 mr-2" />
                    Ask AI
                  </Button>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 flex-1 overflow-hidden">
                {[
                  { title: "Q3 Planning Notes", excerpt: "Key decisions from the planning meeting, action items, and owners for each workstream...", tags: ["Notes", "Planning"], updated: "{doc.updated}" },
                  { title: "Supplier Contract.pdf", excerpt: "Text extracted from the uploaded PDF and indexed, so you can search it and ask questions about it...", tags: ["PDF", "Contracts"], updated: "Updated 3d ago" },
                  { title: "Onboarding Guide", excerpt: "Step-by-step guide for new team members, written in Markdown with live preview...", tags: ["Guide", "Team"], updated: "Updated 5d ago" },
                  { title: "Research Summary", excerpt: "Findings and references collected in one place, private to you or shared publicly...", tags: ["Research", "Public"], updated: "Updated 1w ago" },
                ].map((doc, i) => (
                  <div key={i} className="bg-card rounded-md p-4 shadow-sm transition-all hover:shadow-md border border-border">
                    <h3 className="font-medium mb-2">{doc.title}</h3>
                    <p className="text-sm text-muted-foreground mb-3">
                      {doc.excerpt}
                    </p>
                    <div className="flex items-center justify-between">
                      <div className="flex gap-2">
                        <span className="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary">
                          {doc.tags[0]}
                        </span>
                        <span className="text-xs px-2 py-1 rounded-full bg-secondary/10 text-secondary">
                          {doc.tags[1]}
                        </span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        Updated 2d ago
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
