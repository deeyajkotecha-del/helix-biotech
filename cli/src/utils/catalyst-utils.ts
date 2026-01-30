/**
 * Catalyst utility functions for time-aware catalyst management
 */

import { Catalyst } from '../types/company';

/**
 * Parse a catalyst date string to a Date object
 * Handles ISO dates (2026-03-28) and quarterly estimates (2026-Q3, 2026-06-30)
 */
export function parseCatalystDate(dateStr: string): Date {
  // Handle quarterly format like "2026-Q3"
  const quarterMatch = dateStr.match(/^(\d{4})-Q(\d)$/);
  if (quarterMatch) {
    const year = parseInt(quarterMatch[1]);
    const quarter = parseInt(quarterMatch[2]);
    // Q1 = Jan 1, Q2 = Apr 1, Q3 = Jul 1, Q4 = Oct 1
    const month = (quarter - 1) * 3;
    return new Date(year, month, 1);
  }

  // Handle half-year format like "H1 2026" or "H2 2025"
  const halfMatch = dateStr.match(/^H(\d)\s+(\d{4})$/);
  if (halfMatch) {
    const half = parseInt(halfMatch[1]);
    const year = parseInt(halfMatch[2]);
    // H1 = Jan 1, H2 = Jul 1
    return new Date(year, half === 1 ? 0 : 6, 1);
  }

  // Standard ISO date parsing
  return new Date(dateStr);
}

/**
 * Get the next upcoming catalyst (first catalyst where date > today)
 */
export function getNextCatalyst(catalysts: Catalyst[]): Catalyst | null {
  const now = new Date();
  now.setHours(0, 0, 0, 0); // Normalize to start of day

  const upcomingCatalysts = catalysts
    .filter(c => c.status === 'upcoming')
    .filter(c => parseCatalystDate(c.date) >= now)
    .sort((a, b) => parseCatalystDate(a.date).getTime() - parseCatalystDate(b.date).getTime());

  return upcomingCatalysts[0] || null;
}

/**
 * Get all completed/past catalysts
 */
export function getPastCatalysts(catalysts: Catalyst[]): Catalyst[] {
  return catalysts
    .filter(c => c.status === 'completed')
    .sort((a, b) => parseCatalystDate(b.date).getTime() - parseCatalystDate(a.date).getTime());
}

/**
 * Get all upcoming catalysts (future events)
 */
export function getUpcomingCatalysts(catalysts: Catalyst[]): Catalyst[] {
  const now = new Date();
  now.setHours(0, 0, 0, 0);

  return catalysts
    .filter(c => c.status === 'upcoming')
    .filter(c => parseCatalystDate(c.date) >= now)
    .sort((a, b) => parseCatalystDate(a.date).getTime() - parseCatalystDate(b.date).getTime());
}

/**
 * Get high-importance upcoming catalysts
 */
export function getHighPriorityCatalysts(catalysts: Catalyst[]): Catalyst[] {
  return getUpcomingCatalysts(catalysts).filter(c => c.importance === 'high');
}

/**
 * Format a catalyst date for display
 * Examples: "Mar 28, 2026", "Q3 2026", "H1 2026"
 */
export function formatCatalystDate(dateStr: string): string {
  // Handle quarterly format
  const quarterMatch = dateStr.match(/^(\d{4})-Q(\d)$/);
  if (quarterMatch) {
    return `Q${quarterMatch[2]} ${quarterMatch[1]}`;
  }

  // Handle half-year format
  const halfMatch = dateStr.match(/^H(\d)\s+(\d{4})$/);
  if (halfMatch) {
    return `H${halfMatch[1]} ${halfMatch[2]}`;
  }

  // Parse and format standard date
  const date = new Date(dateStr);

  // Check if it's a quarter-end date (Mar 31, Jun 30, Sep 30, Dec 31)
  const month = date.getMonth();
  const day = date.getDate();

  if ((month === 2 && day === 31) || (month === 5 && day === 30) ||
      (month === 8 && day === 30) || (month === 11 && day === 31)) {
    const quarter = Math.floor(month / 3) + 1;
    return `Q${quarter} ${date.getFullYear()}`;
  }

  // Check if it's a half-year end (Jun 30 or Dec 31)
  if ((month === 5 && day === 30)) {
    return `H1 ${date.getFullYear()}`;
  }
  if ((month === 11 && day === 31)) {
    return `H2 ${date.getFullYear()}`;
  }

  // Format as specific date
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[month]} ${day}, ${date.getFullYear()}`;
}

/**
 * Format catalyst date in short form for cards
 * Examples: "Mar 2026", "Q3 2026", "H1 2026"
 */
export function formatCatalystDateShort(dateStr: string): string {
  // Handle quarterly format
  const quarterMatch = dateStr.match(/^(\d{4})-Q(\d)$/);
  if (quarterMatch) {
    return `Q${quarterMatch[2]} ${quarterMatch[1]}`;
  }

  // Handle half-year format
  const halfMatch = dateStr.match(/^H(\d)\s+(\d{4})$/);
  if (halfMatch) {
    return `H${halfMatch[1]} ${halfMatch[2]}`;
  }

  const date = new Date(dateStr);
  const month = date.getMonth();
  const day = date.getDate();
  const year = date.getFullYear();

  // Check if it's a quarter-end date - return quarter format
  if ((month === 2 && day === 31) || (month === 5 && day === 30) ||
      (month === 8 && day === 30) || (month === 11 && day === 31)) {
    const quarter = Math.floor(month / 3) + 1;
    return `Q${quarter} ${year}`;
  }

  // For specific dates, return "Mon YYYY" format
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[month]} ${year}`;
}

/**
 * Get time until catalyst in human-readable form
 */
export function getTimeUntilCatalyst(dateStr: string): string {
  const now = new Date();
  const catalystDate = parseCatalystDate(dateStr);
  const diffMs = catalystDate.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays < 0) {
    return 'Past';
  } else if (diffDays === 0) {
    return 'Today';
  } else if (diffDays === 1) {
    return 'Tomorrow';
  } else if (diffDays <= 7) {
    return `${diffDays} days`;
  } else if (diffDays <= 30) {
    const weeks = Math.ceil(diffDays / 7);
    return `${weeks} week${weeks > 1 ? 's' : ''}`;
  } else if (diffDays <= 365) {
    const months = Math.ceil(diffDays / 30);
    return `${months} month${months > 1 ? 's' : ''}`;
  } else {
    const years = Math.floor(diffDays / 365);
    return `${years} year${years > 1 ? 's' : ''}`;
  }
}

/**
 * Check if a catalyst is imminent (within 30 days)
 */
export function isImminentCatalyst(dateStr: string): boolean {
  const now = new Date();
  const catalystDate = parseCatalystDate(dateStr);
  const diffMs = catalystDate.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
  return diffDays >= 0 && diffDays <= 30;
}

/**
 * Generate catalyst display text for company card
 */
export function getCatalystDisplayText(catalyst: Catalyst): string {
  const dateText = formatCatalystDateShort(catalyst.date);
  // Extract key part of event name (remove drug name if at start)
  let eventText = catalyst.event;
  if (catalyst.drug && eventText.toLowerCase().startsWith(catalyst.drug.toLowerCase())) {
    eventText = eventText.substring(catalyst.drug.length).trim();
    if (eventText.startsWith('-')) eventText = eventText.substring(1).trim();
  }
  // Truncate if too long
  if (eventText.length > 40) {
    eventText = eventText.substring(0, 37) + '...';
  }
  return `${eventText} (${dateText})`;
}
