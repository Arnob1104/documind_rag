import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDateTime } from "@/lib/utils";
import type { Document } from "@/lib/types";

interface RecentActivityProps {
  documents: Document[];
}

export default function RecentActivity({ documents }: RecentActivityProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle>Recent Activity</CardTitle>
        <CardDescription>
          Your recently updated documents
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {documents.length > 0 ? (
            documents.map((document) => (
              <div key={document.id} className="flex items-start gap-2">
                <div className="flex-1 space-y-1">
                  <p className="text-sm font-medium leading-none">{document.title}</p>
                  <div className="flex items-center pt-2">
                    <time className="text-xs text-muted-foreground">
                      {formatDateTime(document.updatedAt)}
                    </time>
                    <Badge 
                      variant="outline" 
                      className={`ml-2 text-xs ${document.isPublic ? "bg-green-500/10 text-green-700 border-green-500/20 dark:text-green-400" : ""}`}
                    >
                      {document.isPublic ? "Public" : "Private"}
                    </Badge>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground py-4 text-center">
              No recent activity
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}