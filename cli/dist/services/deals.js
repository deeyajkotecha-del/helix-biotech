"use strict";
/**
 * Deals Service
 *
 * Fetches and tracks biopharma deals from RSS feeds,
 * SEC filings, and news sources.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.fetchRecentDeals = fetchRecentDeals;
exports.searchDealsByCompany = searchDealsByCompany;
exports.searchDealsByAsset = searchDealsByAsset;
exports.getDealsByTherapeuticArea = getDealsByTherapeuticArea;
exports.getMAActivity = getMAActivity;
exports.fetchRSSFeed = fetchRSSFeed;
exports.parseRSSXml = parseRSSXml;
exports.extractDealInfo = extractDealInfo;
exports.extractDealType = extractDealType;
exports.extractUpfrontPayment = extractUpfrontPayment;
exports.extractMilestones = extractMilestones;
exports.extractTotalValue = extractTotalValue;
exports.extractRoyalties = extractRoyalties;
exports.extractCompanyNames = extractCompanyNames;
exports.extractAssetInfo = extractAssetInfo;
exports.searchSECMaterialAgreements = searchSECMaterialAgreements;
// RSS feed sources
const RSS_FEEDS = [
    { url: 'https://www.fiercebiotech.com/rss/xml', source: 'Fierce Biotech' },
    { url: 'https://www.fiercepharma.com/rss/xml', source: 'Fierce Pharma' },
    { url: 'https://endpts.com/feed/', source: 'Endpoints News' },
    { url: 'https://www.biopharmadive.com/feeds/news/', source: 'BioPharma Dive' },
];
// ============================================
// Main Functions
// ============================================
/**
 * Fetch recent deals from all sources
 * TODO: Implement comprehensive deal extraction
 * TODO: Add SEC 8-K parsing for material agreements
 */
async function fetchRecentDeals(options) {
    // TODO: Fetch from RSS feeds
    // TODO: Parse deal information
    // TODO: Deduplicate
    throw new Error('Not implemented');
}
/**
 * Search deals by company
 */
async function searchDealsByCompany(companyName) {
    // TODO: Search historical deals
    throw new Error('Not implemented');
}
/**
 * Search deals by drug/asset
 */
async function searchDealsByAsset(assetName) {
    // TODO: Implement
    throw new Error('Not implemented');
}
/**
 * Get deals for a therapeutic area
 */
async function getDealsByTherapeuticArea(therapeuticArea, options) {
    // TODO: Implement
    throw new Error('Not implemented');
}
/**
 * Get M&A activity summary
 */
async function getMAActivity(year) {
    // TODO: Aggregate M&A deals for year
    throw new Error('Not implemented');
}
// ============================================
// RSS Feed Parsing
// ============================================
/**
 * Fetch and parse RSS feed
 */
async function fetchRSSFeed(url, source) {
    // TODO: Fetch RSS XML
    // TODO: Parse items
    throw new Error('Not implemented');
}
/**
 * Parse RSS XML to extract items
 */
function parseRSSXml(xml) {
    const items = [];
    // Match both <item> and <entry> (Atom format)
    const itemMatches = xml.match(/<item[^>]*>[\s\S]*?<\/item>/gi) ||
        xml.match(/<entry[^>]*>[\s\S]*?<\/entry>/gi) ||
        [];
    for (const itemXml of itemMatches) {
        const title = extractXmlTag(itemXml, 'title');
        const link = extractXmlTag(itemXml, 'link') || extractAtomLink(itemXml);
        const pubDate = extractXmlTag(itemXml, 'pubDate') ||
            extractXmlTag(itemXml, 'published') ||
            extractXmlTag(itemXml, 'dc:date');
        const description = extractXmlTag(itemXml, 'description') ||
            extractXmlTag(itemXml, 'content') ||
            extractXmlTag(itemXml, 'summary');
        if (title) {
            items.push({
                title: cleanHtml(title),
                link: link || '',
                pubDate: pubDate || new Date().toISOString(),
                description: cleanHtml(description || '')
            });
        }
    }
    return items;
}
// ============================================
// Deal Extraction
// ============================================
/**
 * Extract deal information from news text
 */
function extractDealInfo(title, description) {
    const text = title + ' ' + description;
    return {
        dealType: extractDealType(text) || undefined,
        terms: {
            upfrontPayment: extractUpfrontPayment(text),
            milestones: extractMilestones(text),
            totalValue: extractTotalValue(text),
            royalties: extractRoyalties(text),
        },
        parties: extractCompanyNames(text),
        asset: extractAssetInfo(text),
    };
}
/**
 * Detect deal type from text
 */
function extractDealType(text) {
    const lower = text.toLowerCase();
    if (lower.includes('acquisition') || lower.includes('acquires') || lower.includes('to buy'))
        return 'Acquisition';
    if (lower.includes('merger') || lower.includes('merge'))
        return 'Merger';
    if (lower.includes('license') && !lower.includes('sublicense'))
        return 'Licensing';
    if (lower.includes('partnership') || lower.includes('partner'))
        return 'Partnership';
    if (lower.includes('collaboration') || lower.includes('collaborate'))
        return 'Collaboration';
    if (lower.includes('co-develop') || lower.includes('codevelop'))
        return 'Co-development';
    if (lower.includes('option agreement') || lower.includes('option to'))
        return 'Option';
    if (lower.includes('asset purchase') || lower.includes('asset sale'))
        return 'Asset Purchase';
    if (lower.includes('series ') || lower.includes('funding') || lower.includes('raises $'))
        return 'Funding';
    if (lower.includes(' ipo ') || lower.includes('initial public'))
        return 'IPO';
    if (lower.includes('spac') || lower.includes('blank check'))
        return 'SPAC';
    return null;
}
/**
 * Extract monetary values from text
 */
function extractUpfrontPayment(text) {
    const patterns = [
        /upfront\s+(?:payment\s+)?(?:of\s+)?\$?([\d,.]+)\s*([mb])/i,
        /\$?([\d,.]+)\s*([mb])(?:illion)?\s+upfront/i,
    ];
    for (const pattern of patterns) {
        const match = text.match(pattern);
        if (match) {
            const value = parseFloat(match[1].replace(/,/g, ''));
            const multiplier = match[2].toLowerCase() === 'b' ? 1000 : 1;
            return value * multiplier;
        }
    }
    return undefined;
}
function extractMilestones(text) {
    const patterns = [
        /(?:up to|total)?\s*\$?([\d,.]+)\s*([mb])(?:illion)?\s+(?:in\s+)?(?:potential\s+)?milestones/i,
        /milestones\s+(?:of\s+)?(?:up to\s+)?\$?([\d,.]+)\s*([mb])/i,
    ];
    for (const pattern of patterns) {
        const match = text.match(pattern);
        if (match) {
            const value = parseFloat(match[1].replace(/,/g, ''));
            const multiplier = match[2].toLowerCase() === 'b' ? 1000 : 1;
            return value * multiplier;
        }
    }
    return undefined;
}
function extractTotalValue(text) {
    const patterns = [
        /(?:total|aggregate)\s+(?:deal\s+)?value\s+(?:of\s+)?(?:up to\s+)?\$?([\d,.]+)\s*([mb])/i,
        /\$?([\d,.]+)\s*([mb])(?:illion)?\s+(?:total\s+)?deal/i,
        /deal\s+(?:valued|worth)\s+(?:at\s+)?(?:up to\s+)?\$?([\d,.]+)\s*([mb])/i,
    ];
    for (const pattern of patterns) {
        const match = text.match(pattern);
        if (match) {
            const value = parseFloat(match[1].replace(/,/g, ''));
            const multiplier = match[2].toLowerCase() === 'b' ? 1000 : 1;
            return value * multiplier;
        }
    }
    return undefined;
}
function extractRoyalties(text) {
    const patterns = [
        /((?:tiered\s+)?royalties?(?:\s+of)?\s+(?:up to\s+)?[\w\s%-]+)/i,
        /((?:single|low|mid|high)[\s-]+(?:single|double)[\s-]+digit(?:\s+royalties)?)/i,
    ];
    for (const pattern of patterns) {
        const match = text.match(pattern);
        if (match) {
            return match[1].trim();
        }
    }
    return undefined;
}
/**
 * Extract company names from text
 */
function extractCompanyNames(text) {
    // TODO: Use NER or company database lookup
    // For now, simple heuristic based on capitalization
    const companies = [];
    const words = text.split(/[\s,]+/);
    let current = '';
    for (const word of words) {
        // Skip common words
        if (['and', 'the', 'a', 'an', 'to', 'for', 'in', 'of', 'with', 'on', 'at', 'from', 'by', 'Inc', 'Ltd', 'Corp'].includes(word)) {
            if (current) {
                companies.push(current.trim());
                current = '';
            }
            continue;
        }
        // Check if capitalized (potential company name)
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
    return companies.filter(c => c.length > 3).slice(0, 5);
}
/**
 * Extract asset/drug information
 */
function extractAssetInfo(text) {
    // TODO: Implement drug name extraction
    // TODO: Match against molecule database
    return undefined;
}
// ============================================
// SEC 8-K Integration
// ============================================
/**
 * Search SEC 8-K filings for material agreements
 * TODO: Implement SEC EDGAR integration
 */
async function searchSECMaterialAgreements(companyName, options) {
    // TODO: Search SEC EDGAR for 8-K filings
    // TODO: Filter for "Material Definitive Agreement" (Item 1.01)
    // TODO: Parse agreement details
    throw new Error('Not implemented');
}
// ============================================
// Utility Functions
// ============================================
function extractXmlTag(xml, tag) {
    const cdataMatch = xml.match(new RegExp(`<${tag}[^>]*><!\\[CDATA\\[([\\s\\S]*?)\\]\\]><\\/${tag}>`, 'i'));
    if (cdataMatch)
        return cdataMatch[1].trim();
    const match = xml.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, 'i'));
    return match ? match[1].trim() : '';
}
function extractAtomLink(xml) {
    const match = xml.match(/<link[^>]*href=["']([^"']+)["'][^>]*>/i);
    return match ? match[1] : '';
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
//# sourceMappingURL=deals.js.map