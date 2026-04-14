# Patent & IP Deep Dive Framework

## Table of Contents
1. [Patent Types in Biopharma](#patent-types)
2. [Orange Book & Regulatory Exclusivity](#orange-book)
3. [Patent Term Adjustments & Extensions](#term-extensions)
4. [PTAB & IPR Proceedings](#ptab)
5. [Freedom-to-Operate Analysis](#fto)
6. [Biosimilar & Generic Entry](#biosimilar-generic)
7. [Patent Cliff Analysis](#patent-cliff)
8. [Licensing & IP Ownership](#licensing)

---

## Patent Types in Biopharma

### Composition of Matter (COM) Patents
The strongest form of patent protection. Covers the drug molecule itself, regardless of how it's used. A COM patent on a small molecule covers the chemical structure; on a biologic, it covers the amino acid sequence.

**Investment relevance:** COM patents provide the broadest protection. Expiry of COM patents is the most critical date for generic/biosimilar entry. If a company only has method-of-use patents (no COM), the IP position is weaker.

### Method of Use Patents
Cover specific therapeutic applications (e.g., "use of compound X for treating HER2+ breast cancer"). Narrower than COM patents — a generic company can potentially market the drug for a different indication.

**Investment relevance:** Method-of-use patents can extend commercial life after COM expiry through "skinny labels" for generics, but enforcement is difficult. The value depends on whether the patented indication is the primary revenue driver.

### Formulation Patents
Cover specific drug formulations (e.g., extended-release tablets, lyophilized formulations, specific excipient combinations). These can block generic competition if the formulation is necessary for the drug's performance.

### Process Patents
Cover manufacturing methods. Weakest protection — a competitor can often design around a process patent. But in biologics, where the process IS the product, process patents carry more weight.

### Combination Patents
Cover specific drug combinations. Increasingly important as oncology moves toward combination regimens.

---

## Orange Book & Regulatory Exclusivity

### Orange Book Listings (US)
The FDA's Orange Book (Approved Drug Products with Therapeutic Equivalence Evaluations) lists patents associated with approved drugs. Only certain patent types can be listed:

- Drug substance (active ingredient) patents
- Drug product (formulation) patents
- Method of use patents

NOT listable: process patents, metabolite patents, packaging patents.

**How to check:** Search the Orange Book at FDA.gov. Each NDA will list associated patents with expiry dates. For biologics (BLAs), patent listings work differently — see the Purple Book.

### Paragraph IV Challenges
When a generic company files an ANDA, it must certify its position on each Orange Book patent:
- **Para I**: No patent listed
- **Para II**: Patent has expired
- **Para III**: Will wait for patent expiry
- **Para IV**: Patent is invalid or won't be infringed

A Para IV certification triggers a 45-day clock for the patent holder to sue. If sued, the FDA imposes a 30-month stay on generic approval.

**Investment relevance:** A Para IV filing is an early warning of generic competition. Track ANDA filings via FDA databases. The 30-month stay provides a defined timeline for IP resolution.

### Regulatory Exclusivity (Independent of Patents)

- **NCE Exclusivity (5 years)**: New chemical entity. Blocks all ANDA filings for 5 years.
- **New Clinical Investigation Exclusivity (3 years)**: For new indications, new dosage forms. Blocks ANDAs relying on the new data.
- **Orphan Drug Exclusivity (7 years US / 10 years EU)**: For drugs treating rare diseases (<200K patients in US). Blocks approval of same drug for same indication.
- **Pediatric Exclusivity (+6 months)**: Added to existing patents/exclusivities for completing pediatric studies.
- **Biologic Exclusivity (12 years US / 8+2 years EU)**: Reference product exclusivity for biologics under BPCIA. Biosimilar applicants can't reference the innovator's data during this period.

---

## Patent Term Adjustments & Extensions

### Patent Term Adjustment (PTA) — US
Compensates for USPTO delays in examining the patent application. Can add months or years to the patent term. Check the issued patent for PTA.

### Patent Term Extension (PTE) — US
Under Hatch-Waxman, one patent per product can be extended to compensate for time lost during FDA review. Maximum extension = 5 years. Total patent life post-approval cannot exceed 14 years.

**Calculation:** PTE = half of IND-to-NDA testing phase + full NDA review phase, capped at 5 years.

### Supplementary Protection Certificate (SPC) — EU
Similar to PTE but for European markets. Extends protection by up to 5 years (+ 6 months if pediatric). One SPC per product per country.

**Investment relevance:** PTE/SPC can significantly extend effective patent life. Always calculate the post-PTE expiry date, not just the base patent expiry.

---

## PTAB & IPR Proceedings

### Inter Partes Review (IPR)
A third party can challenge patent validity at the Patent Trial and Appeal Board (PTAB) based on prior art (patents and publications only). Faster and cheaper than district court litigation.

**Key statistics:** Historically, PTAB has invalidated claims at a high rate (~60-70% of claims that reach final written decision). This has made IPR a powerful tool for generic/biosimilar companies.

### Post-Grant Review (PGR)
Similar to IPR but must be filed within 9 months of patent grant. Can challenge on any ground (not just prior art).

**Investment relevance:**
- Track whether key patents have faced or are facing IPR/PGR challenges
- Check PTAB decisions and their impact on the patent landscape
- A patent that survives IPR challenge is stronger than one that hasn't been challenged (it's been tested)
- Multiple IPR petitions against the same patent signal coordinated generic interest

---

## Freedom-to-Operate Analysis

When evaluating whether a drug can be developed and commercialized without infringing others' patents:

### Key Questions
1. **Are there blocking patents?** Does a third party hold patents that the drug would infringe?
2. **Can the blocking patents be designed around?** Is there an alternative approach that avoids infringement?
3. **Are the blocking patents valid?** Could they be challenged via IPR or litigation?
4. **Is there a licensing path?** Can the company obtain a license at reasonable terms?

### For ADCs Specifically
FTO analysis is particularly complex because ADCs involve multiple components:
- Antibody targeting the antigen
- Linker chemistry (e.g., Seagen's vc-MMAE technology was broadly patented)
- Payload molecule
- Conjugation method
- The combination itself

Each component may be covered by different patents held by different entities.

### For Small Molecules
- Check whether the target itself is patented (target patents are harder to enforce)
- Structural analogs and the scope of composition claims
- Polymorph patents on the specific crystal form
- Metabolite patents

---

## Biosimilar & Generic Entry

### Small Molecule Generics
- **ANDA pathway**: Demonstrate bioequivalence to the reference product. No clinical trials typically needed.
- **Timeline**: After NCE exclusivity (5 years) + patent expiry (whichever is later). Para IV challenge can accelerate this.
- **180-day exclusivity**: First-to-file Para IV generic gets 180 days of generic exclusivity. This incentivizes early Para IV filings.
- **Price impact**: Generics typically enter at 80-90% discount within 1-2 years of first generic launch (more competitors = deeper discounts).

### Biosimilars
- **aBLA pathway (351(k))**: Demonstrate biosimilarity (and optionally interchangeability) to the reference biologic.
- **Timeline**: After 12-year reference product exclusivity (US) or 8+2 year (EU). Patent dance under BPCIA for US patents.
- **Interchangeability**: Interchangeable biosimilars can be substituted at the pharmacy without physician intervention. Higher bar to achieve but significant commercial advantage.
- **Price impact**: Biosimilar discounts are typically 15-35% in the US, deeper in Europe. Fewer competitors compared to small molecule generics due to manufacturing barriers.

### Revenue Impact Modeling
When modeling patent cliff impact:
- Small molecules: Model 80-90% revenue loss within 2 years of first generic entry
- Biologics: Model 30-50% revenue loss within 3-5 years of first biosimilar entry (slower erosion)
- Factor in authorized generics/biosimilars (the innovator launching their own generic to capture share)

---

## Patent Cliff Analysis

### Building a Patent Timeline
For each asset, construct a timeline showing:

1. **Earliest possible generic/biosimilar entry date** — the later of patent expiry and regulatory exclusivity expiry
2. **Key patents and their expiry dates** (including PTE/SPC)
3. **Pending patent challenges** (IPR, Para IV, litigation)
4. **Pipeline assets that could replace revenue** before the cliff

### Portfolio-Level Analysis
For multi-product companies:
- Map the patent cliffs for all key products on a single timeline
- Identify years of concentrated revenue risk
- Assess whether pipeline assets can fill the gap (revenue replacement)
- Compare to peers — companies with well-staggered patent cliffs are more defensible

---

## Licensing & IP Ownership

### Deal Structure Analysis
- **Exclusive vs non-exclusive licenses**: Exclusive licenses are far more valuable. Non-exclusive means competitors could also license.
- **Field-of-use restrictions**: Is the license limited to specific indications? Geographies?
- **Sublicensing rights**: Can the licensee sublicense to partners?
- **Milestone payments**: Clinical milestones (IND, Phase 1/2/3 start, Phase 1/2/3 results) and regulatory milestones (NDA filing, FDA approval). These are contingent liabilities/assets.
- **Royalty tiers**: Typically tiered by net sales (e.g., low-teens % up to $1B, mid-teens % above $1B). Assess whether royalties make the product commercially viable.
- **Opt-in/opt-out rights**: Does the licensor or licensee have the right to opt in to co-development or co-commercialization? This affects economics and control.
- **Reversion rights**: If the licensee stops development, do rights revert? This protects the asset.

### Key Questions for Investors
1. Who owns the composition of matter patent? (The COM patent holder has ultimate leverage.)
2. What happens if the licensing partner is acquired? (Change of control provisions.)
3. Are there co-exclusive or co-development arrangements that could create conflict?
4. What's the total economic burden (milestones + royalties) and does the drug still have attractive unit economics after these payments?
