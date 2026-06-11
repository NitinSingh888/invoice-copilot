import { cn, vendorColor } from '@/lib/utils'

interface VendorAvatarProps {
  vendor: string
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function VendorAvatar({ vendor, size = 'md', className }: VendorAvatarProps) {
  const color = vendorColor(vendor)
  const letter = vendor.charAt(0).toUpperCase()

  const sizeClasses = {
    sm: 'h-6 w-6 text-[10px]',
    md: 'h-8 w-8 text-xs',
    lg: 'h-10 w-10 text-sm',
  }

  return (
    <div
      className={cn(
        'flex items-center justify-center rounded-full font-semibold text-white shrink-0',
        color,
        sizeClasses[size],
        className,
      )}
    >
      {letter}
    </div>
  )
}
