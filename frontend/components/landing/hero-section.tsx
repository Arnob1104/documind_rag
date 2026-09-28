import { Button } from "@/components/ui/button";
import Link from "next/link";
import { FileText, Search, Tag, Clock } from "lucide-react";

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
            Your AI-powered knowledge base for smarter document management and instant insights
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
                    <Clock className="h-4 w-4 mr-2" />
                    Recent
                  </Button>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 flex-1 overflow-hidden">
                {Array(4).fill(0).map((_, i) => (
                  <div key={i} className="bg-card rounded-md p-4 shadow-sm transition-all hover:shadow-md border border-border">
                    <h3 className="font-medium mb-2">Document {i + 1}</h3>
                    <p className="text-sm text-muted-foreground mb-3">
                      This is a brief excerpt of the document content showing the main points and key takeaways...
                    </p>
                    <div className="flex items-center justify-between">
                      <div className="flex gap-2">
                        <span className="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary">
                          AI
                        </span>
                        <span className="text-xs px-2 py-1 rounded-full bg-secondary/10 text-secondary">
                          Research
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