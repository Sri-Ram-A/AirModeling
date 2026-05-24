import { Skeleton } from "@/components/ui/skeleton";

export function LoadingShell() {
  return (
    <div className="grid gap-4">
      <Skeleton className="h-24 w-full rounded-2xl" />
      <div className="grid gap-4 xl:grid-cols-3">
        <Skeleton className="h-72 rounded-2xl xl:col-span-2" />
        <Skeleton className="h-72 rounded-2xl" />
      </div>
      <Skeleton className="h-96 w-full rounded-2xl" />
    </div>
  );
}
