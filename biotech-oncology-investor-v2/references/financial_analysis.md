# Financial & SEC Filing Analysis Framework

## Table of Contents
1. [Cash Position & Runway](#cash-runway)
2. [Revenue Analysis](#revenue)
3. [Partnership Economics](#partnerships)
4. [Peer Comparison](#peer-comparison)
5. [Capital Markets](#capital-markets)
6. [SEC Filing Guide](#sec-filings)

---

## Cash Position & Runway

The most immediately actionable financial question for clinical-stage biotechs: how long can they operate before needing more money?

### Runway Calculation
```
Quarterly burn rate = (Cash at start of quarter - Cash at end of quarter)
                      adjusted for one-time items (milestone receipts, equity raises, etc.)

Runway (quarters) = Current cash & equivalents / Adjusted quarterly burn rate
```

Use the average of the last 2-3 quarters for a smoothed burn rate, but flag any trend (accelerating or decelerating burn).

### What "Good" Looks Like
- **>24 months runway**: Comfortable. Company has time to reach key catalysts.
- **12-24 months**: Adequate but watch closely. Company may need to raise within the year.
- **<12 months**: Red flag. Company is likely planning a raise, which means dilution. Or worse — they may need to cut programs.

### Key Cash Items to Track
- **Cash, cash equivalents, and short-term investments**: The total liquidity available
- **Restricted cash**: Money that's locked up and not available for operations
- **Debt obligations**: Any term loans, convertible notes, or credit facilities that require repayment
- **Upcoming milestone receipts**: Cash the company expects to receive from partners (but hasn't yet)
- **Operating lease obligations**: Can be significant for companies with manufacturing facilities

### Burn Rate Components
- **R&D expense**: The biggest line item. Break down by program if disclosed.
- **G&A expense**: Administrative overhead. Watch for excessive G&A relative to R&D.
- **Capital expenditures**: Manufacturing buildouts, lab equipment. Can spike around commercial launch.
- **Working capital changes**: Sometimes significant. Prepaid clinical trial costs, for example.

---

## Revenue Analysis

### Product Revenue (for commercial-stage companies)
- **Quarterly revenue trajectory**: Growing, stable, or declining? What's the quarter-over-quarter and year-over-year growth rate?
- **Revenue by indication**: If the drug is approved for multiple indications, where is the growth coming from?
- **Revenue by geography**: US vs ex-US. Different pricing dynamics, different competitive landscapes.
- **Gross-to-net adjustments**: The gap between gross revenue (list price x units) and net revenue (what the company actually collects). Government rebates (Medicaid, 340B), commercial discounts, patient assistance programs. Gross-to-net > 50% is common and growing.
- **Inventory channel**: Are revenues being stocked (sell-in) or actually used (sell-through)? Inventory build at launch can inflate early revenues.

### Collaboration Revenue
- **Milestone payments**: One-time payments upon achieving clinical or regulatory milestones. These are lumpy and non-recurring — don't extrapolate them.
- **Cost-sharing / reimbursement**: If a partner is sharing development costs, this shows up as collaboration revenue. It's real cash but also non-recurring.
- **Royalty revenue**: Percentage of partner's net sales. This is the most valuable collaboration revenue — recurring and scales with sales.
- **License fees**: Upfront payments received when a deal is signed. One-time.

### Revenue Quality Assessment
Not all revenue is equal. Rank by quality:
1. Product revenue (recurring, driven by patient demand)
2. Royalty revenue (recurring, driven by partner's commercial execution)
3. Milestone payments (one-time, contingent on development progress)
4. Cost reimbursement (one-time, reduces as programs advance)
5. License fees (one-time, non-recurring)

---

## Partnership Economics

### Deal Value Assessment
Headline deal values are misleading. Dissect the actual economics:

- **Upfront payment**: Cash received at signing. The only guaranteed component.
- **Near-term milestones**: Milestones achievable within 1-2 years with high probability. Somewhat reliable.
- **Long-term milestones**: Regulatory and commercial milestones years away. Heavily discounted.
- **Total biobucks**: The headline number. Sum of all possible payments. Almost never fully achieved. Apply a probability-weighted discount.

### Royalty Economics
- **Royalty rate**: Low single digits (1-5%) for early-stage out-licensing, low-to-mid teens (10-15%) for late-stage. Double-digit royalties are significant economic burden on the commercializing partner.
- **Royalty stacking**: If the product requires licenses from multiple IP holders, total royalty burden can become unsustainable (>25% of net sales is a warning sign).
- **Royalty buydown provisions**: Some deals allow the licensee to reduce royalties by making additional payments or upon generic entry.
- **Net sales definition**: What deductions are allowed before royalties are calculated? Broadly defined deductions reduce the royalty base.

### Opt-In / Co-Commercialization Rights
- **50/50 US co-commercialize**: Company shares profits but also shares costs. Increases potential upside but requires building a commercial infrastructure.
- **Tiered profit-sharing**: e.g., 50/50 up to $1B net sales, 35/65 above $1B. Understand the breakpoints.
- **Opt-in triggers**: When must the company decide whether to co-invest? What information will be available at that point?

### Red Flags in Partnerships
- Partner reduces development investment (slows enrollment, delays milestones)
- Partner restructures and deprioritizes the program
- Dispute over milestones or royalty calculations (check 10-K risk factors)
- Company is overly dependent on one partner for majority of pipeline value

---

## Peer Comparison

### Clinical-Stage Peer Metrics
- **Market capitalization**: Relative size
- **Enterprise value**: Market cap + debt - cash. Better comparison for companies with different capital structures.
- **EV / pipeline value**: Subjective but useful. Compare EV to number and quality of pipeline assets.
- **Cash per share**: How much of the stock price is backed by cash on the balance sheet. If stock trades near cash value, market is assigning minimal value to the pipeline.

### Commercial-Stage Peer Metrics
- **EV / Revenue (NTM)**: Forward revenue multiple. Compare to peers in similar therapeutic areas.
- **EV / Peak revenue estimate**: Forward multiple based on consensus peak revenue estimates.
- **Price / Earnings**: For profitable companies. Rare in biotech until late commercial stage.

### Comparable Transaction Analysis
When evaluating M&A potential or partnership value:
- What premiums have been paid for similar assets? (Typical biotech M&A premiums: 50-100%+ to 30-day VWAP)
- What were the deal terms for similar licensing arrangements?
- What stage was the asset at the time of the deal?

---

## Capital Markets

### Dilution Risk Assessment
- **ATM (at-the-market) programs**: Company files a shelf registration and sells shares gradually at market prices. Check for active ATM programs in SEC filings (prospectus supplements).
- **Secondary offerings**: Larger, more dilutive. Often done at a discount to market. Watch for shelf registrations (S-3 filings).
- **Convertible notes**: Debt that converts to equity at a predetermined price. Creates potential dilution at the conversion price. Check conversion terms.
- **Warrants**: Common in small-cap biotech financing. Check exercise prices and expiration dates.

### Dilution Calculation
```
Fully diluted share count = Basic shares outstanding
                          + In-the-money options (treasury stock method)
                          + Unvested RSUs
                          + Convertible note shares (if converted)
                          + Warrant shares (if exercised)
```

### Insider Activity
- **Form 4 filings**: Track insider buying and selling. Insider buying is a stronger signal than insider selling (insiders sell for many reasons, but they buy for one reason).
- **10b5-1 plans**: Pre-planned selling programs. Less informative than discretionary trades.
- **Institutional ownership changes**: 13F filings show quarterly institutional holdings. Track specialist healthcare funds.

---

## SEC Filing Guide

### 10-K (Annual Report)
The most comprehensive document. Key sections to analyze:

- **Business section (Item 1)**: Pipeline overview, competitive landscape, manufacturing, IP discussion. Often the most detailed public description of the company's programs.
- **Risk Factors (Item 1A)**: Required disclosure of material risks. Look for NEW risk factors added vs. prior year — these signal emerging concerns.
- **MD&A (Item 7)**: Management's discussion of financial results. Look for explanations of revenue trends, R&D spending by program, and forward-looking guidance.
- **Financial Statements (Item 8)**: Balance sheet, income statement, cash flow statement. Check footnotes for: collaboration agreement details (ASC 606 revenue recognition), stock-based compensation breakdown, lease obligations, and contingent liabilities.
- **Notes to Financial Statements**: Often contain the most useful information. Revenue disaggregation by product/geography, detailed terms of collaboration agreements, and contingent milestone payments.

### 10-Q (Quarterly Report)
Similar to 10-K but less detailed. Focus on:
- Updated cash position and burn rate
- New risk factors or changes to existing ones
- Revenue trends
- Material developments in MD&A

### 8-K (Current Events)
Filed within 4 business days of material events:
- Partnership announcements (with deal terms)
- Clinical trial results
- Leadership changes
- Financial results (preliminary)
- Material agreements (attached as exhibits)

**Tip:** The actual agreements are often filed as exhibits to 8-Ks. These contain the detailed deal terms (milestones, royalties, territory rights) that aren't in the press release.

### S-1 / S-3 (Registration Statements)
- **S-1**: Initial registration (IPO or first public filing). Contains the most detailed company description and use of proceeds.
- **S-3**: Shelf registration for seasoned issuers. Signals intent to raise capital. Watch for prospectus supplements (424B filings) that indicate actual sales.

### Proxy Statement (DEF 14A)
- Executive compensation — is management aligned with shareholders?
- Board composition and expertise
- Related party transactions
- Shareholder proposals

### Key Filing Dates to Track
- 10-K: Within 60 days of fiscal year end (large accelerated filer)
- 10-Q: Within 40 days of quarter end
- 8-K: Within 4 business days of material event
- Proxy: At least 40 days before annual meeting
