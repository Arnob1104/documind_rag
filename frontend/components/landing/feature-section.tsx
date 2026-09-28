import { 
  FileText, 
  Search, 
  Tags, 
  Eye, 
  EyeOff,
  Smartphone, 
  Laptop,
  BookOpen,
  History,
  SunMoon,
  AlertCircle
} from "lucide-react";

export function FeatureSection() {
  const features = [
    {
      icon: <FileText className="h-10 w-10 text-primary mb-4" />,
      title: "Markdown Editor",
      description: "Create and edit documents with a powerful Markdown editor including live preview."
    },
    {
      icon: <Search className="h-10 w-10 text-primary mb-4" />,
      title: "Advanced Search",
      description: "Find your documents instantly with our fuzzy matching and relevance ranking search engine."
    },
    {
      icon: <BookOpen className="h-10 w-10 text-primary mb-4" />,
      title: "PDF Extraction",
      description: "Extract and index text from PDF documents for seamless integration into your knowledge base."
    },
    {
      icon: <Tags className="h-10 w-10 text-primary mb-4" />,
      title: "Tag Organization",
      description: "Organize your documents with a flexible tagging system for easy categorization and filtering."
    },
    {
      icon: <Eye className="h-10 w-10 text-primary mb-4" />,
      title: "Visibility Control",
      description: "Choose which documents are public or private with granular visibility controls."
    },
    {
      icon: <Smartphone className="h-10 w-10 text-primary mb-4" />,
      title: "Responsive Design",
      description: "Access your knowledge base from any device with our fully responsive interface."
    },
    {
      icon: <History className="h-10 w-10 text-primary mb-4" />,
      title: "Version History",
      description: "Track changes to your documents with automatic versioning and timestamps."
    },
    {
      icon: <SunMoon className="h-10 w-10 text-primary mb-4" />,
      title: "Light & Dark Mode",
      description: "Switch between light and dark themes to reduce eye strain and work comfortably any time."
    }
  ];

  return (
    <section id="features" className="py-20 bg-muted/30">
      <div className="container mx-auto px-4">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Powerful Features</h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            DocuMind combines advanced document management with powerful search capabilities
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