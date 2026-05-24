import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardTitle } from "@/components/ui/card";

export function ErrorState(props: { title: string; message: string; onRetry?: () => void }) {
  return (
    <Card className="border-destructive/30 bg-destructive/5">
      <CardContent className="flex flex-col gap-4 p-6">
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-destructive/10 p-2 text-destructive">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div className="min-w-0 flex-1">
            <CardTitle>{props.title}</CardTitle>
            <CardDescription className="mt-1">{props.message}</CardDescription>
          </div>
        </div>
        {props.onRetry ? (
          <div>
            <Button type="button" variant="outline" onClick={props.onRetry}>
              Retry
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
