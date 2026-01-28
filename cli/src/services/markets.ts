/**
 * Markets Service
 *
 * Extracts market size and growth data from SEC filings,
 * analyst reports, and other sources.
 */

import { Market, Region } from '../types/schema';

// ============================================
// Main Functions
// ============================================

/**
 * Get market data for an indication
 * TODO: Implement SEC filing extraction
 * TODO: Add analyst report parsing
 */
export async function getMarketData(
  indication: string,
  region?: Region,
  year?: number
): Promise<Market | null> {
  // TODO: Search cache first
  // TODO: Search SEC filings
  // TODO: Search analyst estimates
  throw new Error('Not implemented');
}

/**
 * Get market projections for an indication
 */
export async function getMarketProjections(
  indication: string,
  startYear: number,
  endYear: number
): Promise<{
  year: number;
  sizeBillion: number;
  source: string;
}[]> {
  // TODO: Implement
  throw new Error('Not implemented');
}

/**
 * Get market leaders for an indication
 */
export async function getMarketLeaders(
  indication: string
): Promise<{
  company: string;
  drug: string;
  marketSharePct: number;
  revenueBillion: number;
}[]> {
  // TODO: Extract from SEC filings
  // TODO: Calculate market share
  throw new Error('Not implemented');
}

/**
 * Search SEC filings for market size mentions
 */
export async function searchFilingsForMarketData(
  indication: string,
  options?: {
    formTypes?: string[];  // ['10-K', '10-Q', 'S-1']
    daysBack?: number;
  }
): Promise<{
  ticker: string;
  filingDate: string;
  marketSize: number;
  year: number;
  context: string;
}[]> {
  // TODO: Search SEC EDGAR
  // TODO: Extract market size mentions
  throw new Error('Not implemented');
}

// ============================================
// SEC Filing Analysis
// ============================================

/**
 * Extract market size from filing text
 */
export function extractMarketSize(text: string): {
  value: number;
  unit: 'billion' | 'million';
  year?: number;
  region?: string;
}[] {
  const results: { value: number; unit: 'billion' | 'million'; year?: number; region?: string }[] = [];

  // Pattern: "$X billion market" or "market of $X billion"
  const patterns = [
    /\$?([\d.]+)\s*(billion|million)\s+(?:market|opportunity|TAM)/gi,
    /(?:market|opportunity|TAM)\s+(?:of|worth|valued at)\s+\$?([\d.]+)\s*(billion|million)/gi,
    /(?:addressable market|total market)\s+(?:is|of|estimated at)\s+\$?([\d.]+)\s*(billion|million)/gi,
  ];

  for (const pattern of patterns) {
    let match;
    while ((match = pattern.exec(text)) !== null) {
      results.push({
        value: parseFloat(match[1]),
        unit: match[2].toLowerCase() as 'billion' | 'million',
      });
    }
  }

  return results;
}

/**
 * Extract growth rate from filing text
 */
export function extractGrowthRate(text: string): number | null {
  const patterns = [
    /(?:CAGR|growth rate|growing at)\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*%/gi,
    /(\d+(?:\.\d+)?)\s*%\s+(?:CAGR|growth|annual growth)/gi,
  ];

  for (const pattern of patterns) {
    const match = pattern.exec(text);
    if (match) {
      return parseFloat(match[1]);
    }
  }

  return null;
}

/**
 * Extract patient population from text
 */
export function extractPatientPopulation(text: string): number | null {
  const patterns = [
    /([\d.]+)\s*(million|thousand)\s+(?:patients|people|individuals)\s+(?:affected|diagnosed|living with)/gi,
    /(?:affects|affects approximately|prevalence of)\s+([\d.]+)\s*(million|thousand)/gi,
  ];

  for (const pattern of patterns) {
    const match = pattern.exec(text);
    if (match) {
      const value = parseFloat(match[1]);
      const multiplier = match[2].toLowerCase() === 'million' ? 1000000 : 1000;
      return value * multiplier;
    }
  }

  return null;
}

// ============================================
// Market Comparison
// ============================================

/**
 * Compare market sizes across indications
 */
export async function compareMarkets(
  indications: string[]
): Promise<{
  indication: string;
  sizeBillion: number;
  growthRate: number;
}[]> {
  // TODO: Fetch data for each indication
  // TODO: Sort by size
  throw new Error('Not implemented');
}

/**
 * Get largest markets in a therapeutic area
 */
export async function getLargestMarkets(
  therapeuticArea: string,
  limit?: number
): Promise<Market[]> {
  // TODO: Implement
  throw new Error('Not implemented');
}

/**
 * Get fastest growing markets
 */
export async function getFastestGrowingMarkets(
  minSizeBillion?: number,
  limit?: number
): Promise<Market[]> {
  // TODO: Implement
  throw new Error('Not implemented');
}

// ============================================
// Revenue Analysis
// ============================================

/**
 * Extract drug revenue from SEC filings
 */
export async function extractDrugRevenue(
  ticker: string,
  drugName: string
): Promise<{
  year: number;
  quarter?: number;
  revenueMillion: number;
  growth?: number;
}[]> {
  // TODO: Fetch 10-K/10-Q filings
  // TODO: Parse revenue tables
  throw new Error('Not implemented');
}

/**
 * Build revenue timeline for a drug
 */
export async function buildRevenueTimeline(
  drugName: string
): Promise<{
  year: number;
  globalRevenue: number;
  byRegion: Record<Region, number>;
}[]> {
  // TODO: Aggregate from multiple company filings
  throw new Error('Not implemented');
}

// ============================================
// Market Sizing Models
// ============================================

/**
 * Estimate market size using prevalence model
 */
export function estimateMarketFromPrevalence(
  prevalence: number,           // Number of patients
  treatmentRate: number,        // % who receive treatment
  annualCostPerPatient: number  // Average annual cost
): number {
  return (prevalence * treatmentRate * annualCostPerPatient) / 1e9; // Returns billions
}

/**
 * Project market growth
 */
export function projectMarketGrowth(
  currentSize: number,
  cagr: number,
  years: number
): { year: number; size: number }[] {
  const projections: { year: number; size: number }[] = [];
  const currentYear = new Date().getFullYear();

  for (let i = 0; i <= years; i++) {
    projections.push({
      year: currentYear + i,
      size: currentSize * Math.pow(1 + cagr / 100, i)
    });
  }

  return projections;
}

// ============================================
// Utility
// ============================================

/**
 * Normalize indication name for matching
 */
export function normalizeIndicationName(indication: string): string {
  return indication
    .toLowerCase()
    .replace(/['']/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Match indication variations
 */
export function matchIndication(query: string, target: string): boolean {
  const q = normalizeIndicationName(query);
  const t = normalizeIndicationName(target);

  // Exact match
  if (q === t) return true;

  // Partial match
  if (t.includes(q) || q.includes(t)) return true;

  // Common abbreviations
  const abbreviations: Record<string, string[]> = {
    'ulcerative colitis': ['uc', 'ibd'],
    'crohns disease': ['crohn', 'cd', 'ibd'],
    'rheumatoid arthritis': ['ra'],
    'psoriatic arthritis': ['psa'],
    'multiple sclerosis': ['ms'],
    'non-small cell lung cancer': ['nsclc'],
    'small cell lung cancer': ['sclc'],
  };

  for (const [full, abbrevs] of Object.entries(abbreviations)) {
    if (q === full && abbrevs.includes(t)) return true;
    if (t === full && abbrevs.includes(q)) return true;
  }

  return false;
}
