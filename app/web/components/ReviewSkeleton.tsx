"use client";

import { Skeleton } from "./Skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export function ReviewSkeleton() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header Skeleton */}
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-4">
            <Skeleton className="h-9 w-32" />
            <Skeleton className="h-6 w-40" />
          </div>
          <div className="flex items-center gap-4">
            <Skeleton className="h-5 w-24" />
            <Skeleton className="h-9 w-28" />
          </div>
        </div>
      </header>

      <main className="container py-6">
        <div className="grid grid-cols-12 gap-6">
          {/* Sidebar Skeleton */}
          <div className="col-span-4 space-y-4">
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2 mb-3">
                  <Skeleton className="h-8 w-full" />
                </div>
                <Skeleton className="h-8 w-full" />
              </CardHeader>
            </Card>

            {/* Question list skeleton */}
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <Card key={i}>
                  <CardContent className="p-3">
                    <div className="flex items-start gap-2">
                      <Skeleton className="h-5 w-5 rounded-full" />
                      <div className="flex-1 min-w-0 space-y-2">
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-4 w-3/4" />
                        <div className="flex items-center gap-2 mt-2">
                          <Skeleton className="h-5 w-16" />
                          <Skeleton className="h-4 w-20" />
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Main Content Skeleton */}
          <div className="col-span-8">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Skeleton className="h-5 w-20" />
                    <Skeleton className="h-4 w-32" />
                  </div>
                  <div className="flex items-center gap-2">
                    <Skeleton className="h-8 w-8" />
                    <Skeleton className="h-8 w-8" />
                  </div>
                </div>
                <Skeleton className="h-6 w-full mt-4" />
                <Skeleton className="h-6 w-2/3 mt-2" />
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-muted/50 rounded-lg p-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <Skeleton className="h-4 w-4" />
                    <Skeleton className="h-4 w-40" />
                    <Skeleton className="h-5 w-24 ml-auto" />
                  </div>
                  <Skeleton className="h-32 w-full" />
                </div>

                <div className="space-y-2">
                  <Skeleton className="h-4 w-16" />
                  <div className="flex flex-wrap gap-2">
                    <Skeleton className="h-6 w-24" />
                    <Skeleton className="h-6 w-32" />
                    <Skeleton className="h-6 w-20" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
