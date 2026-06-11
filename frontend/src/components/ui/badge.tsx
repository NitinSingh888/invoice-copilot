import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-medium ring-1 ring-inset transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-primary/10 text-primary ring-primary/20',
        secondary: 'bg-secondary text-secondary-foreground ring-border',
        destructive: 'bg-destructive/10 text-destructive ring-destructive/20',
        outline: 'text-foreground ring-border',
        success: 'bg-success/10 text-[hsl(var(--success))] ring-success/20',
        warning: 'bg-warning/10 text-[hsl(var(--warning))] ring-warning/20',
        muted: 'bg-muted text-muted-foreground ring-border',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
