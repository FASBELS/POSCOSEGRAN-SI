interface IconProps {
  size?: number
  className?: string
  strokeWidth?: number
  style?: React.CSSProperties
}

const icon = (paths: string | string[], fill = false) =>
  ({ size = 20, className = '', strokeWidth = 1.75, style }: IconProps) => (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={fill ? 'currentColor' : 'none'}
      stroke={fill ? 'none' : 'currentColor'}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={style}
      aria-hidden="true"
    >
      {(Array.isArray(paths) ? paths : [paths]).map((d, i) => (
        <path key={i} d={d} />
      ))}
    </svg>
  )

export const IconHome = icon([
  'M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z',
  'M9 22V12h6v10',
])

export const IconClipboard = icon([
  'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2',
  'M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2',
  'M9 12h6M9 16h4',
])

export const IconPackage = icon([
  'M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z',
  'M3.27 6.96L12 12.01l8.73-5.05M12 22.08V12',
])

export const IconActivity = icon('M22 12h-4l-3 9L9 3l-3 9H2')

export const IconBook = icon([
  'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253',
])

export const IconSettings = icon([
  'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z',
  'M15 12a3 3 0 11-6 0 3 3 0 016 0z',
])

export const IconBell = icon(
  'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9'
)

export const IconUser = icon([
  'M16 7a4 4 0 11-8 0 4 4 0 018 0z',
  'M12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z',
])

export const IconChevronLeft = icon('M15 19l-7-7 7-7')
export const IconChevronRight = icon('M9 5l7 7-7 7')
export const IconChevronDown = icon('M19 9l-7 7-7-7')
export const IconChevronUp = icon('M5 15l7-7 7 7')

export const IconPlus = icon('M12 5v14M5 12h14')

export const IconDownload = icon([
  'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1',
  'M16 12l-4 4-4-4M12 3v13',
])

export const IconCalendar = icon([
  'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
])

export const IconSearch = icon('M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z')

export const IconFilter = icon(
  'M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z'
)

export const IconCheckCircle = icon([
  'M9 12l2 2 4-4',
  'M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
])

export const IconXCircle = icon([
  'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2',
  'M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
])

export const IconAlertTriangle = icon(
  'M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z'
)

export const IconInfo = icon([
  'M13 16h-1v-4h-1m1-4h.01',
  'M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
])

export const IconEye = icon([
  'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z',
  'M12 9a3 3 0 100 6 3 3 0 000-6z',
])

export const IconArrowRight = icon('M5 12h14M12 5l7 7-7 7')

export const IconX = icon('M18 6L6 18M6 6l12 12')

export const IconCheck = icon('M5 13l4 4L19 7')

export const IconMenu = icon('M4 6h16M4 12h16M4 18h16')

export const IconClock = icon([
  'M12 8v4l3 3',
  'M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
])

export const IconTrending = icon('M23 6l-9.5 9.5-5-5L1 18M17 6h6v6')

export const IconShield = icon([
  'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
])

export const IconDroplet = icon(
  'M12 2.69l5.66 5.66a8 8 0 11-11.31 0z'
)

export const IconThermometer = icon([
  'M14 14.76V3.5a2.5 2.5 0 00-5 0v11.26a4.5 4.5 0 105 0z',
])

export const IconWind = icon([
  'M9.59 4.59A2 2 0 1111 8H2m10.59 11.41A2 2 0 1014 16H2m15.73-8.27A2.5 2.5 0 1119.5 12H2',
])

export const IconExternalLink = icon([
  'M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6',
  'M15 3h6v6M10 14L21 3',
])
