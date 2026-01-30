/**
 * IR Scraper Service
 *
 * Scrapes investor relations pages to discover presentations,
 * SEC filings, and other investor documents.
 */

import axios from 'axios';
import * as cheerio from 'cheerio';

// ============================================
// Types
// ============================================

export interface IRDocument {
  id: string;
  title: string;
  url: string;
  date: string;
  dateObj: Date;
  type: 'presentation' | 'poster' | 'sec-filing' | 'webcast' | 'other';
  event?: string;
  fileSize?: string;
  fileSizeBytes?: number;
  category?: string;
  downloaded?: boolean;
  extractedText?: boolean;
}

export interface IRScraperResult {
  ticker: string;
  companyName: string;
  irBaseUrl: string;
  documents: IRDocument[];
  scrapedAt: string;
  totalDocuments: number;
  documentsByYear: Record<string, number>;
}

// ============================================
// Known IR Site Configurations
// ============================================

interface IRSiteConfig {
  baseUrl: string;
  eventsPath: string;
  downloadLibraryPath?: string;
  secFilingsPath?: string;
  newsPath?: string;
}

const IR_CONFIGS: Record<string, IRSiteConfig> = {
  ARWR: {
    baseUrl: 'https://ir.arrowheadpharma.com',
    eventsPath: '/events-and-presentations',
    downloadLibraryPath: '/download-library',
    secFilingsPath: '/financials-filings',
    newsPath: 'https://arrowheadpharma.com/newsroom/',
  },
  // Add more companies as needed
};

// ============================================
// Helper Functions
// ============================================

function parseFileSize(sizeStr: string): number {
  if (!sizeStr) return 0;
  const match = sizeStr.match(/([\d.]+)\s*(KB|MB|GB)/i);
  if (!match) return 0;
  const value = parseFloat(match[1]);
  const unit = match[2].toUpperCase();
  switch (unit) {
    case 'KB': return value * 1024;
    case 'MB': return value * 1024 * 1024;
    case 'GB': return value * 1024 * 1024 * 1024;
    default: return 0;
  }
}

function parseDate(dateStr: string): Date {
  // Handle various date formats
  const cleaned = dateStr.trim().replace(/,/g, '');
  const date = new Date(cleaned);
  if (!isNaN(date.getTime())) return date;

  // Try parsing formats like "Apr 15, 2025"
  const months: Record<string, number> = {
    jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5,
    jul: 6, aug: 7, sep: 8, sept: 8, oct: 9, nov: 10, dec: 11
  };

  const match = cleaned.match(/(\w+)\s+(\d+)\s+(\d{4})/i);
  if (match) {
    const month = months[match[1].toLowerCase().slice(0, 3)];
    if (month !== undefined) {
      return new Date(parseInt(match[3]), month, parseInt(match[2]));
    }
  }

  return new Date();
}

function inferDocumentType(title: string, url: string): IRDocument['type'] {
  const titleLower = title.toLowerCase();
  const urlLower = url.toLowerCase();

  if (titleLower.includes('poster') || urlLower.includes('poster')) return 'poster';
  if (titleLower.includes('webcast') || urlLower.includes('webcast')) return 'webcast';
  if (titleLower.includes('10-k') || titleLower.includes('10-q') || titleLower.includes('8-k')) return 'sec-filing';
  if (titleLower.includes('presentation') || titleLower.includes('corporate') ||
      titleLower.includes('conference') || titleLower.includes('congress') ||
      titleLower.includes('study') || titleLower.includes('data')) return 'presentation';

  return 'other';
}

function generateDocumentId(url: string, title: string): string {
  // Extract UUID from static-files URL or generate from title
  const uuidMatch = url.match(/static-files\/([a-f0-9-]+)/i);
  if (uuidMatch) return uuidMatch[1];

  // Generate from title
  return title.toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 50);
}

// ============================================
// Scraping Functions
// ============================================

/**
 * Scrape the download library page for documents
 * Works with ARWR's NIR widget-based IR site structure
 */
async function scrapeDownloadLibrary(config: IRSiteConfig): Promise<IRDocument[]> {
  const documents: IRDocument[] = [];
  const seenIds = new Set<string>();

  if (!config.downloadLibraryPath) return documents;

  let page = 0;
  let hasMore = true;

  while (hasMore && page <= 10) { // Max 10 pages
    try {
      const url = `${config.baseUrl}${config.downloadLibraryPath}${page > 0 ? `?page=${page}` : ''}`;
      console.log(`[IR Scraper] Fetching download library page ${page}: ${url}`);

      const response = await axios.get(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        },
        timeout: 60000,
      });

      const $ = cheerio.load(response.data);
      let foundDocs = 0;

      // ARWR uses table rows with specific NIR widget classes
      $('tr').each((_, row) => {
        const $row = $(row);

        // Get date from NIR asset date field
        const dateStr = $row.find('.field-nir-asset-date .field__item').first().text().trim();

        // Get title link from NIR asset title field
        const $titleLink = $row.find('.field-nir-asset-title a[href*="/static-files/"]').first();
        let href = $titleLink.attr('href') || '';
        let title = $titleLink.text().trim();

        // Fallback: look for any static-files link in the row
        if (!href) {
          const $anyLink = $row.find('a[href*="/static-files/"]').first();
          href = $anyLink.attr('href') || '';
          if (!title || title.length < 3) {
            title = $anyLink.text().trim();
          }
        }

        // Skip generic titles like "View Presentation" or "PDF"
        if (title && (title.toLowerCase() === 'view presentation' || title.toLowerCase() === 'pdf')) {
          // Try to get a better title from the title attribute
          const betterTitle = $row.find('a[href*="/static-files/"]').attr('title');
          if (betterTitle) {
            title = betterTitle.replace(/\.pdf$/i, '');
          }
        }

        // Get file size
        const fileSize = $row.find('.filesize').first().text().trim();

        if (href && title && title.length > 3) {
          const fullUrl = href.startsWith('http') ? href : `${config.baseUrl}${href}`;
          const id = generateDocumentId(fullUrl, title);

          if (!seenIds.has(id)) {
            seenIds.add(id);
            foundDocs++;
            documents.push({
              id,
              title: title.replace(/\s+/g, ' ').trim(),
              url: fullUrl,
              date: dateStr || 'Unknown',
              dateObj: parseDate(dateStr),
              type: inferDocumentType(title, fullUrl),
              fileSize,
              fileSizeBytes: parseFileSize(fileSize),
              category: 'download-library',
            });
          }
        }
      });

      console.log(`[IR Scraper] Found ${foundDocs} documents on page ${page}`);

      // Check for next page - look for pagination links
      const hasNextPage = $('a[href*="page="]').filter((_, el) => {
        const pageNum = $(el).attr('href')?.match(/page=(\d+)/);
        return !!(pageNum && parseInt(pageNum[1]) > page);
      }).length > 0;

      hasMore = foundDocs > 0 && hasNextPage;
      page++;

      // Rate limiting
      await new Promise(resolve => setTimeout(resolve, 500));
    } catch (error: any) {
      console.error(`[IR Scraper] Error scraping page ${page}:`, error.message);
      hasMore = false;
    }
  }

  return documents;
}

/**
 * Scrape a single year's events page
 */
async function scrapeEventsPageForYear(config: IRSiteConfig, year: number): Promise<IRDocument[]> {
  const documents: IRDocument[] = [];

  try {
    const url = `${config.baseUrl}${config.eventsPath}?year=${year}`;
    console.log(`[IR Scraper] Fetching events for ${year}: ${url}`);

    const response = await axios.get(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Cache-Control': 'no-cache',
      },
      timeout: 60000,
      maxRedirects: 5,
    });

    const $ = cheerio.load(response.data);

    // Find all event items - ARWR uses nir-widget--event structure
    $('.nir-widget--event, .module_item, .event-item, article').each((_, eventEl) => {
      const $event = $(eventEl);

      // Get event title/name
      let eventName = $event.find('.nir-widget--field--title, .module_headline, .event-title, h3, h4').first().text().trim();

      // Get date
      let dateStr = $event.find('.nir-widget--field--date, .module_date, .date, time').first().text().trim();
      if (!dateStr) {
        // Try to extract date from text content
        const eventText = $event.text();
        const dateMatch = eventText.match(/(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}/i);
        if (dateMatch) dateStr = dateMatch[0];
      }

      // Find all PDF/document links within this event
      $event.find('a[href*="/static-files/"], a[href*=".pdf"]').each((_, linkEl) => {
        const $link = $(linkEl);
        const href = $link.attr('href') || '';
        if (!href) return;

        const fullUrl = href.startsWith('http') ? href : `${config.baseUrl}${href}`;

        // Get link text as title, or use event name
        let title = $link.text().trim();
        if (!title || title.length < 3 || title.toLowerCase() === 'pdf' || title.toLowerCase() === 'download') {
          title = $link.attr('title') || $link.attr('aria-label') || eventName || 'Untitled';
        }

        // Clean up title
        title = title.replace(/\s+/g, ' ').trim();

        // Skip if we already have this URL
        if (documents.some(d => d.url === fullUrl)) return;

        documents.push({
          id: generateDocumentId(fullUrl, title),
          title,
          url: fullUrl,
          date: dateStr || `${year}`,
          dateObj: parseDate(dateStr || `Jan 1, ${year}`),
          type: inferDocumentType(title, fullUrl),
          event: eventName !== title ? eventName : undefined,
          category: 'events',
        });
      });
    });

    // Also look for standalone PDF links not in event containers
    $('a[href*="/static-files/"], a[href*=".pdf"]').each((_, el) => {
      const $link = $(el);
      const href = $link.attr('href') || '';
      if (!href) return;

      const fullUrl = href.startsWith('http') ? href : `${config.baseUrl}${href}`;

      // Skip if already found
      if (documents.some(d => d.url === fullUrl)) return;

      let title = $link.text().trim();
      if (!title || title.length < 3) {
        title = $link.attr('title') || $link.attr('aria-label') || 'Untitled';
      }

      // Try to find date from nearby elements
      let dateStr = '';
      const parent = $link.closest('tr, li, div, .row');
      parent.find('.date, time, td:contains("/"), td:contains(",")').each((_, dateEl) => {
        const text = $(dateEl).text().trim();
        if (/\d{4}/.test(text) && text.length < 30) {
          dateStr = text;
          return false;
        }
      });

      documents.push({
        id: generateDocumentId(fullUrl, title),
        title: title.replace(/\s+/g, ' ').trim(),
        url: fullUrl,
        date: dateStr || `${year}`,
        dateObj: parseDate(dateStr || `Jan 1, ${year}`),
        type: inferDocumentType(title, fullUrl),
        category: 'events',
      });
    });

    console.log(`[IR Scraper] Found ${documents.length} documents for ${year}`);
  } catch (error: any) {
    console.error(`[IR Scraper] Error scraping ${year}:`, error.message);
  }

  return documents;
}

/**
 * Scrape ALL years from events and presentations page
 */
async function scrapeEventsPage(config: IRSiteConfig): Promise<IRDocument[]> {
  const allDocuments: IRDocument[] = [];
  const currentYear = new Date().getFullYear();
  const startYear = 2015; // Go back to 2015 to capture historical presentations

  console.log(`[IR Scraper] Scraping events from ${startYear} to ${currentYear}...`);

  // Scrape each year sequentially to avoid rate limiting
  for (let year = currentYear; year >= startYear; year--) {
    const yearDocs = await scrapeEventsPageForYear(config, year);
    allDocuments.push(...yearDocs);

    // Rate limiting between years
    if (year > startYear) {
      await new Promise(resolve => setTimeout(resolve, 800));
    }
  }

  console.log(`[IR Scraper] Total events documents found: ${allDocuments.length}`);
  return allDocuments;
}

// ============================================
// Main Scraper Function
// ============================================

/**
 * Scrape all IR documents for a company
 */
export async function scrapeIRDocuments(ticker: string): Promise<IRScraperResult> {
  const config = IR_CONFIGS[ticker.toUpperCase()];

  if (!config) {
    throw new Error(`No IR configuration found for ticker: ${ticker}`);
  }

  console.log(`[IR Scraper] Starting scrape for ${ticker}...`);

  // Scrape all sources
  const [downloadDocs, eventDocs] = await Promise.all([
    scrapeDownloadLibrary(config),
    scrapeEventsPage(config),
  ]);

  // Merge and dedupe
  const allDocs = [...downloadDocs, ...eventDocs];
  const uniqueDocs = new Map<string, IRDocument>();

  for (const doc of allDocs) {
    const existing = uniqueDocs.get(doc.id);
    if (!existing || doc.fileSize) {
      uniqueDocs.set(doc.id, doc);
    }
  }

  const documents = Array.from(uniqueDocs.values())
    .sort((a, b) => b.dateObj.getTime() - a.dateObj.getTime());

  // Calculate stats
  const documentsByYear: Record<string, number> = {};
  for (const doc of documents) {
    const year = doc.dateObj.getFullYear().toString();
    documentsByYear[year] = (documentsByYear[year] || 0) + 1;
  }

  console.log(`[IR Scraper] Completed scrape for ${ticker}: ${documents.length} unique documents`);

  return {
    ticker: ticker.toUpperCase(),
    companyName: getCompanyName(ticker),
    irBaseUrl: config.baseUrl,
    documents,
    scrapedAt: new Date().toISOString(),
    totalDocuments: documents.length,
    documentsByYear,
  };
}

/**
 * Get company name from ticker
 */
function getCompanyName(ticker: string): string {
  const names: Record<string, string> = {
    ARWR: 'Arrowhead Pharmaceuticals',
  };
  return names[ticker.toUpperCase()] || ticker;
}

/**
 * Get list of supported tickers
 */
export function getSupportedTickers(): string[] {
  return Object.keys(IR_CONFIGS);
}

/**
 * Check if a ticker is supported
 */
export function isTickerSupported(ticker: string): boolean {
  return ticker.toUpperCase() in IR_CONFIGS;
}

/**
 * Scrape ALL presentations for a company (convenience function)
 */
export async function scrapeAllPresentations(ticker: string): Promise<{
  ticker: string;
  totalPresentations: number;
  presentations: IRDocument[];
  byYear: Record<string, number>;
  byType: Record<string, number>;
}> {
  const result = await scrapeIRDocuments(ticker);

  // Filter to just presentations (exclude webcasts, SEC filings)
  const presentations = result.documents.filter(
    d => d.type === 'presentation' || d.type === 'poster' || d.url.includes('/static-files/')
  );

  // Count by year
  const byYear: Record<string, number> = {};
  for (const doc of presentations) {
    const year = doc.dateObj.getFullYear().toString();
    byYear[year] = (byYear[year] || 0) + 1;
  }

  // Count by type
  const byType: Record<string, number> = {};
  for (const doc of presentations) {
    byType[doc.type] = (byType[doc.type] || 0) + 1;
  }

  return {
    ticker: ticker.toUpperCase(),
    totalPresentations: presentations.length,
    presentations,
    byYear,
    byType,
  };
}
