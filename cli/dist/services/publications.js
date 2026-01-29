"use strict";
/**
 * Publications Service
 *
 * Fetches and processes publications from PubMed E-utilities API.
 * Handles article metadata, author extraction, and search.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.searchPublications = searchPublications;
exports.getPublicationByPmid = getPublicationByPmid;
exports.getPublicationsByPmids = getPublicationsByPmids;
exports.parsePubmedXml = parsePubmedXml;
exports.determineAuthorPosition = determineAuthorPosition;
exports.extractInstitution = extractInstitution;
exports.extractEmail = extractEmail;
exports.extractNctIds = extractNctIds;
exports.categorizePublication = categorizePublication;
exports.isHighImpactJournal = isHighImpactJournal;
exports.extractTopAuthors = extractTopAuthors;
const PUBMED_BASE = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils';
const RATE_LIMIT_DELAY = 350; // ms between requests (PubMed allows 3/sec without API key)
// ============================================
// Main Functions
// ============================================
/**
 * Search publications by query using PubMed E-utilities
 */
async function searchPublications(query, options) {
    const maxResults = options?.maxResults || 50;
    console.log(`[Publications] Searching PubMed for "${query}" (max ${maxResults})...`);
    try {
        // Step 1: Search for PMIDs
        const pmids = await pubmedSearch(query, {
            retmax: maxResults,
            mindate: options?.fromDate,
            maxdate: options?.toDate,
        });
        if (pmids.length === 0) {
            console.log(`[Publications] No results found for "${query}"`);
            return [];
        }
        console.log(`[Publications] Found ${pmids.length} PMIDs, fetching details...`);
        // Step 2: Fetch publication details in batches
        const publications = await fetchPublicationDetails(pmids);
        console.log(`[Publications] Retrieved ${publications.length} publications`);
        return publications;
    }
    catch (error) {
        console.error(`[Publications] Error searching: ${error}`);
        return [];
    }
}
/**
 * Get publication by PMID
 */
async function getPublicationByPmid(pmid) {
    try {
        const publications = await fetchPublicationDetails([pmid]);
        return publications[0] || null;
    }
    catch (error) {
        console.error(`[Publications] Error fetching PMID ${pmid}: ${error}`);
        return null;
    }
}
/**
 * Get multiple publications by PMIDs
 */
async function getPublicationsByPmids(pmids) {
    const results = new Map();
    const publications = await fetchPublicationDetails(pmids);
    for (const pub of publications) {
        if (pub.pmid) {
            results.set(pub.pmid, pub);
        }
    }
    return results;
}
// ============================================
// PubMed API Functions
// ============================================
/**
 * Search PubMed and return list of PMIDs
 */
async function pubmedSearch(query, options) {
    const params = new URLSearchParams({
        db: 'pubmed',
        term: query,
        retmode: 'json',
        retmax: String(options.retmax || 50),
        retstart: String(options.retstart || 0),
        sort: 'relevance',
    });
    if (options.mindate) {
        params.append('mindate', options.mindate);
        params.append('datetype', 'pdat');
    }
    if (options.maxdate) {
        params.append('maxdate', options.maxdate);
    }
    const url = `${PUBMED_BASE}/esearch.fcgi?${params.toString()}`;
    const response = await fetch(url, {
        headers: { 'User-Agent': 'Helix/1.0 (biotech-intelligence-platform)' }
    });
    if (!response.ok) {
        throw new Error(`PubMed search failed: ${response.status}`);
    }
    const data = await response.json();
    return data.esearchresult?.idlist || [];
}
/**
 * Fetch publication details for a list of PMIDs using efetch
 */
async function fetchPublicationDetails(pmids) {
    if (pmids.length === 0)
        return [];
    const publications = [];
    // Process in batches of 100
    for (let i = 0; i < pmids.length; i += 100) {
        const batch = pmids.slice(i, i + 100);
        const params = new URLSearchParams({
            db: 'pubmed',
            id: batch.join(','),
            retmode: 'xml',
            rettype: 'abstract',
        });
        const url = `${PUBMED_BASE}/efetch.fcgi?${params.toString()}`;
        try {
            const response = await fetch(url, {
                headers: { 'User-Agent': 'Helix/1.0 (biotech-intelligence-platform)' }
            });
            if (!response.ok) {
                console.error(`[Publications] efetch failed: ${response.status}`);
                continue;
            }
            const xml = await response.text();
            const parsed = parsePubmedXml(xml);
            publications.push(...parsed);
            // Rate limiting
            if (i + 100 < pmids.length) {
                await sleep(RATE_LIMIT_DELAY);
            }
        }
        catch (error) {
            console.error(`[Publications] Error fetching batch: ${error}`);
        }
    }
    return publications;
}
/**
 * Parse PubMed XML response into Publication objects
 */
function parsePubmedXml(xml) {
    const publications = [];
    // Match each PubmedArticle element
    const articleMatches = xml.match(/<PubmedArticle>[\s\S]*?<\/PubmedArticle>/gi) || [];
    for (const articleXml of articleMatches) {
        try {
            const pub = parseArticleXml(articleXml);
            if (pub) {
                publications.push(pub);
            }
        }
        catch (error) {
            // Skip malformed articles
        }
    }
    return publications;
}
/**
 * Parse a single PubmedArticle XML element
 */
function parseArticleXml(xml) {
    // Extract PMID
    const pmidMatch = xml.match(/<PMID[^>]*>(\d+)<\/PMID>/);
    if (!pmidMatch)
        return null;
    const pmid = pmidMatch[1];
    // Extract title
    const titleMatch = xml.match(/<ArticleTitle>([^<]+)<\/ArticleTitle>/);
    const title = titleMatch ? cleanXmlText(titleMatch[1]) : 'Untitled';
    // Extract abstract
    const abstractMatch = xml.match(/<AbstractText[^>]*>([\s\S]*?)<\/AbstractText>/gi);
    let abstract = '';
    if (abstractMatch) {
        abstract = abstractMatch.map(a => {
            const text = a.replace(/<[^>]+>/g, '');
            return cleanXmlText(text);
        }).join(' ');
    }
    // Extract journal
    const journalMatch = xml.match(/<Title>([^<]+)<\/Title>/);
    const journal = journalMatch ? cleanXmlText(journalMatch[1]) : undefined;
    // Extract publication date
    const yearMatch = xml.match(/<PubDate>[\s\S]*?<Year>(\d+)<\/Year>/);
    const monthMatch = xml.match(/<PubDate>[\s\S]*?<Month>(\w+)<\/Month>/);
    const dayMatch = xml.match(/<PubDate>[\s\S]*?<Day>(\d+)<\/Day>/);
    let publicationDate;
    if (yearMatch) {
        const year = yearMatch[1];
        const month = monthMatch ? monthToNumber(monthMatch[1]) : '01';
        const day = dayMatch ? dayMatch[1].padStart(2, '0') : '01';
        publicationDate = `${year}-${month}-${day}`;
    }
    // Extract authors
    const authors = [];
    const authorListMatch = xml.match(/<AuthorList[^>]*>([\s\S]*?)<\/AuthorList>/);
    if (authorListMatch) {
        const authorMatches = authorListMatch[1].match(/<Author[^>]*>[\s\S]*?<\/Author>/gi) || [];
        for (let i = 0; i < authorMatches.length; i++) {
            const authorXml = authorMatches[i];
            const lastNameMatch = authorXml.match(/<LastName>([^<]+)<\/LastName>/);
            const foreNameMatch = authorXml.match(/<ForeName>([^<]+)<\/ForeName>/);
            const initialsMatch = authorXml.match(/<Initials>([^<]+)<\/Initials>/);
            const affiliationMatch = authorXml.match(/<Affiliation>([^<]+)<\/Affiliation>/);
            if (lastNameMatch) {
                const lastName = cleanXmlText(lastNameMatch[1]);
                const foreName = foreNameMatch ? cleanXmlText(foreNameMatch[1]) : undefined;
                const initials = initialsMatch ? cleanXmlText(initialsMatch[1]) : undefined;
                authors.push({
                    lastName,
                    foreName,
                    initials,
                    fullName: `${lastName} ${foreName || initials || ''}`.trim(),
                    affiliation: affiliationMatch ? cleanXmlText(affiliationMatch[1]) : undefined,
                    authorPosition: i === 0 ? 'First' : (i === authorMatches.length - 1 ? 'Last' : 'Middle'),
                });
            }
        }
    }
    // Extract publication types
    const publicationTypes = [];
    const pubTypeMatches = xml.match(/<PublicationType[^>]*>([^<]+)<\/PublicationType>/gi) || [];
    for (const match of pubTypeMatches) {
        const typeMatch = match.match(/>([^<]+)</);
        if (typeMatch) {
            publicationTypes.push(cleanXmlText(typeMatch[1]));
        }
    }
    // Extract MeSH terms
    const meshTerms = [];
    const meshMatches = xml.match(/<DescriptorName[^>]*>([^<]+)<\/DescriptorName>/gi) || [];
    for (const match of meshMatches) {
        const termMatch = match.match(/>([^<]+)</);
        if (termMatch) {
            meshTerms.push(cleanXmlText(termMatch[1]));
        }
    }
    // Extract keywords
    const keywords = [];
    const keywordMatches = xml.match(/<Keyword[^>]*>([^<]+)<\/Keyword>/gi) || [];
    for (const match of keywordMatches) {
        const kwMatch = match.match(/>([^<]+)</);
        if (kwMatch) {
            keywords.push(cleanXmlText(kwMatch[1]));
        }
    }
    // Extract DOI
    const doiMatch = xml.match(/<ArticleId IdType="doi">([^<]+)<\/ArticleId>/);
    const doi = doiMatch ? cleanXmlText(doiMatch[1]) : undefined;
    return {
        pmid,
        title,
        abstract,
        authors,
        journal: { name: journal || 'Unknown' },
        publicationDate: publicationDate || new Date().toISOString().split('T')[0],
        publicationType: publicationTypes,
        meshTerms,
        keywords,
        doi,
        fullTextAvailable: false, // Would need PMC lookup to determine
        fetchedAt: new Date().toISOString(),
    };
}
// ============================================
// Author Extraction
// ============================================
/**
 * Determine author position (first, last, middle)
 */
function determineAuthorPosition(index, total) {
    if (index === 0)
        return 'First';
    if (index === total - 1)
        return 'Last';
    return 'Middle';
}
/**
 * Extract institution from affiliation string
 */
function extractInstitution(affiliation) {
    if (!affiliation)
        return null;
    const patterns = [
        /(?:University|Université|Universität|Universidad)\s+of\s+[\w\s]+/i,
        /[\w\s]+\s+University/i,
        /[\w\s]+\s+Medical\s+Center/i,
        /[\w\s]+\s+Hospital/i,
        /[\w\s]+\s+Institute/i,
        /[\w\s]+\s+School\s+of\s+Medicine/i,
        /Mayo\s+Clinic/i,
        /Cleveland\s+Clinic/i,
        /Johns\s+Hopkins/i,
        /Harvard/i,
        /Stanford/i,
        /Memorial\s+Sloan/i,
        /MD\s+Anderson/i,
        /Dana[\s-]Farber/i,
    ];
    for (const pattern of patterns) {
        const match = affiliation.match(pattern);
        if (match)
            return match[0].trim();
    }
    // Fallback: first part before comma
    const parts = affiliation.split(',');
    if (parts[0] && parts[0].length < 100) {
        return parts[0].trim();
    }
    return null;
}
/**
 * Extract email from affiliation string
 */
function extractEmail(text) {
    const match = text.match(/[\w.+-]+@[\w.-]+\.\w+/);
    return match ? match[0] : null;
}
// ============================================
// Trial Linkage
// ============================================
/**
 * Extract NCT IDs mentioned in publication text/abstract
 */
function extractNctIds(text) {
    const pattern = /NCT\d{8}/gi;
    const matches = text.match(pattern) || [];
    return [...new Set(matches.map(m => m.toUpperCase()))];
}
// ============================================
// Publication Analysis
// ============================================
/**
 * Categorize publication by type
 */
function categorizePublication(pubTypes) {
    const types = pubTypes.map(t => t.toLowerCase());
    if (types.some(t => t.includes('clinical trial')))
        return 'Clinical Trial';
    if (types.some(t => t.includes('meta-analysis')))
        return 'Meta-Analysis';
    if (types.some(t => t.includes('review') || t.includes('systematic')))
        return 'Review';
    if (types.some(t => t.includes('case report')))
        return 'Case Report';
    return 'Other';
}
/**
 * Check if publication is high-impact (by journal)
 */
function isHighImpactJournal(journalName) {
    if (!journalName)
        return false;
    const highImpact = [
        'new england journal of medicine',
        'lancet',
        'jama',
        'bmj',
        'nature',
        'science',
        'cell',
        'nature medicine',
        'nature biotechnology',
        'journal of clinical oncology',
        'gastroenterology',
        'hepatology',
        'blood',
        'journal of clinical investigation',
        'annals of internal medicine',
        'cancer discovery',
        'cancer cell',
        'clinical cancer research',
    ];
    return highImpact.some(j => journalName.toLowerCase().includes(j));
}
/**
 * Extract top authors from publications
 */
function extractTopAuthors(publications, limit = 20) {
    const authorMap = new Map();
    const currentYear = new Date().getFullYear();
    const recentCutoff = currentYear - 3;
    for (const pub of publications) {
        const pubYear = pub.publicationDate ? parseInt(pub.publicationDate.substring(0, 4)) : null;
        const isRecent = pubYear && pubYear >= recentCutoff;
        for (const author of pub.authors || []) {
            if (!author.lastName)
                continue;
            const key = `${author.lastName.toLowerCase()}_${(author.foreName || author.initials || '').toLowerCase().charAt(0)}`;
            if (!authorMap.has(key)) {
                authorMap.set(key, {
                    lastName: author.lastName,
                    foreName: author.foreName || author.initials || '',
                    institutions: [],
                    publicationCount: 0,
                    firstAuthorCount: 0,
                    lastAuthorCount: 0,
                    recentYears: new Set(),
                });
            }
            const entry = authorMap.get(key);
            entry.publicationCount++;
            if (author.authorPosition === 'First')
                entry.firstAuthorCount++;
            if (author.authorPosition === 'Last')
                entry.lastAuthorCount++;
            if (author.affiliation) {
                const inst = extractInstitution(author.affiliation);
                if (inst && !entry.institutions.includes(inst)) {
                    entry.institutions.push(inst);
                }
            }
            if (isRecent && pubYear) {
                entry.recentYears.add(String(pubYear));
            }
        }
    }
    // Convert to array and sort by publication count
    const authors = Array.from(authorMap.values())
        .map(a => ({
        name: `${a.foreName} ${a.lastName}`.trim(),
        lastName: a.lastName,
        foreName: a.foreName,
        institution: a.institutions[0] || null,
        publicationCount: a.publicationCount,
        firstAuthorCount: a.firstAuthorCount,
        lastAuthorCount: a.lastAuthorCount,
        recentPublications: a.recentYears.size,
        isActive: a.recentYears.size > 0,
    }))
        .sort((a, b) => b.publicationCount - a.publicationCount)
        .slice(0, limit);
    return authors;
}
// ============================================
// Utility Functions
// ============================================
function cleanXmlText(text) {
    return text
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .replace(/&apos;/g, "'")
        .replace(/\s+/g, ' ')
        .trim();
}
function monthToNumber(month) {
    const months = {
        'jan': '01', 'january': '01',
        'feb': '02', 'february': '02',
        'mar': '03', 'march': '03',
        'apr': '04', 'april': '04',
        'may': '05',
        'jun': '06', 'june': '06',
        'jul': '07', 'july': '07',
        'aug': '08', 'august': '08',
        'sep': '09', 'september': '09',
        'oct': '10', 'october': '10',
        'nov': '11', 'november': '11',
        'dec': '12', 'december': '12',
    };
    return months[month.toLowerCase()] || month.padStart(2, '0');
}
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
//# sourceMappingURL=publications.js.map