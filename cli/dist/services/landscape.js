"use strict";
/**
 * Therapeutic Landscape Service
 *
 * Fetches and combines data from multiple sources:
 * - ClinicalTrials.gov (clinical trials with pagination)
 * - RSS feeds (deals & news) with broader matching
 * - PubMed (research publications with proper year counts and KOL filtering)
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.getLandscapeData = getLandscapeData;
exports.generateLandscapeCSV = generateLandscapeCSV;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
// Cache directory
const CACHE_DIR = path.resolve(__dirname, '..', '..', 'cache', 'landscape');
const CACHE_MAX_AGE_MS = 6 * 60 * 60 * 1000; // 6 hours
// ============================================
// ClinicalTrials.gov API (with pagination)
// ============================================
async function fetchClinicalTrials(condition) {
    console.log(`  [Landscape] Fetching clinical trials for "${condition}"...`);
    const allStudies = [];
    let nextPageToken = null;
    const pageSize = 100;
    const maxPages = 10; // Fetch up to 1000 trials
    let pageCount = 0;
    try {
        // Paginate through all results
        do {
            const encodedCondition = encodeURIComponent(condition);
            let url = `https://clinicaltrials.gov/api/v2/studies?query.cond=${encodedCondition}&pageSize=${pageSize}&format=json`;
            if (nextPageToken) {
                url += `&pageToken=${nextPageToken}`;
            }
            const response = await fetch(url, {
                headers: { 'User-Agent': 'Helix/1.0 (biotech-research-tool)' }
            });
            if (!response.ok) {
                console.log(`  [Landscape] ClinicalTrials.gov returned ${response.status}`);
                break;
            }
            const data = await response.json();
            const studies = data.studies || [];
            allStudies.push(...studies);
            nextPageToken = data.nextPageToken || null;
            pageCount++;
            console.log(`  [Landscape] Fetched page ${pageCount}: ${studies.length} trials (total: ${allStudies.length})`);
            // Add small delay between requests to be nice to the API
            if (nextPageToken && pageCount < maxPages) {
                await sleep(500);
            }
        } while (nextPageToken && pageCount < maxPages);
        const trials = allStudies.map((study) => {
            const protocol = study.protocolSection || {};
            const id = protocol.identificationModule || {};
            const status = protocol.statusModule || {};
            const sponsor = protocol.sponsorCollaboratorsModule || {};
            const design = protocol.designModule || {};
            const arms = protocol.armsInterventionsModule || {};
            const outcomes = protocol.outcomesModule || {};
            const locations = protocol.contactsLocationsModule?.locations || [];
            const hasResults = study.hasResults || false;
            // Extract interventions (drug names)
            const interventions = [];
            for (const intervention of arms.interventions || []) {
                if (intervention.name) {
                    interventions.push(intervention.name);
                }
            }
            // Extract primary endpoint
            let primaryEndpoint = null;
            const primaryOutcomes = outcomes.primaryOutcomes || [];
            if (primaryOutcomes.length > 0) {
                primaryEndpoint = primaryOutcomes[0].measure || null;
            }
            return {
                nctId: id.nctId || '',
                title: id.briefTitle || '',
                status: status.overallStatus || 'Unknown',
                phase: design.phases?.join('/') || 'N/A',
                sponsor: sponsor.leadSponsor?.name || 'Unknown',
                startDate: status.startDateStruct?.date || null,
                completionDate: status.completionDateStruct?.date || null,
                enrollment: design.enrollmentInfo?.count || null,
                locations: locations.slice(0, 3).map((loc) => loc.country || 'Unknown'),
                interventions,
                primaryEndpoint,
                resultsAvailable: hasResults
            };
        });
        // Calculate phase breakdown
        const phaseBreakdown = {};
        for (const trial of trials) {
            const phase = normalizePhase(trial.phase);
            phaseBreakdown[phase] = (phaseBreakdown[phase] || 0) + 1;
        }
        // Calculate status breakdown
        const statusBreakdown = {};
        for (const trial of trials) {
            statusBreakdown[trial.status] = (statusBreakdown[trial.status] || 0) + 1;
        }
        // Calculate top sponsors
        const sponsorCounts = {};
        for (const trial of trials) {
            sponsorCounts[trial.sponsor] = (sponsorCounts[trial.sponsor] || 0) + 1;
        }
        const topSponsors = Object.entries(sponsorCounts)
            .map(([name, count]) => ({ name, count }))
            .sort((a, b) => b.count - a.count)
            .slice(0, 15);
        console.log(`  [Landscape] Found ${trials.length} total clinical trials`);
        return { trials, phaseBreakdown, topSponsors, statusBreakdown };
    }
    catch (error) {
        console.log(`  [Landscape] Error fetching clinical trials: ${error}`);
        return { trials: [], phaseBreakdown: {}, topSponsors: [], statusBreakdown: {} };
    }
}
function normalizePhase(phase) {
    const p = phase.toLowerCase();
    if (p.includes('4'))
        return 'Phase 4';
    if (p.includes('3') && p.includes('2'))
        return 'Phase 2/3';
    if (p.includes('3'))
        return 'Phase 3';
    if (p.includes('2') && p.includes('1'))
        return 'Phase 1/2';
    if (p.includes('2'))
        return 'Phase 2';
    if (p.includes('1'))
        return 'Phase 1';
    if (p.includes('early'))
        return 'Early Phase 1';
    if (p === 'n/a' || p === 'na' || !p)
        return 'Not Applicable';
    return phase;
}
// ============================================
// Molecule Landscape Extraction
// ============================================
function extractMolecules(trials) {
    const moleculeMap = new Map();
    for (const trial of trials) {
        for (const intervention of trial.interventions) {
            // Normalize molecule name
            const normalizedName = normalizeMoleculeName(intervention);
            if (!normalizedName || normalizedName.length < 3)
                continue;
            // Skip placebo, standard of care, etc.
            if (isControlIntervention(normalizedName))
                continue;
            const existing = moleculeMap.get(normalizedName);
            if (existing) {
                existing.trialCount++;
                existing.trialIds.push(trial.nctId);
                // Update highest phase if this trial is more advanced
                if (getPhaseRank(trial.phase) > getPhaseRank(existing.highestPhase)) {
                    existing.highestPhase = normalizePhase(trial.phase);
                }
                // Update status to most active
                if (isActiveStatus(trial.status) && !isActiveStatus(existing.status)) {
                    existing.status = trial.status;
                }
            }
            else {
                moleculeMap.set(normalizedName, {
                    name: intervention,
                    mechanism: extractMechanism(intervention),
                    sponsor: trial.sponsor,
                    highestPhase: normalizePhase(trial.phase),
                    trialCount: 1,
                    trialIds: [trial.nctId],
                    status: trial.status
                });
            }
        }
    }
    // Sort by highest phase then trial count
    return Array.from(moleculeMap.values())
        .sort((a, b) => {
        const phaseDiff = getPhaseRank(b.highestPhase) - getPhaseRank(a.highestPhase);
        if (phaseDiff !== 0)
            return phaseDiff;
        return b.trialCount - a.trialCount;
    })
        .slice(0, 50);
}
function normalizeMoleculeName(name) {
    return name
        .toLowerCase()
        .replace(/\s*\([^)]*\)/g, '') // Remove parenthetical info
        .replace(/\s+/g, ' ')
        .trim();
}
function isControlIntervention(name) {
    const controls = [
        'placebo', 'standard of care', 'standard care', 'soc',
        'best supportive care', 'bsc', 'observation', 'no intervention',
        'usual care', 'control', 'sham', 'active comparator'
    ];
    const lower = name.toLowerCase();
    return controls.some(c => lower.includes(c));
}
function isActiveStatus(status) {
    const active = ['recruiting', 'active', 'enrolling', 'not_yet_recruiting'];
    return active.some(a => status.toLowerCase().includes(a));
}
function extractMechanism(name) {
    const lower = name.toLowerCase();
    if (lower.includes('mab') || lower.includes('umab') || lower.includes('zumab'))
        return 'Monoclonal Antibody';
    if (lower.includes('nib') || lower.includes('tinib'))
        return 'Kinase Inhibitor';
    if (lower.includes('ciclib'))
        return 'CDK Inhibitor';
    if (lower.includes('stat'))
        return 'JAK/STAT Inhibitor';
    if (lower.includes('car-t') || lower.includes('car t'))
        return 'CAR-T Cell Therapy';
    if (lower.includes('vaccine'))
        return 'Vaccine';
    if (lower.includes('sirna') || lower.includes('antisense'))
        return 'RNA Therapeutic';
    if (lower.includes('gene therapy'))
        return 'Gene Therapy';
    if (lower.includes('stem cell'))
        return 'Cell Therapy';
    return null;
}
function getPhaseRank(phase) {
    const p = phase.toLowerCase();
    if (p.includes('approved') || p.includes('marketed') || p.includes('4'))
        return 100;
    if (p.includes('3'))
        return 70;
    if (p.includes('2/3'))
        return 60;
    if (p.includes('2'))
        return 50;
    if (p.includes('1/2'))
        return 40;
    if (p.includes('1'))
        return 30;
    if (p.includes('early'))
        return 20;
    return 0;
}
// ============================================
// RSS Feeds (Deals & News) - Improved
// ============================================
const RSS_FEEDS = [
    { url: 'https://www.fiercebiotech.com/rss/xml', source: 'Fierce Biotech' },
    { url: 'https://www.fiercepharma.com/rss/xml', source: 'Fierce Pharma' },
    { url: 'https://www.prnewswire.com/rss/health-latest-news.rss', source: 'PR Newswire' },
    { url: 'https://endpts.com/feed/', source: 'Endpoints News' },
    { url: 'https://www.biopharmadive.com/feeds/news/', source: 'BioPharma Dive' }
];
async function fetchDealsNews(condition) {
    console.log(`  [Landscape] Fetching deals & news for "${condition}"...`);
    // Create multiple keyword variations for better matching
    const keywords = generateKeywordVariations(condition);
    console.log(`  [Landscape] Using keywords: ${keywords.slice(0, 5).join(', ')}...`);
    const allItems = [];
    // Fetch all feeds in parallel
    const feedPromises = RSS_FEEDS.map(async (feed) => {
        try {
            const response = await fetch(feed.url, {
                headers: {
                    'User-Agent': 'Mozilla/5.0 (compatible; Helix/1.0; +https://helix.bio)',
                    'Accept': 'application/rss+xml, application/xml, text/xml, */*'
                },
                signal: AbortSignal.timeout(15000)
            });
            if (!response.ok) {
                console.log(`  [Landscape] ${feed.source} returned ${response.status}`);
                return [];
            }
            const xml = await response.text();
            console.log(`  [Landscape] ${feed.source}: received ${xml.length} bytes`);
            const items = parseRSSItems(xml, feed.source, keywords);
            console.log(`  [Landscape] ${feed.source}: found ${items.length} matching items`);
            return items;
        }
        catch (error) {
            console.log(`  [Landscape] Error fetching ${feed.source}: ${error}`);
            return [];
        }
    });
    const results = await Promise.all(feedPromises);
    for (const items of results) {
        allItems.push(...items);
    }
    // Sort by date and dedupe
    allItems.sort((a, b) => new Date(b.pubDate).getTime() - new Date(a.pubDate).getTime());
    // Dedupe by title similarity
    const seen = new Set();
    const uniqueItems = allItems.filter(item => {
        const key = item.title.toLowerCase().substring(0, 50);
        if (seen.has(key))
            return false;
        seen.add(key);
        return true;
    });
    console.log(`  [Landscape] Found ${uniqueItems.length} unique news items`);
    return uniqueItems.slice(0, 50);
}
function generateKeywordVariations(condition) {
    const keywords = [];
    const lower = condition.toLowerCase();
    // Original condition
    keywords.push(lower);
    // Individual words (for multi-word conditions)
    const words = lower.split(/\s+/).filter(w => w.length > 3);
    keywords.push(...words);
    // Common abbreviations and variations
    const abbreviations = {
        'ulcerative colitis': ['uc', 'ibd', 'colitis', 'inflammatory bowel'],
        'crohn': ['crohn\'s', 'crohns', 'ibd', 'inflammatory bowel'],
        'psoriasis': ['pso', 'plaque psoriasis', 'psoriatic'],
        'rheumatoid arthritis': ['ra', 'arthritis', 'autoimmune'],
        'multiple sclerosis': ['ms', 'sclerosis'],
        'car-t': ['car t', 'cart', 'chimeric antigen', 'cell therapy'],
        'non-small cell lung cancer': ['nsclc', 'lung cancer'],
        'breast cancer': ['her2', 'triple negative', 'tnbc'],
    };
    for (const [key, variations] of Object.entries(abbreviations)) {
        if (lower.includes(key)) {
            keywords.push(...variations);
        }
    }
    return [...new Set(keywords)];
}
function parseRSSItems(xml, source, keywords) {
    const items = [];
    // Try multiple item tag patterns
    let itemMatches = xml.match(/<item[^>]*>[\s\S]*?<\/item>/gi) || [];
    if (itemMatches.length === 0) {
        itemMatches = xml.match(/<entry[^>]*>[\s\S]*?<\/entry>/gi) || []; // Atom format
    }
    for (const itemXml of itemMatches) {
        const title = extractXmlTag(itemXml, 'title');
        const link = extractXmlTag(itemXml, 'link') || extractAtomLink(itemXml);
        const pubDate = extractXmlTag(itemXml, 'pubDate') ||
            extractXmlTag(itemXml, 'published') ||
            extractXmlTag(itemXml, 'dc:date');
        const description = extractXmlTag(itemXml, 'description') ||
            extractXmlTag(itemXml, 'content') ||
            extractXmlTag(itemXml, 'summary');
        if (!title)
            continue;
        // Check if item matches any condition keyword (more lenient)
        const text = (title + ' ' + description).toLowerCase();
        const matches = keywords.some(kw => text.includes(kw));
        // Also include general biotech deals even without condition match
        const isDealNews = /\$\d|million|billion|acquisition|partnership|collaboration|fda|approved|phase\s*[123]/i.test(text);
        if (!matches && !isDealNews)
            continue;
        // Extract deal info
        const dealType = extractDealType(title + ' ' + description);
        const dealValue = extractDealValue(title + ' ' + description);
        const companies = extractCompanies(title);
        items.push({
            title: cleanHtml(title),
            link: link || '',
            pubDate: pubDate || new Date().toISOString(),
            source,
            companies,
            dealType,
            dealValue
        });
    }
    return items;
}
function extractAtomLink(xml) {
    const match = xml.match(/<link[^>]*href=["']([^"']+)["'][^>]*>/i);
    return match ? match[1] : '';
}
function extractXmlTag(xml, tag) {
    // Handle CDATA
    const cdataMatch = xml.match(new RegExp(`<${tag}[^>]*><!\\[CDATA\\[([\\s\\S]*?)\\]\\]><\\/${tag}>`, 'i'));
    if (cdataMatch)
        return cdataMatch[1].trim();
    // Handle namespaced tags
    const nsMatch = xml.match(new RegExp(`<[^:]*:${tag}[^>]*>([\\s\\S]*?)<\\/[^:]*:${tag}>`, 'i'));
    if (nsMatch)
        return nsMatch[1].trim();
    const match = xml.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, 'i'));
    return match ? match[1].trim() : '';
}
function cleanHtml(text) {
    return text
        .replace(/<[^>]+>/g, '')
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .replace(/&nbsp;/g, ' ')
        .replace(/&#\d+;/g, '')
        .trim();
}
function extractDealType(text) {
    const lower = text.toLowerCase();
    if (lower.includes('acquisition') || lower.includes('acquires') || lower.includes('acquire') || lower.includes('buy'))
        return 'Acquisition';
    if (lower.includes('merger') || lower.includes('merge'))
        return 'Merger';
    if (lower.includes('partnership') || lower.includes('partner'))
        return 'Partnership';
    if (lower.includes('collaboration') || lower.includes('collaborate'))
        return 'Collaboration';
    if (lower.includes('licensing') || lower.includes('license'))
        return 'Licensing';
    if (lower.includes('investment') || lower.includes('invests'))
        return 'Investment';
    if (lower.includes('ipo') || lower.includes('initial public'))
        return 'IPO';
    if (lower.includes('funding') || lower.includes('raises') || lower.includes('series'))
        return 'Funding';
    if (lower.includes('fda approval') || lower.includes('approved') || lower.includes('green light'))
        return 'FDA Approval';
    if (lower.includes('phase 3') || lower.includes('phase 2') || lower.includes('pivotal'))
        return 'Clinical Update';
    if (lower.includes('data') || lower.includes('results') || lower.includes('readout'))
        return 'Data Readout';
    return null;
}
function extractDealValue(text) {
    // Match patterns like $500M, $1.2B, $50 million, up to $X, etc.
    const patterns = [
        /up\s+to\s+\$[\d,.]+\s*[bB](?:illion)?/,
        /up\s+to\s+\$[\d,.]+\s*[mM](?:illion)?/,
        /\$[\d,.]+\s*[bB](?:illion)?/,
        /\$[\d,.]+\s*[mM](?:illion)?/,
        /\$[\d,.]+\s*[kK]/,
        /\$[\d,]+/
    ];
    for (const pattern of patterns) {
        const match = text.match(pattern);
        if (match)
            return match[0];
    }
    return null;
}
function extractCompanies(title) {
    const companies = [];
    const words = title.split(/[\s,]+/);
    let current = '';
    for (const word of words) {
        if (['and', 'the', 'a', 'an', 'to', 'for', 'in', 'of', 'with', 'on', 'at', 'from', 'by'].includes(word.toLowerCase())) {
            if (current) {
                companies.push(current.trim());
                current = '';
            }
            continue;
        }
        if (word[0] && word[0] === word[0].toUpperCase() && word.length > 2) {
            current += (current ? ' ' : '') + word;
        }
        else if (current) {
            companies.push(current.trim());
            current = '';
        }
    }
    if (current)
        companies.push(current.trim());
    return companies
        .filter(c => c.length > 3 && !['FDA', 'CEO', 'USA', 'Inc', 'Ltd', 'Phase', 'Trial', 'Data', 'Drug'].includes(c))
        .slice(0, 3);
}
// ============================================
// PubMed API - Improved for accurate KOL data
// ============================================
async function fetchPubMedData(condition) {
    console.log(`  [Landscape] Fetching PubMed data for "${condition}"...`);
    try {
        const currentYear = new Date().getFullYear();
        // 1. Get total publication count
        const countUrl = `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=${encodeURIComponent(condition)}&rettype=count&retmode=json`;
        const countResponse = await fetch(countUrl, {
            headers: { 'User-Agent': 'Helix/1.0 (biotech-research-tool)' },
            signal: AbortSignal.timeout(15000)
        });
        let totalCount = 0;
        if (countResponse.ok) {
            const countData = await countResponse.json();
            totalCount = parseInt(countData.esearchresult?.count || '0', 10);
        }
        console.log(`  [Landscape] Total PubMed publications: ${totalCount}`);
        // 2. Get publication counts by year (last 10 years) - sequential to avoid rate limiting
        const byYear = [];
        for (let year = currentYear - 9; year <= currentYear; year++) {
            const count = await fetchYearCount(condition, year);
            byYear.push({ year, count });
            console.log(`  [Landscape] Year ${year}: ${count} publications`);
            // Delay between requests to avoid rate limiting (PubMed allows 3/sec without API key)
            await sleep(400);
        }
        // 3. Get top KOLs by fetching recent publications and counting authors
        const topKOLs = await fetchTopKOLs(condition, currentYear);
        console.log(`  [Landscape] Found ${topKOLs.length} active KOLs`);
        return { totalCount, byYear, topKOLs };
    }
    catch (error) {
        console.log(`  [Landscape] Error fetching PubMed data: ${error}`);
        return { totalCount: 0, byYear: [], topKOLs: [] };
    }
}
async function fetchYearCount(condition, year) {
    // Use mindate/maxdate format which works more reliably
    const url = `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=${encodeURIComponent(condition)}&mindate=${year}&maxdate=${year}&datetype=pdat&rettype=count&retmode=json`;
    // Retry up to 3 times with increasing delays
    for (let attempt = 0; attempt < 3; attempt++) {
        try {
            if (attempt > 0) {
                await sleep(500 * attempt); // Increasing backoff
            }
            const response = await fetch(url, {
                headers: { 'User-Agent': 'Helix/1.0 (biotech-research-tool)' },
                signal: AbortSignal.timeout(10000)
            });
            if (response.status === 429) {
                // Rate limited, wait and retry
                await sleep(1000);
                continue;
            }
            if (!response.ok)
                return 0;
            const data = await response.json();
            return parseInt(data.esearchresult?.count || '0', 10);
        }
        catch {
            // Retry on error
        }
    }
    return 0;
}
async function fetchTopKOLs(condition, currentYear) {
    // Fetch recent publications (last 3 years) to find active researchers
    const searchUrl = `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=${encodeURIComponent(condition)}&mindate=${currentYear - 2}&maxdate=${currentYear}&datetype=pdat&retmax=500&retmode=json&sort=relevance`;
    try {
        const searchResponse = await fetch(searchUrl, {
            headers: { 'User-Agent': 'Helix/1.0 (biotech-research-tool)' },
            signal: AbortSignal.timeout(20000)
        });
        if (!searchResponse.ok) {
            console.log(`  [Landscape] PubMed search returned ${searchResponse.status}`);
            return [];
        }
        const searchData = await searchResponse.json();
        const idList = searchData.esearchresult?.idlist || [];
        if (idList.length === 0) {
            return [];
        }
        console.log(`  [Landscape] Found ${idList.length} recent publications for KOL analysis`);
        // Fetch article details in batches
        const authorCounts = {};
        // Process in batches of 50 (smaller batches for reliability)
        for (let i = 0; i < Math.min(idList.length, 300); i += 50) {
            const batchIds = idList.slice(i, i + 50).join(',');
            const fetchUrl = `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=${batchIds}&retmode=xml`;
            try {
                const fetchResponse = await fetch(fetchUrl, {
                    headers: { 'User-Agent': 'Helix/1.0 (biotech-research-tool)' },
                    signal: AbortSignal.timeout(30000)
                });
                if (!fetchResponse.ok) {
                    console.log(`  [Landscape] PubMed efetch returned ${fetchResponse.status}`);
                    continue;
                }
                const xmlText = await fetchResponse.text();
                // Parse author information from XML - handle both formats
                const articleMatches = xmlText.match(/<PubmedArticle[\s>][\s\S]*?<\/PubmedArticle>/gi) || [];
                for (const articleXml of articleMatches) {
                    // Get publication year
                    const yearMatch = articleXml.match(/<PubDate>[\s\S]*?<Year>(\d{4})<\/Year>/);
                    const pubYear = yearMatch ? parseInt(yearMatch[1], 10) : currentYear;
                    // Get authors with affiliations
                    const authorListMatch = articleXml.match(/<AuthorList[^>]*>[\s\S]*?<\/AuthorList>/i);
                    if (!authorListMatch)
                        continue;
                    const authorMatches = authorListMatch[0].match(/<Author[^>]*>[\s\S]*?<\/Author>/gi) || [];
                    // Only count first and last authors (typically key contributors)
                    const authorsToCount = [];
                    if (authorMatches.length > 2) {
                        if (authorMatches[0])
                            authorsToCount.push(authorMatches[0]);
                        const lastAuthor = authorMatches[authorMatches.length - 1];
                        if (lastAuthor)
                            authorsToCount.push(lastAuthor);
                    }
                    else {
                        authorsToCount.push(...authorMatches.filter((a) => !!a));
                    }
                    for (const authorXml of authorsToCount) {
                        const lastName = extractXmlTag(authorXml, 'LastName');
                        const foreName = extractXmlTag(authorXml, 'ForeName') || extractXmlTag(authorXml, 'Initials');
                        if (!lastName)
                            continue;
                        const fullName = foreName ? `${lastName} ${foreName}` : lastName;
                        // Extract affiliation
                        const affiliationMatch = authorXml.match(/<AffiliationInfo>[\s\S]*?<Affiliation>([^<]+)<\/Affiliation>/i);
                        const affiliation = affiliationMatch ? affiliationMatch[1].trim() : null;
                        // Try to extract email from affiliation
                        const emailMatch = affiliation?.match(/[\w.+-]+@[\w.-]+\.\w+/);
                        const email = emailMatch ? emailMatch[0] : null;
                        // Extract institution from affiliation
                        const institution = affiliation ? extractInstitution(affiliation) : null;
                        if (!authorCounts[fullName]) {
                            authorCounts[fullName] = {
                                count: 0,
                                institution,
                                email,
                                years: new Set()
                            };
                        }
                        authorCounts[fullName].count++;
                        authorCounts[fullName].years.add(pubYear);
                        // Update institution/email if we got better data
                        if (institution && !authorCounts[fullName].institution) {
                            authorCounts[fullName].institution = institution;
                        }
                        if (email && !authorCounts[fullName].email) {
                            authorCounts[fullName].email = email;
                        }
                    }
                }
            }
            catch (batchError) {
                console.log(`  [Landscape] Error processing batch: ${batchError}`);
                continue;
            }
            // Delay between batches to avoid rate limiting (PubMed allows 3/sec without API key)
            await sleep(500);
        }
        console.log(`  [Landscape] Found ${Object.keys(authorCounts).length} unique authors`);
        // Get top candidates by sample count (take more than we need, then re-rank)
        const topCandidates = Object.entries(authorCounts)
            .filter(([name, data]) => {
            return data.count >= 2 && name.length > 3;
        })
            .sort((a, b) => b[1].count - a[1].count)
            .slice(0, 25);
        console.log(`  [Landscape] Enriching ${topCandidates.length} KOL candidates with real publication counts...`);
        // Enrich each candidate with their real PubMed publication count for this condition
        const enrichedAuthors = [];
        for (const [name, data] of topCandidates) {
            const realCount = await getAuthorPublicationCount(name, condition);
            await sleep(400); // Rate limit: PubMed allows 3/sec without key
            const recentCount = await getAuthorPublicationCount(name, condition, 3);
            await sleep(400);
            enrichedAuthors.push({
                name,
                institution: data.institution,
                email: data.email,
                publicationCount: realCount > 0 ? realCount : data.count,
                recentPublications: recentCount > 0 ? recentCount : data.count,
                hIndex: null,
            });
        }
        // Re-sort by real publication count and return top 15
        enrichedAuthors.sort((a, b) => b.publicationCount - a.publicationCount);
        const topKOLs = enrichedAuthors.slice(0, 15);
        console.log(`  [Landscape] Top KOL: ${topKOLs[0]?.name} (${topKOLs[0]?.publicationCount} publications)`);
        return topKOLs;
    }
    catch (error) {
        console.log(`  [Landscape] Error fetching KOL data: ${error}`);
        return [];
    }
}
// Cache for author publication counts (avoids repeat lookups within same session)
const authorCountCache = new Map();
/**
 * Get an author's total publication count for a condition via PubMed esearch.
 * Uses rettype=count so only the count is returned (no abstracts fetched).
 */
async function getAuthorPublicationCount(authorName, condition, yearsBack) {
    // Build the PubMed author query
    // Format: "LastName FirstInitial"[Author] AND "condition"
    const nameParts = authorName.split(' ');
    const lastName = nameParts[0];
    const firstName = nameParts.slice(1).join(' ');
    // Use abbreviated author format for broader matching: "LastName FI"
    const authorQuery = firstName
        ? `${lastName} ${firstName[0]}`
        : lastName;
    let query = `"${authorQuery}"[Author] AND "${condition}"`;
    // Add year filter if specified
    if (yearsBack) {
        const currentYear = new Date().getFullYear();
        const fromYear = currentYear - yearsBack;
        query += ` AND ${fromYear}:${currentYear}[pdat]`;
    }
    const cacheKey = query;
    if (authorCountCache.has(cacheKey)) {
        return authorCountCache.get(cacheKey);
    }
    try {
        const url = `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=${encodeURIComponent(query)}&rettype=count&retmode=json`;
        const response = await fetch(url, {
            headers: { 'User-Agent': 'Helix/1.0 (biotech-research-tool)' },
            signal: AbortSignal.timeout(10000)
        });
        if (!response.ok) {
            console.log(`  [KOL] PubMed returned ${response.status} for "${authorQuery}"`);
            return 0;
        }
        const data = await response.json();
        const count = parseInt(data.esearchresult?.count || '0', 10);
        if (count > 0) {
            console.log(`  [KOL] ${authorName}: ${count} publications${yearsBack ? ` (last ${yearsBack}yr)` : ''}`);
        }
        authorCountCache.set(cacheKey, count);
        return count;
    }
    catch (err) {
        console.log(`  [KOL] Error for "${authorQuery}": ${err}`);
        return 0;
    }
}
function extractInstitution(affiliation) {
    // Common patterns for extracting institution names
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
        /MIT/i,
    ];
    for (const pattern of patterns) {
        const match = affiliation.match(pattern);
        if (match) {
            return match[0].trim();
        }
    }
    // Fallback: take first part before comma
    const parts = affiliation.split(',');
    if (parts[0] && parts[0].length < 100) {
        return parts[0].trim();
    }
    return null;
}
// ============================================
// Main Function
// ============================================
async function getLandscapeData(condition) {
    // Check cache first
    const cached = getCachedLandscape(condition);
    if (cached) {
        console.log(`  [Landscape] Using cached data for "${condition}"`);
        return cached;
    }
    console.log(`  [Landscape] Fetching fresh data for "${condition}"...`);
    // Fetch all sources in parallel
    const [clinicalTrials, dealsNews, research] = await Promise.all([
        fetchClinicalTrials(condition),
        fetchDealsNews(condition),
        fetchPubMedData(condition)
    ]);
    // Extract molecules from trials
    const molecules = extractMolecules(clinicalTrials.trials);
    // Count unique active companies (sponsors + deal companies)
    const companies = new Set();
    for (const trial of clinicalTrials.trials) {
        if (trial.sponsor && trial.sponsor !== 'Unknown') {
            companies.add(trial.sponsor);
        }
    }
    for (const deal of dealsNews) {
        for (const company of deal.companies) {
            companies.add(company);
        }
    }
    const landscapeData = {
        condition,
        fetchedAt: new Date().toISOString(),
        summary: {
            totalTrials: clinicalTrials.trials.length,
            activeCompanies: companies.size,
            recentDeals: dealsNews.filter(d => d.dealType).length,
            totalPublications: research.totalCount,
            uniqueMolecules: molecules.length
        },
        clinicalTrials,
        molecules,
        dealsNews,
        research
    };
    // Cache the result
    saveCachedLandscape(condition, landscapeData);
    return landscapeData;
}
// ============================================
// Cache Functions
// ============================================
function getCacheFilePath(condition) {
    const sanitized = condition.toLowerCase().replace(/[^a-z0-9]+/g, '-');
    return path.join(CACHE_DIR, `${sanitized}.json`);
}
function getCachedLandscape(condition) {
    const filePath = getCacheFilePath(condition);
    if (!fs.existsSync(filePath))
        return null;
    try {
        const data = fs.readFileSync(filePath, 'utf-8');
        const cached = JSON.parse(data);
        // Check if cache is still valid
        if (cached.fetchedAt) {
            const cacheAge = Date.now() - new Date(cached.fetchedAt).getTime();
            if (cacheAge > CACHE_MAX_AGE_MS) {
                console.log(`  [Landscape] Cache expired for "${condition}"`);
                return null;
            }
        }
        return cached;
    }
    catch {
        return null;
    }
}
function saveCachedLandscape(condition, data) {
    if (!fs.existsSync(CACHE_DIR)) {
        fs.mkdirSync(CACHE_DIR, { recursive: true });
    }
    const filePath = getCacheFilePath(condition);
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
}
// ============================================
// CSV Export - Updated with molecules
// ============================================
function generateLandscapeCSV(data) {
    const lines = [];
    // Header
    lines.push(`Therapeutic Landscape Report: ${data.condition}`);
    lines.push(`Generated: ${data.fetchedAt}`);
    lines.push('');
    // Summary
    lines.push('SUMMARY');
    lines.push(`Total Trials,${data.summary.totalTrials}`);
    lines.push(`Active Companies,${data.summary.activeCompanies}`);
    lines.push(`Recent Deals,${data.summary.recentDeals}`);
    lines.push(`Total Publications,${data.summary.totalPublications}`);
    lines.push(`Unique Molecules,${data.summary.uniqueMolecules}`);
    lines.push('');
    // Molecules
    lines.push('MOLECULE LANDSCAPE');
    lines.push('Molecule,Mechanism,Sponsor,Highest Phase,Trial Count,Status');
    for (const mol of data.molecules) {
        lines.push(`"${mol.name}","${mol.mechanism || ''}","${mol.sponsor.replace(/"/g, '""')}","${mol.highestPhase}",${mol.trialCount},"${mol.status}"`);
    }
    lines.push('');
    // Clinical Trials
    lines.push('CLINICAL TRIALS');
    lines.push('NCT ID,Title,Status,Phase,Sponsor,Interventions,Primary Endpoint,Enrollment');
    for (const trial of data.clinicalTrials.trials) {
        lines.push(`"${trial.nctId}","${trial.title.replace(/"/g, '""')}","${trial.status}","${trial.phase}","${trial.sponsor.replace(/"/g, '""')}","${trial.interventions.join('; ')}","${(trial.primaryEndpoint || '').replace(/"/g, '""')}","${trial.enrollment || ''}"`);
    }
    lines.push('');
    // Deals
    lines.push('DEALS & NEWS');
    lines.push('Date,Title,Source,Type,Value,Link');
    for (const deal of data.dealsNews) {
        const date = new Date(deal.pubDate).toISOString().split('T')[0];
        lines.push(`"${date}","${deal.title.replace(/"/g, '""')}","${deal.source}","${deal.dealType || ''}","${deal.dealValue || ''}","${deal.link}"`);
    }
    lines.push('');
    // KOLs
    lines.push('KEY OPINION LEADERS');
    lines.push('Rank,Name,Institution,Email,Publications (Recent)');
    data.research.topKOLs.forEach((kol, i) => {
        lines.push(`${i + 1},"${kol.name}","${kol.institution || ''}","${kol.email || ''}",${kol.publicationCount}`);
    });
    return lines.join('\n');
}
// ============================================
// Utility
// ============================================
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
//# sourceMappingURL=landscape.js.map