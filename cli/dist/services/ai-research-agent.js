"use strict";
/**
 * AI Research Agent
 *
 * Uses Claude API with web search to automatically discover and verify
 * drug assets for any therapeutic target. Provides the same research
 * capability as Claude Co-work but automated.
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.researchTarget = researchTarget;
exports.convertToKnownAssets = convertToKnownAssets;
const sdk_1 = __importDefault(require("@anthropic-ai/sdk"));
const config_1 = require("../config");
// ============================================
// Main Research Function
// ============================================
/**
 * Research a therapeutic target using Claude with web search
 */
async function researchTarget(target) {
    const config = (0, config_1.getConfig)();
    // Debug: Check API key
    console.log(`[AI Research] ========== DEBUG ==========`);
    console.log(`[AI Research] API Key exists: ${!!config.claudeApiKey}`);
    console.log(`[AI Research] API Key prefix: ${config.claudeApiKey?.substring(0, 15)}...`);
    console.log(`[AI Research] Target: ${target}`);
    if (!config.claudeApiKey) {
        const errorMsg = 'Anthropic API key not configured for AI research.\n' +
            'Set ANTHROPIC_API_KEY in your environment or .env file.';
        console.error(`[AI Research] ERROR: ${errorMsg}`);
        throw new Error(errorMsg);
    }
    console.log(`[AI Research] Starting research for target: ${target}`);
    const startTime = Date.now();
    const anthropic = new sdk_1.default({
        apiKey: config.claudeApiKey,
    });
    const researchPrompt = buildResearchPrompt(target);
    console.log(`[AI Research] Prompt length: ${researchPrompt.length} chars`);
    try {
        console.log(`[AI Research] Calling Claude API with web search...`);
        let response;
        try {
            // First try with web search tool
            response = await anthropic.messages.create({
                model: 'claude-sonnet-4-20250514',
                max_tokens: 8000,
                tools: [{
                        type: 'web_search_20250305',
                        name: 'web_search',
                    }], // Type assertion needed for beta feature
                messages: [{
                        role: 'user',
                        content: researchPrompt,
                    }],
            });
        }
        catch (webSearchError) {
            // If web search fails (unsupported, rate limit, etc.), try without it
            console.log(`[AI Research] Web search failed (${webSearchError?.message}), trying without web search...`);
            response = await anthropic.messages.create({
                model: 'claude-sonnet-4-20250514',
                max_tokens: 8000,
                messages: [{
                        role: 'user',
                        content: researchPrompt + '\n\nNote: Use your training knowledge to compile this list. Focus on well-known drugs and recent developments you are aware of.',
                    }],
            });
        }
        console.log(`[AI Research] API Response received`);
        console.log(`[AI Research] Response stop_reason: ${response.stop_reason}`);
        console.log(`[AI Research] Response content blocks: ${response.content.length}`);
        // Log content block types
        response.content.forEach((block, i) => {
            console.log(`[AI Research] Block ${i}: type=${block.type}`);
            if (block.type === 'text') {
                console.log(`[AI Research] Block ${i} text length: ${block.text.length}`);
                console.log(`[AI Research] Block ${i} text preview: ${block.text.substring(0, 500)}...`);
            }
        });
        // Extract assets from response
        const assets = parseAssetsFromResponse(response, target);
        const elapsed = Date.now() - startTime;
        console.log(`[AI Research] Completed in ${(elapsed / 1000).toFixed(1)}s - Found ${assets.length} assets`);
        return {
            target,
            assets,
            researchedAt: new Date().toISOString(),
            searchQueries: getSearchQueriesUsed(target),
            totalSourcesChecked: countSourcesFromResponse(response),
            dataSource: 'ai-research',
        };
    }
    catch (error) {
        console.error(`[AI Research] ========== ERROR ==========`);
        console.error(`[AI Research] Error type: ${error?.constructor?.name}`);
        console.error(`[AI Research] Error message: ${error?.message}`);
        console.error(`[AI Research] Error status: ${error?.status}`);
        console.error(`[AI Research] Full error:`, error);
        if (error instanceof sdk_1.default.APIError) {
            if (error.status === 401) {
                throw new Error('Invalid Anthropic API key. Please check ANTHROPIC_API_KEY in your .env file or environment variables.');
            }
            if (error.status === 429) {
                throw new Error('API rate limit exceeded. Please try again later.');
            }
            throw new Error(`AI research API error (${error.status}): ${error.message}`);
        }
        throw error;
    }
}
// ============================================
// Prompt Building
// ============================================
function buildResearchPrompt(target) {
    return `You are a biotech research analyst specializing in drug development and competitive intelligence.

Your task is to compile a comprehensive list of ALL drugs and therapeutics currently in development that target ${target}.

## Search Methodology

Search for information using these queries (search all of them):
1. "${target} clinical trials drugs companies 2024 2025"
2. "${target} antibody ADC CAR-T bispecific pipeline"
3. "anti-${target} therapy drug development"
4. "${target} monoclonal antibody development"
5. "Chinese biotech ${target} drug"
6. "${target} phase 3 clinical trial"
7. "${target} drug deal licensing partnership"

## For Each Asset Found, Provide:

1. **Drug Name**: Primary name and all code names (e.g., "Tulisokibart" with codes "PRA023", "MK-7240")
2. **Company/Owner**: Who owns or is developing the drug
3. **Development Phase**: Preclinical, Phase 1, Phase 1/2, Phase 2, Phase 3, Filed, or Approved
4. **Modality**: mAb, ADC, CAR-T, Bispecific, Small Molecule, etc.
5. **Mechanism**: How it works (e.g., "Anti-TL1A monoclonal antibody blocking TNF superfamily signaling")
6. **Lead Indication**: Primary disease target
7. **Clinical Data**: Key efficacy data if available (e.g., "47% remission vs 20% placebo")
8. **Deal Information**: Any licensing, partnership, or acquisition deals with values
9. **Sources**: URLs or publications that verify this information

## CRITICAL VERIFICATION RULES

Before including ANY drug, verify it ACTUALLY targets ${target}:
- Check that the drug's mechanism specifically involves ${target}
- Don't include combination partners (e.g., if pembrolizumab is used WITH a ${target} drug, don't list pembrolizumab as a ${target} drug)
- Don't include drugs that target different proteins
- Don't include standard chemotherapy, steroids, or supportive care drugs
- If uncertain, mark confidence as LOW

## Exclusion List (DO NOT INCLUDE)

- Generic chemotherapy: cisplatin, carboplatin, paclitaxel, docetaxel, etc.
- Standard immunotherapy: pembrolizumab, nivolumab, atezolizumab, ipilimumab (unless they ARE ${target} drugs)
- Steroids: prednisone, dexamethasone, methylprednisolone
- Supportive care: filgrastim, ondansetron, etc.

## Output Format

Return your findings as a JSON array. Be thorough - include ALL assets you find, even early-stage ones.

\`\`\`json
[
  {
    "name": "Primary Drug Name",
    "codeNames": ["CODE-123", "XYZ-456"],
    "genericName": "generic name if exists",
    "owner": "Company Name",
    "ownerType": "Big Pharma|Biotech|Chinese Biotech|Academic",
    "partner": "Partner company if any",
    "phase": "Phase 2",
    "status": "Active",
    "modality": "mAb",
    "mechanism": "Description of mechanism of action",
    "leadIndication": "Primary indication",
    "otherIndications": ["Other indication 1"],
    "keyData": "Key clinical data if available",
    "trialIds": ["NCT12345678"],
    "deal": {
      "partner": "Deal partner",
      "value": "$500M upfront + $2B milestones",
      "upfront": 500,
      "milestones": 2000,
      "date": "2024-01"
    },
    "confidence": "HIGH|MEDIUM|LOW",
    "sources": ["https://source1.com", "https://source2.com"],
    "verificationNotes": "Notes about verification"
  }
]
\`\`\`

Now research ${target} thoroughly and return the JSON array of all assets found.`;
}
function getSearchQueriesUsed(target) {
    return [
        `${target} clinical trials drugs companies 2024 2025`,
        `${target} antibody ADC CAR-T bispecific pipeline`,
        `anti-${target} therapy drug development`,
        `${target} monoclonal antibody development`,
        `Chinese biotech ${target} drug`,
        `${target} phase 3 clinical trial`,
        `${target} drug deal licensing partnership`,
    ];
}
// ============================================
// Response Parsing
// ============================================
function parseAssetsFromResponse(response, target) {
    const assets = [];
    // Find text content blocks
    for (const block of response.content) {
        if (block.type === 'text') {
            const text = block.text;
            // Try to extract JSON from the response
            const jsonMatch = text.match(/```json\s*([\s\S]*?)\s*```/);
            if (jsonMatch) {
                try {
                    const parsed = JSON.parse(jsonMatch[1]);
                    if (Array.isArray(parsed)) {
                        for (const item of parsed) {
                            const asset = normalizeAsset(item, target);
                            if (asset && isValidAsset(asset)) {
                                assets.push(asset);
                            }
                        }
                    }
                }
                catch (e) {
                    console.warn('[AI Research] Failed to parse JSON response:', e);
                }
            }
            else {
                // Try to parse raw JSON if no code block
                try {
                    const parsed = JSON.parse(text);
                    if (Array.isArray(parsed)) {
                        for (const item of parsed) {
                            const asset = normalizeAsset(item, target);
                            if (asset && isValidAsset(asset)) {
                                assets.push(asset);
                            }
                        }
                    }
                }
                catch {
                    // Not JSON, try to extract structured data from text
                    const extracted = extractAssetsFromText(text, target);
                    assets.push(...extracted);
                }
            }
        }
    }
    // Deduplicate by name
    const seen = new Set();
    const unique = [];
    for (const asset of assets) {
        const key = asset.name.toLowerCase().replace(/[-\s]/g, '');
        if (!seen.has(key)) {
            seen.add(key);
            unique.push(asset);
        }
    }
    return unique;
}
function normalizeAsset(raw, target) {
    if (!raw || typeof raw !== 'object')
        return null;
    if (!raw.name && !raw.drugName && !raw.primaryName)
        return null;
    const name = raw.name || raw.drugName || raw.primaryName;
    const codeNames = Array.isArray(raw.codeNames) ? raw.codeNames :
        raw.codeName ? [raw.codeName] : [];
    return {
        name,
        codeNames,
        genericName: raw.genericName,
        target,
        modality: raw.modality || 'Unknown',
        mechanism: raw.mechanism || raw.mechanismOfAction,
        owner: raw.owner || raw.company || 'Unknown',
        ownerType: raw.ownerType,
        partner: raw.partner,
        phase: normalizePhase(raw.phase || raw.developmentPhase || 'Unknown'),
        status: raw.status || 'Active',
        leadIndication: raw.leadIndication || raw.indication || 'Not specified',
        otherIndications: Array.isArray(raw.otherIndications) ? raw.otherIndications : undefined,
        keyData: raw.keyData || raw.clinicalData,
        trialIds: Array.isArray(raw.trialIds) ? raw.trialIds :
            raw.nctId ? [raw.nctId] : undefined,
        deal: raw.deal ? {
            partner: raw.deal.partner,
            value: raw.deal.value,
            upfront: raw.deal.upfront,
            milestones: raw.deal.milestones,
            date: raw.deal.date,
        } : undefined,
        confidence: normalizeConfidence(raw.confidence),
        sources: Array.isArray(raw.sources) ? raw.sources : [],
        verificationNotes: raw.verificationNotes,
    };
}
function normalizePhase(phase) {
    const p = phase.toLowerCase();
    if (p.includes('approved'))
        return 'Approved';
    if (p.includes('filed') || p.includes('bla') || p.includes('nda'))
        return 'Filed';
    if (p.includes('3'))
        return 'Phase 3';
    if (p.includes('2/3') || p.includes('2-3'))
        return 'Phase 2/3';
    if (p.includes('2'))
        return 'Phase 2';
    if (p.includes('1/2') || p.includes('1-2'))
        return 'Phase 1/2';
    if (p.includes('1'))
        return 'Phase 1';
    if (p.includes('preclin'))
        return 'Preclinical';
    return phase;
}
function normalizeConfidence(conf) {
    if (!conf)
        return 'MEDIUM';
    const c = conf.toUpperCase();
    if (c === 'HIGH')
        return 'HIGH';
    if (c === 'LOW')
        return 'LOW';
    return 'MEDIUM';
}
function isValidAsset(asset) {
    // Basic validation
    if (!asset.name || asset.name.length < 2)
        return false;
    if (asset.name.toLowerCase() === 'unknown')
        return false;
    // Exclude common non-specific drugs
    const excludedDrugs = [
        'pembrolizumab', 'nivolumab', 'atezolizumab', 'durvalumab', 'ipilimumab',
        'cisplatin', 'carboplatin', 'paclitaxel', 'docetaxel', 'gemcitabine',
        'prednisone', 'dexamethasone', 'methylprednisolone',
        'placebo', 'standard of care',
    ];
    const nameLower = asset.name.toLowerCase();
    for (const excluded of excludedDrugs) {
        if (nameLower.includes(excluded))
            return false;
    }
    return true;
}
function extractAssetsFromText(text, target) {
    // Fallback text extraction for when JSON parsing fails
    // This is a simplified implementation
    const assets = [];
    // Look for drug names with common patterns
    const patterns = [
        /([A-Z]{2,4}-?\d{3,6})/g, // Code names like ABC-123, DS-7300
        /([A-Za-z]+(?:mab|nib|tinib|ciclib|zumab|ximab))/g, // -mab, -nib suffixes
    ];
    for (const pattern of patterns) {
        const matches = text.matchAll(pattern);
        for (const match of matches) {
            const name = match[1];
            if (name.length >= 4 && !assets.some(a => a.name === name)) {
                assets.push({
                    name,
                    codeNames: [],
                    target,
                    modality: 'Unknown',
                    owner: 'Unknown',
                    phase: 'Unknown',
                    status: 'Active',
                    leadIndication: 'Unknown',
                    confidence: 'LOW',
                    sources: [],
                    verificationNotes: 'Extracted from unstructured text - requires verification',
                });
            }
        }
    }
    return assets;
}
function countSourcesFromResponse(response) {
    let count = 0;
    for (const block of response.content) {
        if (block.type === 'text') {
            // Count URLs in the response
            const urlMatches = block.text.match(/https?:\/\/[^\s)]+/g);
            if (urlMatches) {
                count += urlMatches.length;
            }
        }
    }
    return count;
}
// ============================================
// Convert to KnownAsset Format
// ============================================
/**
 * Convert discovered assets to KnownAsset format for report compatibility
 */
function convertToKnownAssets(discovered) {
    return discovered.map(d => {
        const regulatory = {
            btd: false,
            odd: false,
            fastTrack: false,
            prime: false,
        };
        const deal = d.deal ? {
            headline: d.deal.value,
            upfront: d.deal.upfront,
            milestones: d.deal.milestones,
            date: d.deal.date,
            partner: d.deal.partner,
            hasBreakdown: Boolean(d.deal.upfront || d.deal.milestones),
        } : undefined;
        return {
            primaryName: d.name,
            codeNames: d.codeNames,
            genericName: d.genericName,
            aliases: [...d.codeNames, d.name],
            target: d.target,
            modality: normalizeModality(d.modality),
            modalityDetail: d.mechanism,
            owner: d.owner,
            ownerType: normalizeOwnerType(d.ownerType),
            partner: d.partner,
            phase: d.phase,
            status: (d.status === 'Active' ? 'Active' : 'On Hold'),
            leadIndication: d.leadIndication,
            otherIndications: d.otherIndications,
            regulatory,
            deal,
            trialIds: d.trialIds || [],
            keyData: d.keyData,
            notes: d.verificationNotes,
            differentiator: `AI-discovered (${d.confidence} confidence)`,
        };
    });
}
function normalizeModality(modality) {
    const m = modality.toLowerCase();
    if (m.includes('adc') || m.includes('antibody drug conjugate'))
        return 'ADC';
    if (m.includes('bispecific') || m.includes('bi-specific'))
        return 'Bispecific';
    if (m.includes('car-t') || m.includes('car t'))
        return 'CAR-T';
    if (m.includes('bite'))
        return 'BiTE';
    if (m.includes('small molecule'))
        return 'Small Molecule';
    if (m.includes('radio'))
        return 'Radioconjugate';
    if (m.includes('vaccine'))
        return 'Vaccine';
    if (m.includes('mab') || m.includes('monoclonal'))
        return 'mAb';
    return 'Other';
}
function normalizeOwnerType(ownerType) {
    if (!ownerType)
        return 'Biotech';
    const o = ownerType.toLowerCase();
    if (o.includes('big pharma') || o.includes('large pharma'))
        return 'Big Pharma';
    if (o.includes('chinese'))
        return 'Chinese Biotech';
    if (o.includes('academic') || o.includes('university') || o.includes('institute'))
        return 'Academic';
    return 'Biotech';
}
//# sourceMappingURL=ai-research-agent.js.map