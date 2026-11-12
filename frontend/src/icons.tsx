type IconProps = { filled?: boolean; className?: string; size?: number }

export function HeartIcon({ filled, className, size = 28 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className={className}
         fill={filled ? '#e11d48' : 'none'} stroke={filled ? '#e11d48' : 'currentColor'} strokeWidth="2">
      <path d="M12 21s-7-4.5-9.5-9C.5 8 2.5 4 6.5 4c2 0 3.5 1 5.5 3 2-2 3.5-3 5.5-3 4 0 6 4 4 8-2.5 4.5-9.5 9-9.5 9z" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}

export function ThumbDownIcon({ filled, className, size = 28 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className={className}
         fill={filled ? '#6b7280' : 'none'} stroke={filled ? '#6b7280' : 'currentColor'} strokeWidth="2">
      <path d="M17 14V4M17 14l-4 7a2 2 0 0 1-2-2v-3H5a2 2 0 0 1-2-2.3l1.2-6A2 2 0 0 1 6.2 6H17" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}

export function CheckCircleIcon({ filled, className, size = 28 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className={className}
         fill={filled ? '#16a34a' : 'none'} stroke={filled ? '#16a34a' : 'currentColor'} strokeWidth="2">
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12l3 3 5-6" fill="none" stroke={filled ? '#fff' : 'currentColor'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function ChevronRightIcon({ className, size = 28 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className={className}
         fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 6l6 6-6 6" />
    </svg>
  )
}