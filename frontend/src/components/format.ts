export function timeAgo(iso: string): string {
  const s = Math.max(1, Math.round((Date.now() - new Date(iso).getTime()) / 1000))
  const steps: [number, string][] = [[60, 'second'], [60, 'minute'], [24, 'hour'], [30, 'day'], [12, 'month']]
  let value = s
  for (const [size, unit] of steps) {
    if (value < size) return `${value} ${unit}${value === 1 ? '' : 's'} ago`
    value = Math.floor(value / size)
  }
  return `${value} year${value === 1 ? '' : 's'} ago`
}

export const RECENCY_LABEL: Record<string, string> = {
  '30d': 'last 30 days', '3m': 'last 3 months', '6m': 'last 6 months', '6m+': 'more than 6 months ago',
}
