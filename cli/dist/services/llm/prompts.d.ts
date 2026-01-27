/**
 * LLM Prompts for Biotech Analysis
 *
 * This file contains the prompts sent to the AI for analyzing SEC filings.
 * Edit this file to tune the analysis output.
 *
 * Tips for prompt tuning:
 * - Be specific about the JSON structure you want
 * - Add examples if the LLM isn't following instructions
 * - Use "Rules" section to constrain behavior
 * - Test with --debug flag to see raw responses
 */
/**
 * Main analysis prompt for SEC filings
 *
 * This prompt is designed for biotech companies and extracts:
 * - Pipeline drugs and their phases
 * - Financial health (cash, burn rate, runway)
 * - FDA interactions (approvals, designations)
 * - Partnerships and deals
 * - Key risks
 * - Recent material events
 */
export declare const BIOTECH_ANALYSIS_PROMPT = "You are a senior biotech equity analyst. Analyze this SEC filing and extract key investment-relevant information.\n\nReturn a JSON object with this exact structure:\n\n{\n  \"company\": {\n    \"name\": \"string\",\n    \"ticker\": \"string\",\n    \"marketCap\": \"string or null if not found\",\n    \"employees\": \"number or null\"\n  },\n  \"pipeline\": [\n    {\n      \"drug\": \"drug name/code\",\n      \"phase\": \"Preclinical | Phase 1 | Phase 2 | Phase 3 | NDA/BLA Filed | Approved\",\n      \"indication\": \"what it treats\",\n      \"status\": \"brief status update\",\n      \"catalyst\": \"next expected event if mentioned\"\n    }\n  ],\n  \"financials\": {\n    \"cash\": \"Look for 'Cash, cash equivalents and marketable securities' or similar - extract the dollar amount (e.g., '$4.2 billion')\",\n    \"cashDate\": \"The 'as of' date for the cash position (e.g., 'December 31, 2024')\",\n    \"quarterlyBurnRate\": \"Calculate from operating expenses or cash used in operations\",\n    \"runwayMonths\": \"Calculate: cash divided by quarterly burn rate, as number of months\",\n    \"revenue\": \"Total revenue or net product sales for the period\",\n    \"revenueSource\": \"product sales, collaborations, grants, etc\"\n  },\n  \"fdaInteractions\": [\n    \"List any: approvals, CRLs, breakthrough designations, fast track, orphan drug, PDUFA dates\"\n  ],\n  \"partnerships\": [\n    {\n      \"partner\": \"company name\",\n      \"type\": \"licensing, collaboration, acquisition, etc\",\n      \"value\": \"deal value if mentioned\",\n      \"details\": \"brief description\"\n    }\n  ],\n  \"risks\": [\n    \"Top 3-5 key risks from Risk Factors section, biotech-specific\"\n  ],\n  \"recentEvents\": [\n    \"Key events from the reporting period - trial results, approvals, executive changes\"\n  ],\n  \"analystSummary\": \"2-3 sentence summary of the investment thesis and key considerations\"\n}\n\nRules:\n- Only include information explicitly stated in the filing\n- Use null for fields where information is not available\n- For pipeline, focus on lead programs (max 10 drugs)\n- For risks, prioritize clinical, regulatory, and financial risks\n- Be concise but specific\n- Return ONLY the JSON object, no other text\n\nIMPORTANT for financials:\n- Search for tables with \"Cash, cash equivalents\" or \"Liquidity\"\n- Look for specific dollar amounts like \"$X billion\" or \"$X million\"\n- Check the balance sheet or liquidity discussion sections\n- If you find cash position, always include the as-of date";
/**
 * Build the full prompt with filing content
 *
 * @param filingContent - The extracted text from the SEC filing
 * @param ticker - The company's stock ticker
 * @returns Complete prompt ready to send to LLM
 */
export declare function buildAnalysisPrompt(filingContent: string, ticker: string): string;
//# sourceMappingURL=prompts.d.ts.map