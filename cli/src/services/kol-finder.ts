/**
 * KOL Finder Service
 * Orchestrates PubMed and ClinicalTrials.gov data to find Key Opinion Leaders
 */

import { searchPubMedAuthors, PubMedAuthor, extractInstitutionName } from './pubmed-authors';
import { searchTrialInvestigators, TrialInvestigator } from './trial-investigators';
import { findEmailsForKOLs, findEmailBySearch } from './email-finder';

export { findEmailBySearch };

export interface KOL {
  name: string;
  firstName: string;
  lastName: string;
  institution: string;
  country: string;
  email: string | null;
  publicationCount: number;
  trialCount: number;
  role: 'PI' | 'Author' | 'PI + Author';
  score: number;
  publications: Array<{
    pmid: string;
    title: string;
    journal: string;
    year: string;
  }>;
  trials: Array<{
    nctId: string;
    title: string;
    phase: string;
    status: string;
  }>;
}

export interface KOLSearchResult {
  query: string;
  totalKOLs: number;
  kols: KOL[];
  searchTime: number;
}

/**
 * Main KOL search function
 * Combines PubMed authors and ClinicalTrials.gov investigators
 */
export async function findKOLs(
  query: string,
  options: {
    minPublications?: number;
    country?: string;
    roleFilter?: 'all' | 'pi' | 'author';
    maxResults?: number;
  } = {}
): Promise<KOLSearchResult> {
  const startTime = Date.now();
  const {
    minPublications = 0,
    country = '',
    roleFilter = 'all',
    maxResults = 50,
  } = options;

  // Run both searches in parallel
  const [pubmedAuthors, trialInvestigators] = await Promise.all([
    searchPubMedAuthors(query, 100),
    searchTrialInvestigators(query, 100),
  ]);

  // Merge and deduplicate results
  const kolMap = new Map<string, KOL>();

  // Process PubMed authors
  for (const author of pubmedAuthors) {
    const key = normalizeKey(author.lastName, author.firstName);

    kolMap.set(key, {
      name: author.name,
      firstName: author.firstName,
      lastName: author.lastName,
      institution: author.affiliation,
      country: author.country,
      email: author.email,
      publicationCount: author.publicationCount,
      trialCount: 0,
      role: 'Author',
      score: 0,
      publications: author.publications.slice(0, 10).map(p => ({
        pmid: p.pmid,
        title: p.title,
        journal: p.journal,
        year: p.year,
      })),
      trials: [],
    });
  }

  // Merge trial investigators
  for (const investigator of trialInvestigators) {
    const key = normalizeKey(investigator.lastName, investigator.firstName);

    if (kolMap.has(key)) {
      // Merge with existing author
      const existing = kolMap.get(key)!;
      existing.trialCount = investigator.trialCount;
      existing.role = 'PI + Author';
      existing.trials = investigator.trials.slice(0, 10).map(t => ({
        nctId: t.nctId,
        title: t.title,
        phase: t.phase,
        status: t.status,
      }));
      // Update institution if we have better data
      if (!existing.institution && investigator.affiliation) {
        existing.institution = investigator.affiliation;
      }
      // Update country if missing
      if (!existing.country && investigator.country) {
        existing.country = investigator.country;
      }
    } else {
      // Add new investigator
      kolMap.set(key, {
        name: investigator.name,
        firstName: investigator.firstName,
        lastName: investigator.lastName,
        institution: investigator.affiliation,
        country: investigator.country,
        email: null,
        publicationCount: 0,
        trialCount: investigator.trialCount,
        role: 'PI',
        score: 0,
        publications: [],
        trials: investigator.trials.slice(0, 10).map(t => ({
          nctId: t.nctId,
          title: t.title,
          phase: t.phase,
          status: t.status,
        })),
      });
    }
  }

  // Calculate scores and filter
  let kols = Array.from(kolMap.values());

  // Shorten institution names
  for (const kol of kols) {
    kol.institution = extractInstitutionName(kol.institution);
  }

  // Calculate score for each KOL
  for (const kol of kols) {
    kol.score = calculateKOLScore(kol);
  }

  // US-only filter (always applied)
  kols = kols.filter(k => k.country === 'US');

  // Apply filters
  if (minPublications > 0) {
    kols = kols.filter(k => k.publicationCount >= minPublications);
  }

  if (roleFilter === 'pi') {
    kols = kols.filter(k => k.trialCount > 0);
  } else if (roleFilter === 'author') {
    kols = kols.filter(k => k.publicationCount > 0);
  }

  // Sort by publication + trial count first to get top KOLs
  kols.sort((a, b) => {
    const aScore = a.publicationCount + (a.trialCount * 2);
    const bScore = b.publicationCount + (b.trialCount * 2);
    return bScore - aScore;
  });

  // Limit results
  kols = kols.slice(0, maxResults);

  // Search for emails for top KOLs who don't have one
  const kolsNeedingEmail = kols
    .filter(k => !k.email && k.institution)
    .slice(0, 10); // Search for top 10 only

  if (kolsNeedingEmail.length > 0) {
    const emailResults = await findEmailsForKOLs(
      kolsNeedingEmail.map(k => ({ name: k.name, institution: k.institution })),
      { maxConcurrent: 3, delayMs: 300, limit: 10 }
    );

    // Update KOLs with found emails
    for (const kol of kols) {
      if (!kol.email && emailResults.has(kol.name)) {
        kol.email = emailResults.get(kol.name) || null;
      }
    }
  }

  // Re-sort: email first, then by publication count
  kols.sort((a, b) => {
    const aHasEmail = a.email ? 1 : 0;
    const bHasEmail = b.email ? 1 : 0;
    if (bHasEmail !== aHasEmail) {
      return bHasEmail - aHasEmail;
    }
    return b.publicationCount - a.publicationCount;
  });

  const searchTime = Date.now() - startTime;

  return {
    query,
    totalKOLs: kols.length,
    kols,
    searchTime,
  };
}

/**
 * Calculate a KOL score based on publications and trials
 */
function calculateKOLScore(kol: KOL): number {
  // Weights for different factors
  const pubWeight = 2;
  const trialWeight = 5; // Trials are harder to get, so weight higher
  const bothBonus = 10; // Bonus for being both author and PI

  let score = 0;
  score += kol.publicationCount * pubWeight;
  score += kol.trialCount * trialWeight;

  // Bonus for being both author and PI
  if (kol.role === 'PI + Author') {
    score += bothBonus;
  }

  // Bonus for having email (actionable contact)
  if (kol.email) {
    score += 3;
  }

  return score;
}

/**
 * Normalize name for deduplication
 */
function normalizeKey(lastName: string, firstName: string): string {
  const normalizedLast = lastName.toLowerCase().replace(/[^a-z]/g, '');
  const normalizedFirst = firstName.toLowerCase().replace(/[^a-z]/g, '');
  return `${normalizedLast}_${normalizedFirst.charAt(0) || ''}`;
}

/**
 * Get cached or fresh KOL data
 * Uses a simple in-memory cache with TTL
 */
const kolCache = new Map<string, { data: KOLSearchResult; timestamp: number }>();
const CACHE_TTL = 30 * 60 * 1000; // 30 minutes

export async function findKOLsCached(
  query: string,
  options: {
    minPublications?: number;
    country?: string;
    roleFilter?: 'all' | 'pi' | 'author';
    maxResults?: number;
  } = {}
): Promise<KOLSearchResult> {
  const cacheKey = JSON.stringify({ query, ...options });
  const cached = kolCache.get(cacheKey);

  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data;
  }

  const result = await findKOLs(query, options);
  kolCache.set(cacheKey, { data: result, timestamp: Date.now() });

  return result;
}
