/**
 * Pharma Company Registry
 *
 * Registry of 13 major pharma companies with SEC CIK numbers,
 * IR page URLs, presentation URL patterns, and verification status.
 */

import { PharmaCompany } from '../types/pharma';

// ============================================
// Company Registry
// ============================================

export const PHARMA_COMPANIES: Record<string, PharmaCompany> = {
  MRK: {
    ticker: 'MRK',
    name: 'Merck & Co.',
    cik: '0000310158',
    irPageUrl: 'https://www.merck.com/investor-relations/',
    cdnBase: 'https://s21.q4cdn.com/488056881/files/doc_presentations/',
    urlPatterns: {
      jpm: 'https://s21.q4cdn.com/488056881/files/doc_presentations/{year}-JPM-Presentation.pdf',
      quarterly: 'https://s21.q4cdn.com/488056881/files/doc_presentations/{year}-Q{quarter}-Earnings.pdf',
    },
    verified: true,
  },
  PFE: {
    ticker: 'PFE',
    name: 'Pfizer Inc.',
    cik: '0000078003',
    irPageUrl: 'https://investors.pfizer.com/',
    cdnBase: 'https://s28.q4cdn.com/781576035/files/doc_presentations/',
    urlPatterns: {
      jpm: 'https://s28.q4cdn.com/781576035/files/doc_presentations/{year}-JPM-Healthcare-Conference.pdf',
    },
    verified: true,
  },
  JNJ: {
    ticker: 'JNJ',
    name: 'Johnson & Johnson',
    cik: '0000200406',
    irPageUrl: 'https://www.investor.jnj.com/',
    verified: false,
  },
  LLY: {
    ticker: 'LLY',
    name: 'Eli Lilly and Company',
    cik: '0000059478',
    irPageUrl: 'https://investor.lilly.com/',
    verified: false,
  },
  ABBV: {
    ticker: 'ABBV',
    name: 'AbbVie Inc.',
    cik: '0001551152',
    irPageUrl: 'https://investors.abbvie.com/',
    verified: false,
  },
  BMY: {
    ticker: 'BMY',
    name: 'Bristol-Myers Squibb',
    cik: '0000014272',
    irPageUrl: 'https://www.bms.com/investors.html',
    cdnBase: 'https://s21.q4cdn.com/104322789/files/doc_presentations/',
    urlPatterns: {
      jpm: 'https://s21.q4cdn.com/104322789/files/doc_presentations/{year}-JPM-Healthcare-Conference.pdf',
    },
    verified: true,
  },
  AMGN: {
    ticker: 'AMGN',
    name: 'Amgen Inc.',
    cik: '0000318154',
    irPageUrl: 'https://investors.amgen.com/',
    verified: false,
  },
  GILD: {
    ticker: 'GILD',
    name: 'Gilead Sciences',
    cik: '0000882095',
    irPageUrl: 'https://investors.gilead.com/',
    verified: false,
  },
  AZN: {
    ticker: 'AZN',
    name: 'AstraZeneca',
    cik: '0000901832',
    irPageUrl: 'https://www.astrazeneca.com/investor-relations.html',
    cdnBase: 'https://www.astrazeneca.com/content/dam/az/Investor_Relations/',
    urlPatterns: {
      jpm: 'https://www.astrazeneca.com/content/dam/az/Investor_Relations/JPM-{year}-presentation.pdf',
    },
    verified: true,
  },
  NVS: {
    ticker: 'NVS',
    name: 'Novartis AG',
    cik: '0001114448',
    irPageUrl: 'https://www.novartis.com/investors',
    verified: false,
  },
  SNY: {
    ticker: 'SNY',
    name: 'Sanofi',
    cik: '0001121404',
    irPageUrl: 'https://www.sanofi.com/en/investors',
    verified: false,
  },
  GSK: {
    ticker: 'GSK',
    name: 'GSK plc',
    cik: '0001131399',
    irPageUrl: 'https://www.gsk.com/en-gb/investors/',
    verified: false,
  },
  RHHBY: {
    ticker: 'RHHBY',
    name: 'Roche Holding AG',
    cik: '0001140262',
    irPageUrl: 'https://www.roche.com/investors',
    verified: false,
  },
};

// ============================================
// Helper Functions
// ============================================

/**
 * Get all registered ticker symbols
 */
export function getAllTickers(): string[] {
  return Object.keys(PHARMA_COMPANIES);
}

/**
 * Get only companies with verified IR URL patterns
 */
export function getVerifiedCompanies(): PharmaCompany[] {
  return Object.values(PHARMA_COMPANIES).filter((c) => c.verified);
}

/**
 * Build a presentation URL from a company's URL pattern
 */
export function buildPresentationUrl(
  ticker: string,
  type: 'jpm' | 'quarterly' | 'annual',
  params: { year: number; quarter?: number }
): string | null {
  const company = PHARMA_COMPANIES[ticker.toUpperCase()];
  if (!company?.urlPatterns?.[type]) return null;

  let url = company.urlPatterns[type]!;
  url = url.replace('{year}', String(params.year));
  if (params.quarter !== undefined) {
    url = url.replace('{quarter}', String(params.quarter));
  }
  return url;
}

/**
 * Get JPM presentation URLs for a given year across all verified companies
 */
export function getJPM2026Urls(): { ticker: string; name: string; url: string | null }[] {
  return getVerifiedCompanies().map((company) => ({
    ticker: company.ticker,
    name: company.name,
    url: buildPresentationUrl(company.ticker, 'jpm', { year: 2026 }),
  }));
}

/**
 * Get SEC EDGAR URL for a company
 */
export function getSecEdgarUrl(ticker: string): string | null {
  const company = PHARMA_COMPANIES[ticker.toUpperCase()];
  if (!company) return null;
  return `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${company.cik}&type=10-K&dateb=&owner=include&count=40`;
}
