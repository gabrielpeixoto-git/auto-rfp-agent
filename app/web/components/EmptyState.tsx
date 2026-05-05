"use client";

import { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  actionHref?: string;
  onAction?: () => void;
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  actionHref,
  onAction,
  secondaryAction,
}: EmptyStateProps) {
  return (
    <Card className="border-dashed border-border/50 bg-gradient-to-b from-muted/30 to-background">
      <CardContent className="flex flex-col items-center justify-center py-16 px-4 text-center">
        {/* Icon with gradient background */}
        <div className="relative mb-6">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/20 to-primary/5 rounded-2xl blur-xl" />
          <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5 ring-1 ring-primary/20 shadow-lg shadow-primary/10">
            <Icon className="h-8 w-8 text-primary" />
          </div>
        </div>
        
        {/* Title with better typography */}
        <h3 className="text-xl font-semibold tracking-tight text-foreground mb-3">
          {title}
        </h3>
        
        {/* Description with max-width and line-height */}
        <p className="text-sm text-muted-foreground max-w-sm mb-8 leading-relaxed">
          {description}
        </p>
        
        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
          {actionLabel && (actionHref || onAction) && (
            <Button
              onClick={onAction}
              asChild={!!actionHref}
              className="bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary shadow-lg shadow-primary/25 transition-all duration-200"
            >
              {actionHref ? (
                <a href={actionHref}>{actionLabel}</a>
              ) : (
                actionLabel
              )}
            </Button>
          )}
          {secondaryAction && (
            <Button 
              variant="outline" 
              onClick={secondaryAction.onClick}
              className="border-border/50 hover:bg-accent transition-colors"
            >
              {secondaryAction.label}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function EmptyStateCompact({
  icon: Icon,
  title,
  description,
}: Omit<EmptyStateProps, "actionLabel" | "actionHref" | "onAction" | "secondaryAction">) {
  return (
    <div className="flex flex-col items-center justify-center py-10 px-4 text-center">
      {/* Subtle icon container */}
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted mb-4">
        <Icon className="h-6 w-6 text-muted-foreground/70" />
      </div>
      <h3 className="text-base font-semibold text-foreground mb-1.5">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-xs leading-relaxed">{description}</p>
    </div>
  );
}
