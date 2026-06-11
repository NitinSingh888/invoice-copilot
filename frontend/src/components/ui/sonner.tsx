import { Toaster as Sonner, type ToasterProps } from 'sonner'

function Toaster({ ...props }: ToasterProps) {
  return (
    <Sonner
      theme="system"
      className="toaster group"
      style={{
        '--normal-bg': 'hsl(var(--card))',
        '--normal-border': 'hsl(var(--border))',
        '--normal-text': 'hsl(var(--card-foreground))',
      } as React.CSSProperties}
      {...props}
    />
  )
}

export { Toaster }
