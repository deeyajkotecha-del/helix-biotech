"use strict";
/**
 * Pharma Company Registry
 *
 * Registry of major pharma companies with IR page URLs,
 * presentation URL patterns, and verification status.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.PHARMA_COMPANIES = void 0;
exports.getAllTickers = getAllTickers;
exports.getVerifiedCompanies = getVerifiedCompanies;
exports.buildPresentationUrl = buildPresentationUrl;
exports.getJPM2026Urls = getJPM2026Urls;
// ============================================
// Company Registry
// ============================================
exports.PHARMA_COMPANIES = {
    MRK: {
        ticker: 'MRK',
        name: 'Merck & Co.',
        irPageUrl: 'https://www.merck.com/investor-relations/',
        cdnBase: 'https://s21.q4cdn.com/488056881/files/doc_presentations/',
        urlPatterns: {
            jpm: 'https://s21.q4cdn.com/488056881/files/doc_presentations/{year}-JPM-Presentation.pdf',
            quarterly: 'https://s21.q4cdn.com/488056881/files/doc_presentations/{year}-Q{quarter}-Earnings.pdf',
        },
        verified: true,
    },
    BMY: {
        ticker: 'BMY',
        name: 'Bristol-Myers Squibb',
        irPageUrl: 'https://www.bms.com/investors.html',
        cdnBase: 'https://s21.q4cdn.com/104322789/files/doc_presentations/',
        urlPatterns: {
            jpm: 'https://s21.q4cdn.com/104322789/files/doc_presentations/{year}-JPM-Healthcare-Conference.pdf',
        },
        verified: true,
    },
    AZN: {
        ticker: 'AZN',
        name: 'AstraZeneca',
        irPageUrl: 'https://www.astrazeneca.com/investor-relations.html',
        cdnBase: 'https://www.astrazeneca.com/content/dam/az/Investor_Relations/',
        urlPatterns: {
            jpm: 'https://www.astrazeneca.com/content/dam/az/Investor_Relations/JPM-{year}-presentation.pdf',
        },
        verified: true,
    },
    PFE: {
        ticker: 'PFE',
        name: 'Pfizer Inc.',
        irPageUrl: 'https://investors.pfizer.com/',
        cdnBase: 'https://s28.q4cdn.com/781576035/files/doc_presentations/',
        urlPatterns: {
            jpm: 'https://s28.q4cdn.com/781576035/files/doc_presentations/{year}-JPM-Healthcare-Conference.pdf',
        },
        verified: true,
    },
    LLY: {
        ticker: 'LLY',
        name: 'Eli Lilly and Company',
        irPageUrl: 'https://investor.lilly.com/',
        verified: false,
    },
    ABBV: {
        ticker: 'ABBV',
        name: 'AbbVie Inc.',
        irPageUrl: 'https://investors.abbvie.com/',
        verified: false,
    },
    JNJ: {
        ticker: 'JNJ',
        name: 'Johnson & Johnson',
        irPageUrl: 'https://www.investor.jnj.com/',
        verified: false,
    },
    NVS: {
        ticker: 'NVS',
        name: 'Novartis AG',
        irPageUrl: 'https://www.novartis.com/investors',
        verified: false,
    },
    ROG: {
        ticker: 'ROG',
        name: 'Roche Holding AG',
        irPageUrl: 'https://www.roche.com/investors',
        verified: false,
    },
    AMGN: {
        ticker: 'AMGN',
        name: 'Amgen Inc.',
        irPageUrl: 'https://investors.amgen.com/',
        verified: false,
    },
    GILD: {
        ticker: 'GILD',
        name: 'Gilead Sciences',
        irPageUrl: 'https://investors.gilead.com/',
        verified: false,
    },
    REGN: {
        ticker: 'REGN',
        name: 'Regeneron Pharmaceuticals',
        irPageUrl: 'https://investor.regeneron.com/',
        verified: false,
    },
    VRTX: {
        ticker: 'VRTX',
        name: 'Vertex Pharmaceuticals',
        irPageUrl: 'https://investors.vrtx.com/',
        verified: false,
    },
};
// ============================================
// Helper Functions
// ============================================
/**
 * Get all registered ticker symbols
 */
function getAllTickers() {
    return Object.keys(exports.PHARMA_COMPANIES);
}
/**
 * Get only companies with verified IR URL patterns
 */
function getVerifiedCompanies() {
    return Object.values(exports.PHARMA_COMPANIES).filter((c) => c.verified);
}
/**
 * Build a presentation URL from a company's URL pattern
 */
function buildPresentationUrl(ticker, type, params) {
    const company = exports.PHARMA_COMPANIES[ticker.toUpperCase()];
    if (!company?.urlPatterns?.[type])
        return null;
    let url = company.urlPatterns[type];
    url = url.replace('{year}', String(params.year));
    if (params.quarter !== undefined) {
        url = url.replace('{quarter}', String(params.quarter));
    }
    return url;
}
/**
 * Get JPM presentation URLs for a given year across all verified companies
 */
function getJPM2026Urls() {
    return getVerifiedCompanies().map((company) => ({
        ticker: company.ticker,
        name: company.name,
        url: buildPresentationUrl(company.ticker, 'jpm', { year: 2026 }),
    }));
}
//# sourceMappingURL=pharma-registry.js.map