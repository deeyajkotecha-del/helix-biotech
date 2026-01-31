/**
 * Email Finder Service
 * Searches the web to find institutional emails for researchers
 */

import axios from 'axios';

// In-memory cache for found emails
const emailCache = new Map<string, string | null>();

// Personal email domains to filter out
const PERSONAL_DOMAINS = new Set([
  'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
  'icloud.com', 'me.com', 'mail.com', 'protonmail.com', 'ymail.com',
  'live.com', 'msn.com', 'comcast.net', 'verizon.net', 'att.net',
]);

// Known institutional email domains (partial matches)
const INSTITUTIONAL_PATTERNS = [
  /\.edu$/i,
  /\.ac\.[a-z]{2}$/i,  // .ac.uk, .ac.jp, etc.
  /\.org$/i,
  /\.gov$/i,
  // Major medical institutions
  /jhmi\.edu$/i,        // Johns Hopkins
  /mskcc\.org$/i,       // Memorial Sloan Kettering
  /mdanderson\.org$/i,  // MD Anderson
  /mayoclinic\.org$/i,  // Mayo Clinic
  /clevelandclinic\.org$/i,
  /partners\.org$/i,    // Mass General / Partners
  /bwh\.harvard\.edu$/i,
  /dfci\.harvard\.edu$/i,  // Dana-Farber
  /stanford\.edu$/i,
  /ucsf\.edu$/i,
  /ucla\.edu$/i,
  /upenn\.edu$/i,
  /uchicago\.edu$/i,
  /northwestern\.edu$/i,
  /duke\.edu$/i,
  /emory\.edu$/i,
  /vanderbilt\.edu$/i,
  /cshs\.org$/i,        // Cedars-Sinai
  /mssm\.edu$/i,        // Mount Sinai
  /nyulangone\.org$/i,
  /weill\.cornell\.edu$/i,
  /columbia\.edu$/i,
  /yale\.edu$/i,
  /nih\.gov$/i,
  /cancer\.gov$/i,
];

/**
 * Check if an email domain is institutional (not personal)
 */
function isInstitutionalEmail(email: string): boolean {
  const domain = email.split('@')[1]?.toLowerCase();
  if (!domain) return false;

  // Reject known personal domains
  if (PERSONAL_DOMAINS.has(domain)) return false;

  // Accept known institutional patterns
  for (const pattern of INSTITUTIONAL_PATTERNS) {
    if (pattern.test(domain)) return true;
  }

  // Accept any .edu domain
  if (domain.endsWith('.edu')) return true;

  // Accept any .org domain (likely institutional)
  if (domain.endsWith('.org')) return true;

  // Accept any .gov domain
  if (domain.endsWith('.gov')) return true;

  return false;
}

/**
 * Extract emails from text using regex
 */
function extractEmails(text: string): string[] {
  const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
  const matches = text.match(emailRegex) || [];

  // Deduplicate and filter
  const seen = new Set<string>();
  const emails: string[] = [];

  for (const email of matches) {
    const normalized = email.toLowerCase();
    if (!seen.has(normalized) && isInstitutionalEmail(normalized)) {
      seen.add(normalized);
      emails.push(normalized);
    }
  }

  return emails;
}

/**
 * Search for a researcher's email using multiple methods
 */
export async function findEmailBySearch(
  name: string,
  institution: string
): Promise<string | null> {
  // Check cache first
  const cacheKey = `${name}|${institution}`.toLowerCase();
  if (emailCache.has(cacheKey)) {
    return emailCache.get(cacheKey) || null;
  }

  // Clean up name (remove MD, PhD, etc.)
  const cleanName = name.replace(/,?\s*(MD|PhD|M\.D\.|Ph\.D\.|DO|DrPH|MPH|MS|RN|FACS|FACP)\.?\s*/gi, '').trim();
  const nameParts = cleanName.toLowerCase().split(/\s+/).filter(p => p.length > 1);
  const lastName = nameParts[nameParts.length - 1] || '';
  const firstName = nameParts[0] || '';

  let bestEmail: string | null = null;

  // Method 1: Search PubMed for author's papers with email (get more papers)
  try {
    // Use stricter author search with affiliation
    const searchTerms = institution
      ? `${lastName} ${firstName}[Author] AND ${institution}[Affiliation]`
      : `${lastName} ${firstName}[Author]`;
    const pubmedUrl = `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=${encodeURIComponent(searchTerms)}&retmax=20&retmode=json`;
    const searchResp = await axios.get(pubmedUrl, { timeout: 10000 });
    const pmids = searchResp.data?.esearchresult?.idlist || [];

    if (pmids.length > 0) {
      // Fetch paper details
      const fetchUrl = `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=${pmids.join(',')}&retmode=xml`;
      const fetchResp = await axios.get(fetchUrl, { timeout: 15000 });
      const xml = fetchResp.data;

      // Look specifically for emails near the author's name in XML
      // Extract author blocks and find email in their affiliation
      const authorBlocks = xml.match(/<Author[^>]*>[\s\S]*?<\/Author>/g) || [];
      for (const block of authorBlocks) {
        const lastNameMatch = block.match(/<LastName>([\s\S]*?)<\/LastName>/);
        if (lastNameMatch && lastNameMatch[1].toLowerCase().includes(lastName)) {
          const affiliationMatch = block.match(/<Affiliation>([\s\S]*?)<\/Affiliation>/);
          if (affiliationMatch) {
            const emails = extractEmails(affiliationMatch[1]);
            const ranked = rankEmails(emails, firstName, lastName);
            if (ranked) {
              bestEmail = ranked;
              break;
            }
          }
        }
      }

      // If no author-specific email found, try general extraction
      if (!bestEmail) {
        const emails = extractEmails(xml);
        bestEmail = rankEmails(emails, firstName, lastName);
      }
    }
  } catch (error) {
    // PubMed search failed, continue
  }

  // Method 2: Try DuckDuckGo search with better query
  if (!bestEmail) {
    try {
      const query = `"${cleanName}" ${institution} email contact`;
      const searchUrl = 'https://html.duckduckgo.com/html/';

      const response = await axios.post(searchUrl, `q=${encodeURIComponent(query)}`, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        },
        timeout: 10000,
      });

      const html = response.data;
      const emails = extractEmails(html);
      bestEmail = rankEmails(emails, firstName, lastName);
    } catch (error) {
      // DuckDuckGo failed, continue
    }
  }

  // Method 2: Try fetching institutional profile page directly
  if (!bestEmail) {
    const profileUrl = getProfileUrl(cleanName, institution);
    if (profileUrl) {
      try {
        const response = await axios.get(profileUrl, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
          },
          timeout: 10000,
        });
        const emails = extractEmails(response.data);
        bestEmail = rankEmails(emails, firstName, lastName);
      } catch (error) {
        // Profile page fetch failed
      }
    }
  }

  // Method 3: Try searching with "@" in query to find contact pages
  if (!bestEmail) {
    try {
      const contactQuery = `${cleanName} ${institution} contact @ site:.edu OR site:.org`;
      const searchUrl = 'https://html.duckduckgo.com/html/';

      const response = await axios.post(searchUrl, `q=${encodeURIComponent(contactQuery)}`, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        },
        timeout: 10000,
      });

      const emails = extractEmails(response.data);
      bestEmail = rankEmails(emails, firstName, lastName);
    } catch (error) {
      // Continue
    }
  }

  // Method 3: Try common email patterns for the institution
  if (!bestEmail && firstName && lastName) {
    const patterns = generateEmailPatterns(firstName, lastName, institution);
    // Just return the most likely pattern - we can't verify without SMTP check
    // For now, suggest the most common pattern
    if (patterns.length > 0) {
      // Don't set as found, but could suggest as "try this"
    }
  }

  // Cache the result
  emailCache.set(cacheKey, bestEmail);
  return bestEmail;
}

/**
 * Rank emails by how well they match the person's name
 */
function rankEmails(emails: string[], firstName: string, lastName: string): string | null {
  if (emails.length === 0) return null;

  // Must have at least first or last name to match
  if (!firstName && !lastName) return null;

  // Score each email
  const scored = emails.map(email => {
    const localPart = email.split('@')[0].toLowerCase();
    let score = 0;

    // Check if the email contains the last name (required for a valid match)
    const containsLastName = lastName.length >= 3 && localPart.includes(lastName);
    const containsFirstName = firstName.length >= 2 && localPart.includes(firstName);
    const containsFirstInitial = firstName && localPart.includes(firstName.charAt(0));

    // Must contain at least the last name
    if (!containsLastName) {
      // Check for first initial + part of last name
      if (!(containsFirstInitial && lastName.length >= 4 && localPart.includes(lastName.substring(0, 4)))) {
        return { email, score: -100 }; // Reject this email
      }
    }

    // Score based on patterns
    if (localPart === `${firstName}.${lastName}`) score += 50;
    if (localPart === `${firstName}${lastName}`) score += 45;
    if (localPart === `${lastName}.${firstName}`) score += 45;
    if (localPart === `${firstName.charAt(0)}.${lastName}`) score += 40;
    if (localPart === `${firstName.charAt(0)}${lastName}`) score += 35;
    if (localPart === `${lastName}${firstName.charAt(0)}`) score += 35;
    if (localPart === `${lastName}.${firstName.charAt(0)}`) score += 35;
    if (localPart === `${firstName}${lastName.charAt(0)}`) score += 30;

    // Partial matches
    if (containsLastName && containsFirstName) score += 25;
    if (containsLastName && containsFirstInitial) score += 15;
    if (containsLastName) score += 10;

    // Penalize if it looks like a generic email
    if (localPart.includes('info') || localPart.includes('contact') || localPart.includes('admin') || localPart.includes('support')) {
      score -= 50;
    }

    return { email, score };
  });

  // Filter out rejected emails and sort by score
  const validScored = scored.filter(s => s.score > 0);
  if (validScored.length === 0) return null;

  validScored.sort((a, b) => b.score - a.score);
  return validScored[0].email;
}

/**
 * Get direct profile URL for institutional lookup
 */
function getProfileUrl(name: string, institution: string): string | null {
  const instLower = institution.toLowerCase();
  const nameParts = name.toLowerCase().split(/\s+/);
  const lastName = nameParts[nameParts.length - 1];
  const firstName = nameParts[0];

  // Institutional profile URL patterns
  if (instLower.includes('johns hopkins')) {
    // Johns Hopkins faculty search
    return `https://www.hopkinsmedicine.org/profiles/search?search=${encodeURIComponent(name)}`;
  }
  if (instLower.includes('memorial sloan') || instLower.includes('mskcc')) {
    return `https://www.mskcc.org/search?keys=${encodeURIComponent(name)}`;
  }
  if (instLower.includes('md anderson')) {
    return `https://faculty.mdanderson.org/search?search=${encodeURIComponent(name)}`;
  }
  if (instLower.includes('dana-farber') || instLower.includes('dfci')) {
    return `https://www.dana-farber.org/find-a-doctor?q=${encodeURIComponent(name)}`;
  }
  if (instLower.includes('mayo clinic')) {
    return `https://www.mayoclinic.org/appointments/find-a-doctor/search-results?displayName=${encodeURIComponent(name)}`;
  }
  if (instLower.includes('cedars-sinai') || instLower.includes('cshs')) {
    return `https://www.cedars-sinai.org/research/faculty-directory.html?q=${encodeURIComponent(name)}`;
  }
  if (instLower.includes('ucsf')) {
    return `https://profiles.ucsf.edu/search/?SearchFor=${encodeURIComponent(name)}`;
  }
  if (instLower.includes('stanford')) {
    return `https://med.stanford.edu/search.html?q=${encodeURIComponent(name)}`;
  }
  if (instLower.includes('nih')) {
    return `https://irp.nih.gov/pi-search?firstName=${encodeURIComponent(firstName)}&lastName=${encodeURIComponent(lastName)}`;
  }

  return null;
}

/**
 * Generate common email patterns for an institution
 */
function generateEmailPatterns(firstName: string, lastName: string, institution: string): string[] {
  const patterns: string[] = [];

  // Map institutions to domains
  const domainMap: Record<string, string> = {
    'johns hopkins': 'jhmi.edu',
    'memorial sloan kettering': 'mskcc.org',
    'md anderson': 'mdanderson.org',
    'dana-farber': 'dfci.harvard.edu',
    'mayo clinic': 'mayo.edu',
    'cedars-sinai': 'cshs.org',
    'mount sinai': 'mssm.edu',
    'ucsf': 'ucsf.edu',
    'ucla': 'mednet.ucla.edu',
    'stanford': 'stanford.edu',
    'harvard': 'hms.harvard.edu',
    'yale': 'yale.edu',
    'columbia': 'columbia.edu',
    'northwestern': 'northwestern.edu',
    'duke': 'duke.edu',
    'nih': 'nih.gov',
  };

  const instLower = institution.toLowerCase();
  let domain = '';

  for (const [key, value] of Object.entries(domainMap)) {
    if (instLower.includes(key)) {
      domain = value;
      break;
    }
  }

  if (domain) {
    const f = firstName.toLowerCase();
    const l = lastName.toLowerCase();
    patterns.push(`${f}.${l}@${domain}`);
    patterns.push(`${f}${l}@${domain}`);
    patterns.push(`${f.charAt(0)}${l}@${domain}`);
    patterns.push(`${l}${f.charAt(0)}@${domain}`);
  }

  return patterns;
}

/**
 * Find emails for multiple KOLs with rate limiting
 */
export async function findEmailsForKOLs(
  kols: Array<{ name: string; institution: string }>,
  options: {
    maxConcurrent?: number;
    delayMs?: number;
    limit?: number;
  } = {}
): Promise<Map<string, string | null>> {
  const { maxConcurrent = 3, delayMs = 500, limit = 10 } = options;

  const results = new Map<string, string | null>();
  const kolsToSearch = kols.slice(0, limit);

  // Process in batches
  for (let i = 0; i < kolsToSearch.length; i += maxConcurrent) {
    const batch = kolsToSearch.slice(i, i + maxConcurrent);

    const promises = batch.map(async (kol) => {
      const email = await findEmailBySearch(kol.name, kol.institution);
      results.set(kol.name, email);
    });

    await Promise.all(promises);

    // Delay between batches
    if (i + maxConcurrent < kolsToSearch.length) {
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }
  }

  return results;
}

/**
 * Get cached email for a KOL
 */
export function getCachedEmail(name: string, institution: string): string | null | undefined {
  const cacheKey = `${name}|${institution}`.toLowerCase();
  return emailCache.get(cacheKey);
}

/**
 * Clear the email cache
 */
export function clearEmailCache(): void {
  emailCache.clear();
}
