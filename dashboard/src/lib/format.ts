import { format, parseISO, isValid } from "date-fns";

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function formatTokens(value: number): string {
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(2)}M`;
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  return value.toString();
}

export function formatDate(dateStr: string, pattern: string = "MMM d, yyyy"): string {
  const date = parseISO(dateStr);
  if (!isValid(date)) return dateStr;
  return format(date, pattern);
}

export function formatDateTime(dateStr: string): string {
  return formatDate(dateStr, "MMM d, yyyy HH:mm");
}
