"use strict";
/**
 * Analyze Command
 *
 * Fetch the latest SEC filing and run AI analysis.
 *
 * Examples:
 *   helix analyze MRNA           # Analyze latest 10-K
 *   helix analyze MRNA -f 10-Q   # Analyze latest 10-Q
 *   helix analyze MRNA --debug   # Show prompt, raw response, then parsed output
 *   helix analyze MRNA --raw     # Just show raw filing text, no AI
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerAnalyzeCommand = registerAnalyzeCommand;
const chalk_1 = __importDefault(require("chalk"));
const ora_1 = __importDefault(require("ora"));
const sec_edgar_1 = require("../services/sec-edgar");
const companies_1 = require("../services/companies");
const llm_1 = require("../services/llm");
function registerAnalyzeCommand(program) {
    program
        .command('analyze <ticker>')
        .description('Analyze SEC filings using AI')
        .option('-f, --form <type>', 'Filing type: 10-K (annual) or 10-Q (quarterly)', '10-K')
        .option('--debug', 'Show prompt, raw LLM response, and parsed output', false)
        .option('--raw', 'Just show raw filing text (no AI analysis)', false)
        .option('--mock', 'Use mock data to test output formatting (no Ollama needed)', false)
        .action(async (ticker, options) => {
        const tickerUpper = ticker.toUpperCase();
        const spinner = (0, ora_1.default)(`Analyzing ${tickerUpper}...`).start();
        try {
            // Get company info
            spinner.text = `Looking up ${tickerUpper}...`;
            const company = await (0, companies_1.getCompanyByTicker)(tickerUpper);
            // Fetch filings
            spinner.text = `Fetching SEC filings for ${tickerUpper}...`;
            const filings = await (0, sec_edgar_1.getFilings)(tickerUpper, 10);
            if (filings.length === 0) {
                spinner.fail(`No filings found for ${tickerUpper}`);
                return;
            }
            // Find the requested filing type
            const targetForm = options.form.toUpperCase();
            const filing = filings.find(f => f.form === targetForm || f.form === `${targetForm}/A`);
            if (!filing) {
                spinner.fail(`No ${targetForm} filing found for ${tickerUpper}`);
                console.log(chalk_1.default.yellow('\nAvailable filings:'));
                for (const f of filings.slice(0, 5)) {
                    console.log(`  ${f.form} - ${f.filingDate}`);
                }
                return;
            }
            // Fetch filing content
            spinner.text = `Downloading ${filing.form} from ${filing.filingDate}...`;
            const content = await (0, sec_edgar_1.getFilingForAnalysis)(filing);
            spinner.stop();
            // --raw mode: just show the filing text and exit
            if (options.raw) {
                printRawFiling(tickerUpper, filing, content, 5000);
                return;
            }
            // --mock mode: use fake data to test output formatting
            if (options.mock) {
                spinner.stop();
                console.log(chalk_1.default.yellow('\n[MOCK MODE - Using sample data for output testing]\n'));
                const mockAnalysis = getMockAnalysis(tickerUpper);
                printAnalysis(tickerUpper, company?.name || tickerUpper, filing, mockAnalysis);
                return;
            }
            // --debug mode: show filing preview and prompt before analysis
            if (options.debug) {
                printDebugHeader(tickerUpper, filing);
                printFilingPreview(content, 3000);
                printPromptPreview(content, tickerUpper);
            }
            // Run AI analysis
            const llm = (0, llm_1.getLLMProvider)();
            const analyzeSpinner = (0, ora_1.default)(`Analyzing with ${llm.name}... (this may take a minute)`).start();
            const analysis = await llm.analyze(content, tickerUpper);
            analyzeSpinner.stop();
            // --debug mode: show raw LLM response
            if (options.debug) {
                printRawResponse(analysis.rawResponse || 'No raw response captured');
            }
            // Post-process to fix common LLM issues
            const cleanedAnalysis = postProcessAnalysis(analysis, filing);
            // Display parsed results
            printAnalysis(tickerUpper, company?.name || tickerUpper, filing, cleanedAnalysis);
        }
        catch (error) {
            spinner.fail('Analysis failed');
            console.error(chalk_1.default.red(error instanceof Error ? error.message : 'Unknown error'));
            process.exit(1);
        }
    });
}
// ============================================
// Debug/Raw mode printing functions
// ============================================
/**
 * Print raw filing text (for --raw mode)
 */
function printRawFiling(ticker, filing, content, maxChars) {
    console.log('');
    console.log(chalk_1.default.bold.cyan(`═══ RAW FILING: ${ticker} ${filing.form} ═══`));
    console.log(chalk_1.default.gray(`Filed: ${filing.filingDate} | Period: ${filing.reportDate}`));
    console.log(chalk_1.default.gray(`Total length: ${content.length.toLocaleString()} characters`));
    console.log(chalk_1.default.gray('─'.repeat(60)));
    console.log('');
    console.log(content.substring(0, maxChars));
    if (content.length > maxChars) {
        console.log('');
        console.log(chalk_1.default.yellow(`... truncated (showing first ${maxChars.toLocaleString()} of ${content.length.toLocaleString()} chars)`));
    }
    console.log('');
}
/**
 * Print debug header
 */
function printDebugHeader(ticker, filing) {
    console.log('');
    console.log(chalk_1.default.bgYellow.black(' DEBUG MODE '));
    console.log(chalk_1.default.gray(`Analyzing ${ticker} ${filing.form} from ${filing.filingDate}`));
    console.log('');
}
/**
 * Print filing preview (for --debug mode)
 */
function printFilingPreview(content, maxChars) {
    console.log(chalk_1.default.bold.yellow('═══ FILING TEXT PREVIEW ═══'));
    console.log(chalk_1.default.gray(`Total: ${content.length.toLocaleString()} chars | Showing first ${maxChars.toLocaleString()}`));
    console.log(chalk_1.default.gray('─'.repeat(60)));
    console.log(content.substring(0, maxChars));
    console.log(chalk_1.default.gray('─'.repeat(60)));
    console.log('');
}
/**
 * Print the prompt being sent to LLM (for --debug mode)
 */
function printPromptPreview(content, ticker) {
    const prompt = (0, llm_1.buildAnalysisPrompt)(content.substring(0, 2000) + '...', ticker);
    console.log(chalk_1.default.bold.yellow('═══ LLM PROMPT (truncated) ═══'));
    console.log(chalk_1.default.gray('─'.repeat(60)));
    // Show prompt structure without full filing content
    const promptLines = prompt.split('\n');
    for (let i = 0; i < Math.min(promptLines.length, 50); i++) {
        console.log(chalk_1.default.gray(promptLines[i]));
    }
    if (promptLines.length > 50) {
        console.log(chalk_1.default.yellow(`... (${promptLines.length - 50} more lines)`));
    }
    console.log(chalk_1.default.gray('─'.repeat(60)));
    console.log('');
}
/**
 * Print raw LLM response (for --debug mode)
 */
function printRawResponse(response) {
    console.log(chalk_1.default.bold.yellow('═══ RAW LLM RESPONSE ═══'));
    console.log(chalk_1.default.gray('─'.repeat(60)));
    console.log(chalk_1.default.white(response));
    console.log(chalk_1.default.gray('─'.repeat(60)));
    console.log('');
}
// ============================================
// Post-processing to fix common LLM issues
// ============================================
/**
 * Clean up LLM analysis output
 * - Deduplicate pipeline entries
 * - Flag uncertain/outdated data
 */
function postProcessAnalysis(analysis, filing) {
    // Deep clone to avoid mutating original
    const cleaned = JSON.parse(JSON.stringify(analysis));
    // 1. Deduplicate pipeline by drug name, keeping most complete entry
    cleaned.pipeline = deduplicatePipeline(cleaned.pipeline);
    // 2. Validate and flag financial data
    cleaned.financials = validateFinancials(cleaned.financials, filing);
    return cleaned;
}
/**
 * Deduplicate pipeline entries by drug name
 * Keeps the entry with the most fields filled in
 */
function deduplicatePipeline(pipeline) {
    const drugMap = new Map();
    for (const item of pipeline) {
        const drugKey = item.drug.toLowerCase().trim();
        const existing = drugMap.get(drugKey);
        if (!existing) {
            drugMap.set(drugKey, item);
        }
        else {
            // Score each entry by completeness
            const existingScore = scoreEntry(existing);
            const newScore = scoreEntry(item);
            // Keep the more complete entry, or the one with higher phase
            if (newScore > existingScore ||
                (newScore === existingScore && getPhaseRank(item.phase) > getPhaseRank(existing.phase))) {
                drugMap.set(drugKey, item);
            }
        }
    }
    return Array.from(drugMap.values());
}
/**
 * Score a pipeline entry by completeness (more filled fields = higher score)
 */
function scoreEntry(item) {
    let score = 0;
    if (item.drug)
        score += 1;
    if (item.phase)
        score += 1;
    if (item.indication)
        score += 1;
    if (item.status)
        score += 2; // Status is more valuable
    if (item.catalyst)
        score += 2; // Catalyst is more valuable
    return score;
}
/**
 * Rank phases for comparison (higher = more advanced)
 */
function getPhaseRank(phase) {
    const p = phase.toLowerCase();
    if (p.includes('approved') || p.includes('marketed'))
        return 100;
    if (p.includes('bla') || p.includes('nda'))
        return 90;
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
    if (p.includes('preclinical') || p.includes('pre-clinical'))
        return 10;
    return 0;
}
/**
 * Validate financial data and flag potential issues
 */
function validateFinancials(financials, filing) {
    const validated = { ...financials };
    const warnings = [];
    // Get the filing year
    const filingYear = new Date(filing.filingDate).getFullYear();
    // Check if cash date is outdated (more than 1 year before filing)
    if (validated.cashDate) {
        const yearMatch = validated.cashDate.match(/20\d{2}/);
        if (yearMatch) {
            const cashYear = parseInt(yearMatch[0]);
            if (filingYear - cashYear > 1) {
                warnings.push(`Cash date (${cashYear}) may be outdated for ${filingYear} filing`);
            }
        }
    }
    // Check for unrealistic runway
    if (validated.runwayMonths !== null) {
        if (validated.runwayMonths > 120) {
            warnings.push('Runway >10 years seems unrealistic');
        }
        else if (validated.runwayMonths < 0) {
            warnings.push('Negative runway detected');
            validated.runwayMonths = null;
        }
    }
    // Check for suspiciously round numbers that might be hallucinated
    if (validated.cash) {
        const cashMatch = validated.cash.match(/\$?([\d.]+)\s*(B|M|billion|million)?/i);
        if (cashMatch) {
            const num = parseFloat(cashMatch[1]);
            // Exact round numbers like $2.0B often indicate hallucination
            if (num === Math.floor(num) && num > 0) {
                warnings.push('Financial figures may need verification');
            }
        }
    }
    if (warnings.length > 0) {
        validated.dataWarning = warnings.join('; ');
    }
    return validated;
}
// ============================================
// Pretty analysis output
// ============================================
function printAnalysis(ticker, companyName, filing, analysis) {
    console.log('');
    // Header with source info
    console.log(chalk_1.default.bold.cyan('╔' + '═'.repeat(58) + '╗'));
    console.log(chalk_1.default.bold.cyan('║') + chalk_1.default.bold.white(` ${companyName}`.padEnd(58)) + chalk_1.default.bold.cyan('║'));
    console.log(chalk_1.default.bold.cyan('║') + chalk_1.default.gray(` ${ticker} | ${filing.form} | Period: ${filing.reportDate}`.padEnd(58)) + chalk_1.default.bold.cyan('║'));
    console.log(chalk_1.default.bold.cyan('╚' + '═'.repeat(58) + '╝'));
    // Source info
    console.log(chalk_1.default.gray(`  Source: ${filing.form} filed ${filing.filingDate}`));
    console.log(chalk_1.default.gray(`  Link: ${filing.fileUrl}`));
    console.log('');
    // Analyst Summary (top of report)
    if (analysis.analystSummary) {
        console.log(chalk_1.default.bold.white('ANALYST SUMMARY'));
        console.log(chalk_1.default.gray('─'.repeat(50)));
        console.log(wrapText(analysis.analystSummary, 70));
        console.log('');
    }
    // Financials with runway indicator
    printFinancials(analysis);
    // Pipeline as table
    if (analysis.pipeline.length > 0) {
        printPipeline(analysis.pipeline);
    }
    // FDA Interactions
    if (analysis.fdaInteractions.length > 0) {
        console.log(chalk_1.default.bold.white('FDA INTERACTIONS'));
        console.log(chalk_1.default.gray('─'.repeat(50)));
        for (const item of analysis.fdaInteractions) {
            console.log(chalk_1.default.magenta(`  ▸ ${item}`));
        }
        console.log('');
    }
    // Partnerships
    if (analysis.partnerships.length > 0) {
        printPartnerships(analysis.partnerships);
    }
    // Key Risks
    if (analysis.risks.length > 0) {
        console.log(chalk_1.default.bold.white('KEY RISKS'));
        console.log(chalk_1.default.gray('─'.repeat(50)));
        for (const risk of analysis.risks) {
            console.log(chalk_1.default.red(`  ⚠ ${wrapText(risk, 65)}`));
        }
        console.log('');
    }
    // Recent Events
    if (analysis.recentEvents.length > 0) {
        console.log(chalk_1.default.bold.white('RECENT EVENTS'));
        console.log(chalk_1.default.gray('─'.repeat(50)));
        for (const event of analysis.recentEvents) {
            console.log(chalk_1.default.blue(`  • ${wrapText(event, 65)}`));
        }
        console.log('');
    }
    // Footer
    console.log(chalk_1.default.gray('═'.repeat(60)));
}
/**
 * Print financials section with runway indicator
 */
function printFinancials(analysis) {
    const fin = analysis.financials;
    console.log(chalk_1.default.bold.white('FINANCIALS'));
    console.log(chalk_1.default.gray('─'.repeat(50)));
    // Show data warning if present
    if (fin.dataWarning) {
        console.log(chalk_1.default.yellow(`  ⚠️  ${fin.dataWarning}`));
        console.log('');
    }
    // Cash position
    if (fin.cash) {
        console.log(`  Cash:         ${chalk_1.default.green.bold(fin.cash)}${fin.cashDate ? chalk_1.default.gray(` (as of ${fin.cashDate})`) : ''}`);
    }
    // Burn rate
    if (fin.quarterlyBurnRate) {
        console.log(`  Burn Rate:    ${chalk_1.default.yellow(fin.quarterlyBurnRate)} /quarter`);
    }
    // Runway with visual indicator
    if (fin.runwayMonths !== null) {
        const runway = fin.runwayMonths;
        let runwayDisplay;
        if (runway >= 24) {
            // Green: good runway (>24 months)
            runwayDisplay = `🟢 ${chalk_1.default.green.bold(`${runway} months`)}`;
        }
        else if (runway >= 12) {
            // Yellow: moderate runway (12-24 months)
            runwayDisplay = `🟡 ${chalk_1.default.yellow.bold(`${runway} months`)}`;
        }
        else {
            // Red: short runway (<12 months)
            runwayDisplay = `🔴 ${chalk_1.default.red.bold(`${runway} months`)}`;
        }
        console.log(`  Runway:       ${runwayDisplay}`);
    }
    // Revenue
    if (fin.revenue) {
        console.log(`  Revenue:      ${chalk_1.default.cyan(fin.revenue)}${fin.revenueSource ? chalk_1.default.gray(` (${fin.revenueSource})`) : ''}`);
    }
    console.log('');
}
/**
 * Print pipeline as a formatted table
 */
function printPipeline(pipeline) {
    console.log(chalk_1.default.bold.white('PIPELINE'));
    console.log(chalk_1.default.gray('─'.repeat(50)));
    // Table header
    console.log(chalk_1.default.gray('  Phase        Drug                    Indication'));
    console.log(chalk_1.default.gray('  ' + '─'.repeat(48)));
    for (const item of pipeline) {
        const phaseColor = getPhaseColor(item.phase);
        const phaseStr = phaseColor(item.phase.padEnd(12));
        const drugStr = item.drug.substring(0, 22).padEnd(22);
        const indicationStr = item.indication.substring(0, 25);
        console.log(`  ${phaseStr} ${chalk_1.default.white.bold(drugStr)}  ${chalk_1.default.gray(indicationStr)}`);
        // Show status and catalyst on next line if available
        const details = [];
        if (item.status)
            details.push(item.status);
        if (item.catalyst)
            details.push(chalk_1.default.yellow(`Next: ${item.catalyst}`));
        if (details.length > 0) {
            console.log(chalk_1.default.gray(`               ${details.join(' | ')}`));
        }
    }
    console.log('');
}
/**
 * Print partnerships section
 */
function printPartnerships(partnerships) {
    console.log(chalk_1.default.bold.white('PARTNERSHIPS'));
    console.log(chalk_1.default.gray('─'.repeat(50)));
    for (const p of partnerships) {
        console.log(`  ${chalk_1.default.cyan.bold(p.partner)} ${chalk_1.default.gray(`(${p.type})`)}`);
        if (p.value) {
            console.log(`    Value: ${chalk_1.default.green(p.value)}`);
        }
        if (p.details) {
            console.log(chalk_1.default.gray(`    ${wrapText(p.details, 50)}`));
        }
    }
    console.log('');
}
/**
 * Get color for pipeline phase
 * Approved = green, Phase 3 = cyan, Phase 2 = blue, Phase 1 = magenta, etc.
 */
function getPhaseColor(phase) {
    const phaseLower = phase.toLowerCase();
    if (phaseLower.includes('approved') || phaseLower.includes('marketed')) {
        return (t) => chalk_1.default.green.bold(t);
    }
    if (phaseLower.includes('nda') || phaseLower.includes('bla') || phaseLower.includes('filed')) {
        return (t) => chalk_1.default.green(t);
    }
    if (phaseLower.includes('3')) {
        return (t) => chalk_1.default.cyan.bold(t);
    }
    if (phaseLower.includes('2')) {
        return (t) => chalk_1.default.blue(t);
    }
    if (phaseLower.includes('1')) {
        return (t) => chalk_1.default.magenta(t);
    }
    if (phaseLower.includes('preclinical') || phaseLower.includes('pre-clinical')) {
        return (t) => chalk_1.default.gray(t);
    }
    return (t) => chalk_1.default.white(t);
}
/**
 * Wrap text to specified width
 */
function wrapText(text, width) {
    if (!text)
        return '';
    const words = text.split(' ');
    const lines = [];
    let currentLine = '';
    for (const word of words) {
        if ((currentLine + ' ' + word).length > width) {
            lines.push(currentLine);
            currentLine = word;
        }
        else {
            currentLine = currentLine ? currentLine + ' ' + word : word;
        }
    }
    if (currentLine)
        lines.push(currentLine);
    return lines.join('\n    '); // Indent continuation lines
}
// ============================================
// Mock data for testing output formatting
// ============================================
/**
 * Generate realistic mock analysis data for testing output
 */
function getMockAnalysis(ticker) {
    return {
        company: {
            name: `${ticker} Inc.`,
            ticker: ticker,
            marketCap: '$18.5B',
            employees: 5200
        },
        analystSummary: `${ticker} is a clinical-stage biotechnology company focused on developing novel mRNA therapeutics for infectious diseases and oncology. The company has a diversified pipeline with lead assets in Phase 3 trials. Strong cash position provides runway through 2026, though burn rate has increased due to expanded clinical programs. Key catalyst: Phase 3 data readout expected Q2 2025.`,
        financials: {
            cash: '$4.2B',
            cashDate: 'Dec 31, 2024',
            quarterlyBurnRate: '$380M',
            runwayMonths: 28,
            revenue: '$1.8B',
            revenueSource: 'Product sales (COVID-19 vaccine)'
        },
        pipeline: [
            {
                drug: 'mRNA-1283',
                indication: 'COVID-19 (next-gen)',
                phase: 'Phase 3',
                status: 'Enrollment complete',
                catalyst: 'Data Q2 2025'
            },
            {
                drug: 'mRNA-1345',
                indication: 'RSV Vaccine',
                phase: 'Approved',
                status: 'FDA approved May 2024',
                catalyst: 'EU approval pending'
            },
            {
                drug: 'mRNA-4157',
                indication: 'Melanoma (adjuvant)',
                phase: 'Phase 3',
                status: 'Partnered with Merck',
                catalyst: 'Pivotal data H2 2025'
            },
            {
                drug: 'mRNA-1893',
                indication: 'Zika Vaccine',
                phase: 'Phase 2',
                status: 'Dose optimization',
                catalyst: 'Phase 3 initiation 2025'
            },
            {
                drug: 'mRNA-3927',
                indication: 'Propionic Acidemia',
                phase: 'Phase 1/2',
                status: 'Rare disease orphan drug',
                catalyst: 'Interim data Q3 2025'
            }
        ],
        fdaInteractions: [
            'Breakthrough Therapy designation granted for mRNA-4157 in melanoma',
            'Fast Track designation for mRNA-3927 in propionic acidemia',
            'Pre-BLA meeting completed for next-gen COVID vaccine'
        ],
        partnerships: [
            {
                partner: 'Merck',
                type: 'Development',
                value: 'Up to $950M + royalties',
                details: 'Collaboration on personalized cancer vaccines using mRNA-4157'
            },
            {
                partner: 'Vertex',
                type: 'Research',
                value: '$75M upfront',
                details: 'Cystic fibrosis mRNA therapeutics development'
            },
            {
                partner: 'BARDA',
                type: 'Government',
                value: '$1.3B contract',
                details: 'Pandemic preparedness and vaccine stockpile'
            }
        ],
        risks: [
            'Revenue concentration: 85% from COVID-19 vaccine which faces declining demand',
            'Competition: Multiple mRNA competitors advancing similar programs',
            'Manufacturing capacity constraints may delay commercial scale-up',
            'Patent litigation ongoing with CureVac and Arbutus',
            'Regulatory uncertainty around annual vaccine reformulation requirements'
        ],
        recentEvents: [
            'Q4 2024 revenue beat estimates by 12%, driven by updated COVID booster',
            'Announced $3B share repurchase program in January 2025',
            'Expanded manufacturing facility in Melbourne, Australia',
            'Phase 2 flu/COVID combo vaccine showed positive immunogenicity data',
            'CEO highlighted plans for 10+ Phase 3 programs by 2026'
        ]
    };
}
//# sourceMappingURL=analyze.js.map