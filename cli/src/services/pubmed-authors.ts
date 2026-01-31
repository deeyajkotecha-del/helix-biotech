/**
 * PubMed Authors Service
 * Searches PubMed for publications and extracts author information
 * Uses NCBI E-utilities API: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
 */

import axios from 'axios';

export interface PubMedAuthor {
  name: string;
  firstName: string;
  lastName: string;
  affiliation: string;
  country: string;
  email: string | null;
  publicationCount: number;
  publications: PublicationInfo[];
}

export interface PublicationInfo {
  pmid: string;
  title: string;
  journal: string;
  year: string;
  isCorrespondingAuthor: boolean;
}

interface ESearchResult {
  esearchresult: {
    count: string;
    idlist: string[];
  };
}

interface EFetchResult {
  PubmedArticleSet?: {
    PubmedArticle?: PubmedArticle[];
  };
}

interface PubmedArticle {
  MedlineCitation: {
    PMID: { _: string } | string;
    Article: {
      ArticleTitle: string | { _: string };
      Journal?: {
        Title?: string;
        ISOAbbreviation?: string;
      };
      AuthorList?: {
        Author?: AuthorEntry[];
      };
      ArticleDate?: { Year?: string }[];
    };
    DateCompleted?: { Year?: string };
    DateRevised?: { Year?: string };
  };
}

interface AuthorEntry {
  LastName?: string;
  ForeName?: string;
  Initials?: string;
  AffiliationInfo?: { Affiliation?: string }[] | { Affiliation?: string };
}

const EUTILS_BASE = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils';

/**
 * Search PubMed and extract top authors for a given query
 */
export async function searchPubMedAuthors(
  query: string,
  maxResults: number = 100
): Promise<PubMedAuthor[]> {
  try {
    // Step 1: Search for article IDs
    const searchUrl = `${EUTILS_BASE}/esearch.fcgi`;
    const searchResponse = await axios.get<ESearchResult>(searchUrl, {
      params: {
        db: 'pubmed',
        term: query,
        retmax: maxResults,
        retmode: 'json',
        sort: 'relevance',
      },
      timeout: 15000,
    });

    const pmids = searchResponse.data?.esearchresult?.idlist || [];
    if (pmids.length === 0) {
      return [];
    }

    // Step 2: Fetch article details
    const fetchUrl = `${EUTILS_BASE}/efetch.fcgi`;
    const fetchResponse = await axios.get(fetchUrl, {
      params: {
        db: 'pubmed',
        id: pmids.join(','),
        retmode: 'xml',
      },
      timeout: 30000,
    });

    // Step 3: Parse XML response
    const articles = parsePubMedXML(fetchResponse.data);

    // Step 4: Aggregate authors
    const authorMap = new Map<string, PubMedAuthor>();

    for (const article of articles) {
      const authors = article.authors || [];
      const totalAuthors = authors.length;

      for (let i = 0; i < authors.length; i++) {
        const author = authors[i];
        if (!author.lastName) continue;

        const key = normalizeAuthorName(author.lastName, author.firstName || '');
        const isCorresponding = i === 0 || i === totalAuthors - 1;

        if (authorMap.has(key)) {
          const existing = authorMap.get(key)!;
          existing.publicationCount++;
          existing.publications.push({
            pmid: article.pmid,
            title: article.title,
            journal: article.journal,
            year: article.year,
            isCorrespondingAuthor: isCorresponding,
          });
          // Update affiliation if we have a better one
          if (author.affiliation && (!existing.affiliation || existing.affiliation.length < author.affiliation.length)) {
            existing.affiliation = author.affiliation;
            existing.country = extractCountry(author.affiliation);
          }
          // Update email if found
          if (author.email && !existing.email) {
            existing.email = author.email;
          }
        } else {
          authorMap.set(key, {
            name: `${author.firstName || ''} ${author.lastName}`.trim(),
            firstName: author.firstName || '',
            lastName: author.lastName,
            affiliation: author.affiliation || '',
            country: extractCountry(author.affiliation || ''),
            email: author.email || null,
            publicationCount: 1,
            publications: [{
              pmid: article.pmid,
              title: article.title,
              journal: article.journal,
              year: article.year,
              isCorrespondingAuthor: isCorresponding,
            }],
          });
        }
      }
    }

    // Step 5: Sort by publication count and return top 50
    const sortedAuthors = Array.from(authorMap.values())
      .sort((a, b) => b.publicationCount - a.publicationCount)
      .slice(0, 50);

    return sortedAuthors;
  } catch (error) {
    console.error('PubMed search error:', error);
    return [];
  }
}

/**
 * Parse PubMed XML response to extract article and author information
 */
function parsePubMedXML(xml: string): Array<{
  pmid: string;
  title: string;
  journal: string;
  year: string;
  authors: Array<{
    lastName: string;
    firstName: string;
    affiliation: string;
    email: string | null;
  }>;
}> {
  const articles: Array<{
    pmid: string;
    title: string;
    journal: string;
    year: string;
    authors: Array<{
      lastName: string;
      firstName: string;
      affiliation: string;
      email: string | null;
    }>;
  }> = [];

  // Simple XML parsing using regex (avoiding heavy XML parser dependency)
  const articleMatches = xml.match(/<PubmedArticle>[\s\S]*?<\/PubmedArticle>/g) || [];

  for (const articleXml of articleMatches) {
    // Extract PMID
    const pmidMatch = articleXml.match(/<PMID[^>]*>(\d+)<\/PMID>/);
    const pmid = pmidMatch ? pmidMatch[1] : '';

    // Extract title
    const titleMatch = articleXml.match(/<ArticleTitle[^>]*>([\s\S]*?)<\/ArticleTitle>/);
    let title = titleMatch ? titleMatch[1].replace(/<[^>]+>/g, '').trim() : '';

    // Extract journal
    const journalMatch = articleXml.match(/<Title>([\s\S]*?)<\/Title>/) ||
                         articleXml.match(/<ISOAbbreviation>([\s\S]*?)<\/ISOAbbreviation>/);
    const journal = journalMatch ? journalMatch[1].trim() : '';

    // Extract year
    const yearMatch = articleXml.match(/<PubDate>[\s\S]*?<Year>(\d{4})<\/Year>/) ||
                      articleXml.match(/<ArticleDate[^>]*>[\s\S]*?<Year>(\d{4})<\/Year>/) ||
                      articleXml.match(/<DateCompleted>[\s\S]*?<Year>(\d{4})<\/Year>/);
    const year = yearMatch ? yearMatch[1] : '';

    // Extract authors
    const authors: Array<{
      lastName: string;
      firstName: string;
      affiliation: string;
      email: string | null;
    }> = [];

    const authorMatches = articleXml.match(/<Author[^>]*>[\s\S]*?<\/Author>/g) || [];

    for (const authorXml of authorMatches) {
      const lastNameMatch = authorXml.match(/<LastName>([\s\S]*?)<\/LastName>/);
      const foreNameMatch = authorXml.match(/<ForeName>([\s\S]*?)<\/ForeName>/);
      const affiliationMatch = authorXml.match(/<Affiliation>([\s\S]*?)<\/Affiliation>/);

      if (lastNameMatch) {
        const affiliation = affiliationMatch ? affiliationMatch[1].trim() : '';
        const emailMatch = affiliation.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/);

        authors.push({
          lastName: lastNameMatch[1].trim(),
          firstName: foreNameMatch ? foreNameMatch[1].trim() : '',
          affiliation: affiliation.replace(/\s*Electronic address:.*$/i, '').trim(),
          email: emailMatch ? emailMatch[1] : null,
        });
      }
    }

    if (pmid) {
      articles.push({ pmid, title, journal, year, authors });
    }
  }

  return articles;
}

/**
 * Normalize author name for deduplication
 */
function normalizeAuthorName(lastName: string, firstName: string): string {
  const normalizedLast = lastName.toLowerCase().replace(/[^a-z]/g, '');
  const normalizedFirst = firstName.toLowerCase().replace(/[^a-z]/g, '');
  return `${normalizedLast}_${normalizedFirst.charAt(0) || ''}`;
}

/**
 * Extract country from affiliation string
 */
function extractCountry(affiliation: string): string {
  const aff = affiliation.toLowerCase();

  const countryPatterns: [RegExp, string][] = [
    [/\bunited states\b|\busa\b|\bu\.s\.a\b|\bu\.s\.\b/i, 'US'],
    [/\bchina\b|\bbeijing\b|\bshanghai\b|\bguangzhou\b/i, 'CN'],
    [/\bunited kingdom\b|\bengland\b|\buk\b|\bu\.k\.\b|\blondon\b/i, 'UK'],
    [/\bgermany\b|\bdeutschland\b|\bberlin\b|\bmunich\b/i, 'DE'],
    [/\bfrance\b|\bparis\b/i, 'FR'],
    [/\bjapan\b|\btokyo\b|\bosaka\b/i, 'JP'],
    [/\bsouth korea\b|\bkorea\b|\bseoul\b/i, 'KR'],
    [/\bcanada\b|\btoronto\b|\bvancouver\b|\bmontreal\b/i, 'CA'],
    [/\baustralia\b|\bsydney\b|\bmelbourne\b/i, 'AU'],
    [/\bitaly\b|\brome\b|\bmilan\b/i, 'IT'],
    [/\bspain\b|\bmadrid\b|\bbarcelona\b/i, 'ES'],
    [/\bnetherlands\b|\bamsterdam\b/i, 'NL'],
    [/\bswitzerland\b|\bzurich\b|\bgeneva\b/i, 'CH'],
    [/\bsweden\b|\bstockholm\b/i, 'SE'],
    [/\bbrazil\b|\bsao paulo\b/i, 'BR'],
    [/\bindia\b|\bmumbai\b|\bdelhi\b/i, 'IN'],
    [/\btaiwan\b|\btaipei\b/i, 'TW'],
    [/\bisrael\b|\btel aviv\b/i, 'IL'],
    [/\bbelgium\b|\bbrussels\b/i, 'BE'],
    [/\baustria\b|\bvienna\b/i, 'AT'],
  ];

  for (const [pattern, code] of countryPatterns) {
    if (pattern.test(aff)) {
      return code;
    }
  }

  // Check for US state abbreviations or major US institutions
  const usStates = /\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b/;
  if (usStates.test(affiliation)) {
    return 'US';
  }

  const usInstitutions = /\b(harvard|stanford|mit|yale|columbia|johns hopkins|mayo clinic|nih|cdc|fda|ucla|ucsf|duke|northwestern|cornell|upenn|uchicago|emory|vanderbilt|washington university|memorial sloan|md anderson|dana-farber|cleveland clinic)\b/i;
  if (usInstitutions.test(aff)) {
    return 'US';
  }

  return '';
}

/**
 * Extract shortened institution name from full affiliation string
 * Looks for hospital, university, institute, or medical center names
 */
export function extractInstitutionName(affiliation: string): string {
  if (!affiliation) return '';

  // Common institution patterns to look for
  const institutionPatterns = [
    // Cancer Centers (check first as they're more specific)
    /\b([\w\s\-\.]+(?:Cancer Center|Cancer Institute|Comprehensive Cancer Center))\b/i,
    // Medical Centers
    /\b([\w\s\-\.]+Medical Center)\b/i,
    // Hospitals (with common prefixes)
    /\b((?:Massachusetts General|Johns Hopkins|Mayo Clinic|Cleveland Clinic|Memorial Sloan[- ]?Kettering|MD Anderson|Cedars[- ]?Sinai|Mount Sinai|NYU Langone|Stanford|UCSF|UCLA|Duke|Emory|Northwestern|Vanderbilt)[\w\s\-\.]*(?:Hospital|Medical Center|Health System)?)\b/i,
    // Named hospitals
    /\b([\w\s\-\.]+(?:Hospital|Hospitals))\b/i,
    // Universities (check after hospitals)
    /\b((?:University of [\w\s]+|[\w\s]+ University|[\w\s]+ School of Medicine))\b/i,
    // Institutes
    /\b([\w\s\-\.]+Institute(?:\s+of\s+[\w\s]+)?)\b/i,
    // Research centers
    /\b([\w\s\-\.]+Research Center)\b/i,
  ];

  // Known institution shortcuts
  const knownInstitutions: [RegExp, string][] = [
    [/dana[- ]?farber/i, 'Dana-Farber Cancer Institute'],
    [/memorial sloan[- ]?kettering|mskcc/i, 'Memorial Sloan Kettering'],
    [/md anderson/i, 'MD Anderson Cancer Center'],
    [/mayo clinic/i, 'Mayo Clinic'],
    [/cleveland clinic/i, 'Cleveland Clinic'],
    [/johns hopkins/i, 'Johns Hopkins'],
    [/massachusetts general|mass general|mgh/i, 'Massachusetts General Hospital'],
    [/brigham and women|brigham & women/i, 'Brigham and Women\'s Hospital'],
    [/cedars[- ]?sinai/i, 'Cedars-Sinai Medical Center'],
    [/mount sinai/i, 'Mount Sinai'],
    [/nyu langone/i, 'NYU Langone'],
    [/stanford/i, 'Stanford Medicine'],
    [/ucsf|uc san francisco/i, 'UCSF'],
    [/ucla/i, 'UCLA'],
    [/duke university|duke medical/i, 'Duke University'],
    [/university of pennsylvania|upenn|penn medicine/i, 'University of Pennsylvania'],
    [/university of michigan/i, 'University of Michigan'],
    [/university of chicago/i, 'University of Chicago'],
    [/northwestern university|northwestern memorial/i, 'Northwestern University'],
    [/vanderbilt/i, 'Vanderbilt University'],
    [/emory/i, 'Emory University'],
    [/cornell|weill cornell/i, 'Weill Cornell Medicine'],
    [/columbia university/i, 'Columbia University'],
    [/yale/i, 'Yale University'],
    [/harvard/i, 'Harvard Medical School'],
    [/nih|national institutes of health/i, 'NIH'],
    [/fred hutch|hutchinson/i, 'Fred Hutchinson Cancer Center'],
    [/sloan kettering/i, 'Memorial Sloan Kettering'],
    [/university of texas/i, 'University of Texas'],
    [/university of california/i, 'University of California'],
    [/university of washington/i, 'University of Washington'],
    [/university of colorado/i, 'University of Colorado'],
    [/university of pittsburgh/i, 'University of Pittsburgh'],
    [/university of north carolina|unc/i, 'UNC Chapel Hill'],
    [/ohio state/i, 'Ohio State University'],
    [/city of hope/i, 'City of Hope'],
    [/roswell park/i, 'Roswell Park'],
    [/fox chase/i, 'Fox Chase Cancer Center'],
    [/moffitt/i, 'Moffitt Cancer Center'],
    [/huntsman/i, 'Huntsman Cancer Institute'],
  ];

  // First check for known institutions
  for (const [pattern, name] of knownInstitutions) {
    if (pattern.test(affiliation)) {
      return name;
    }
  }

  // Try to extract institution using patterns
  for (const pattern of institutionPatterns) {
    const match = affiliation.match(pattern);
    if (match && match[1]) {
      let inst = match[1].trim();
      // Clean up the result
      inst = inst.replace(/^(the|from|at)\s+/i, '');
      inst = inst.replace(/,.*$/, ''); // Remove trailing comma and everything after
      inst = inst.replace(/\s+/g, ' '); // Normalize whitespace
      if (inst.length > 5 && inst.length < 80) {
        return inst;
      }
    }
  }

  // Fallback: try to get first meaningful segment before comma
  const segments = affiliation.split(',').map(s => s.trim());
  for (const seg of segments) {
    if (seg.length > 10 && seg.length < 60 &&
        (seg.includes('University') || seg.includes('Hospital') ||
         seg.includes('Institute') || seg.includes('Center') || seg.includes('Clinic'))) {
      return seg.replace(/^(Department of|Division of|School of)\s+[\w\s]+,?\s*/i, '').trim();
    }
  }

  // Last resort: return first 50 chars
  if (affiliation.length > 50) {
    return affiliation.substring(0, 47) + '...';
  }
  return affiliation;
}

export { extractCountry };
