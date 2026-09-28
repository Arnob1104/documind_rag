import {
  FileText,
  Search,
  Tags,
  Eye,
  BookOpen,
  History,
  MessageSquare,
  Bot
} from "lucide-react";

export function FeatureSection() {
  const features = [
    {
      icon: <MessageSquare className="h-10 w-10 text-primary mb-4" />,
      title: "Chat With Your Documents",
      description: "Ask questions in plain language and get answers grounded in your own documents, with the source documents cited."
    },
    {
      icon: <Bot className="h-10 w-10 text-primary mb-4" />,
      title: "Multi-Agent Assistant",
      description: "A supervisor routes each request to a retriever agent that finds information or a tagger agent that organizes your documents, then a responder writes the reply."
    },
    {
      icon: <Search className="h-10 w-10 text-primary mb-4" />,
      title: "Semantic Search",
      description: "Search by meaning, not just keywords. Results are ranked by semantic similarity, and exact title matches are included."
    },
    {
      icon: <BookOpen className="h-10 w-10 text-primary mb-4" />,
      title: "PDF Upload & Extraction",
      description: "Upload PDFs to extract their text and index it, so you can search and chat with them like any other document."
    },
    {
      icon: <FileText className="h-10 w-10 text-primary mb-4" />,
      title: "Markdown Editor",
      description: "Write documents in Markdown with live preview and auto-save as you type."
    },
    {
      icon: <Tags className="h-10 w-10 text-primary mb-4" />,
      title: "Tags & AI Tagging",
      description: "Organize documents with tags yourself, or ask the AI assistant to suggest and apply tags for you."
    },
    {
      icon: <Eye className="h-10 w-10 text-primary mb-4" />,
      title: "Public or Private",
      description: "Keep a document private to you or make it public. Only the author can edit, delete, or tag it."
    },
    {
      icon: <History className="h-10 w-10 text-primary mb-4" />,
      title: "Version History",
      description: "Snapshots are saved automatically as you edit, so the author can review earlier versions of a document."
    }
  ];

  return (
    <section id="features" className="py-20 bg-muted/30">
      <div className="container mx-auto px-4">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">What DocuMind Does</h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            A personal knowledge base you can write in, search by meaning, and talk to
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {features.map((feature, index) => (
            <div 
              key={index} 
              className="bg-card p-6 rounded-lg shadow-sm border border-border hover:shadow-md transition-all duration-300"
            >
              <div className="flex flex-col items-center text-center">
                {feature.icon}
                <h3 className="text-xl font-medium mb-2">{feature.title}</h3>
                <p className="text-muted-foreground">{feature.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
