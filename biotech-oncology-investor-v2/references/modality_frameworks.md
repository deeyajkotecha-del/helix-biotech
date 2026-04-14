# Modality-Specific Evaluation Frameworks

## Table of Contents
1. [Antibody-Drug Conjugates (ADCs)](#adcs)
2. [Small Molecules](#small-molecules)
3. [Bispecific Antibodies](#bispecifics)
4. [Cell Therapies](#cell-therapies)
5. [Immune Checkpoint Inhibitors](#checkpoint-inhibitors)
6. [Cancer Vaccines](#cancer-vaccines)
7. [Radioligand Therapy](#radioligand-therapy)
8. [Gene Therapy](#gene-therapy)

---

## ADCs

Antibody-drug conjugates combine a targeting antibody with a cytotoxic payload via a chemical linker. Their complexity creates unique investment considerations.

### PK/PD Considerations
- **Drug-antibody ratio (DAR)**: Typically 2-8. Higher DAR increases potency but can impair PK (faster clearance, aggregation). DAR ~4 is a common sweet spot.
- **Linker stability**: Cleavable vs non-cleavable linkers. Cleavable linkers (e.g., valine-citrulline) release payload in the tumor microenvironment. Non-cleavable linkers (e.g., SMCC in T-DM1) require lysosomal degradation. Linker stability in plasma affects the toxicity profile.
- **Bystander effect**: Payloads that can cross cell membranes after release (e.g., DXd, MMAE) kill neighboring tumor cells even without target expression. This matters for heterogeneous tumors but also drives off-target toxicity.
- **Target expression and internalization**: The target antigen must be expressed on tumor cells AND efficiently internalized upon antibody binding. Targets that shed extracellularly or don't internalize well are problematic.
- **Payload class**: Topoisomerase I inhibitors (DXd, SN-38), microtubule inhibitors (MMAE, DM1, DM4), DNA-damaging agents (PBD, calicheamicin). Each class has a different potency and resistance profile.

### Manufacturing/CMC
- **Conjugation chemistry**: Site-specific conjugation produces more homogeneous product with tighter DAR control vs. random conjugation. This affects batch-to-batch consistency and regulatory scrutiny.
- **Analytical complexity**: Characterizing a heterogeneous ADC mixture is harder than a naked antibody. Regulators expect extensive characterization data.
- **Supply chain**: Three components (antibody, linker, payload) from potentially different manufacturers. Supply chain coordination and quality control at each step.
- **Scalability**: Conjugation step can be a bottleneck. Assess manufacturing capacity relative to projected demand.

### Key Safety Signals
- **Interstitial lung disease (ILD)/pneumonitis**: Particularly with topo-I inhibitor payloads (e.g., T-DXd). This is the signal that killed several ADC programs. Grade 2+ ILD rates matter enormously.
- **Ocular toxicity**: Common with MMAF payloads and some others. Corneal deposits, blurred vision.
- **Neuropathy**: Microtubule inhibitor payloads (MMAE, DM1) cause peripheral neuropathy.
- **Hematologic toxicity**: Neutropenia, thrombocytopenia — varies by payload.

### Competitive Dynamics
- The ADC landscape is increasingly crowded, especially in HER2+ and TROP2+ cancers. Differentiation now comes from novel targets, improved linker-payload technology, and combination strategies.

---

## Small Molecules

### PK/PD Considerations
- **Oral bioavailability**: Oral drugs have major commercial advantages over IV. Assess bioavailability, food effects, and dosing frequency.
- **Half-life and dosing**: Once-daily dosing is commercially preferred. BID dosing is acceptable. TID is a commercial disadvantage.
- **CYP interactions**: Which CYP enzymes metabolize the drug? Are there DDI (drug-drug interaction) risks? This matters for combination strategies and real-world use in patients on multiple medications.
- **Selectivity**: For kinase inhibitors especially — off-target kinase inhibition drives toxicity. Compare the kinase selectivity profile to competitors.
- **Resistance mechanisms**: What are the known or predicted resistance mechanisms? Is there a next-generation molecule in the pipeline to address resistance?
- **CNS penetration**: For indications with brain metastases (common in NSCLC, melanoma, breast cancer), CNS-penetrant drugs have significant advantages.

### Manufacturing/CMC
- **Synthetic complexity**: Number of synthetic steps, use of hazardous reagents, chiral centers. More complex synthesis = higher COGS and scale-up risk.
- **Polymorphism**: Different crystal forms can affect bioavailability and stability. Robust polymorph screening is important.
- **Formulation**: Standard oral solid dosage forms (tablets, capsules) are straightforward. Special formulations (e.g., amorphous solid dispersions) add complexity.
- **COGS**: Small molecules generally have favorable cost of goods vs biologics. But specialty intermediates or complex chemistry can erode this advantage.

### Key Safety Signals
- **Hepatotoxicity**: ALT/AST elevations, Hy's Law cases. This is a common program-killer.
- **Cardiac effects**: QTc prolongation (especially kinase inhibitors), LVEF decline.
- **Class-specific toxicity**: Depends on the target — e.g., EGFR inhibitors cause rash and diarrhea, VEGFR inhibitors cause hypertension and proteinuria, CDK4/6 inhibitors cause neutropenia.

---

## Bispecifics

Bispecific antibodies engage two different targets simultaneously. The most common oncology format is T-cell engagers (TCEs) that bridge tumor cells to T cells.

### PK/PD Considerations
- **Format**: Full-length IgG-like bispecifics have longer half-life (~2-3 weeks) vs smaller formats like BiTEs (~2 hours, requiring continuous infusion or subcutaneous dosing with half-life extension).
- **Cytokine release syndrome (CRS)**: T-cell engagers cause CRS, especially with first doses. Step-up dosing protocols and hospitalization requirements affect commercial viability.
- **T-cell exhaustion**: Continuous T-cell activation can lead to exhaustion over time, limiting durability.
- **Tumor accessibility**: Large molecules have limited tumor penetration. Solid tumors are harder targets than hematologic malignancies.

### Manufacturing/CMC
- **Chain pairing**: Ensuring correct heavy-light chain pairing is the central manufacturing challenge. Technologies like knobs-into-holes, CrossMAb, and common light chain address this.
- **Yield and purity**: Bispecific yields are typically lower than monospecific antibodies. Purification of the desired bispecific from homodimeric contaminants requires additional steps.
- **Stability**: Some bispecific formats are inherently less stable than conventional antibodies.

### Key Safety Signals
- **CRS**: The dominant safety concern for TCEs. Grade 3+ CRS rates and management protocols matter.
- **Neurotoxicity (ICANS)**: Immune effector cell-associated neurotoxicity, similar to CAR-T.
- **Infections**: Particularly with CD20-targeting bispecifics — prolonged B-cell depletion increases infection risk.

---

## Cell Therapies

Includes CAR-T, TIL (tumor-infiltrating lymphocyte) therapy, TCR-T, and NK cell therapy.

### PK/PD Considerations
- **Expansion and persistence**: CAR-T cells need to expand in vivo and persist for durable responses. Peak expansion levels and persistence at 6-12 months correlate with outcomes.
- **Trafficking to solid tumors**: The biggest challenge for cell therapy in solid tumors. The immunosuppressive tumor microenvironment limits efficacy.
- **Manufacturing turnaround (vein-to-vein time)**: Autologous products require 3-6 weeks from apheresis to infusion. Patients may progress during this time. Allogeneic (off-the-shelf) products solve this but face rejection and durability challenges.

### Manufacturing/CMC
- **Autologous vs allogeneic**: Autologous products are patient-specific — every batch is unique. This limits scalability and creates logistics challenges. Allogeneic products are scalable but face biological hurdles.
- **Manufacturing success rate**: What percentage of patients who undergo apheresis actually receive the product? Manufacturing failures are a real issue.
- **Decentralized vs centralized manufacturing**: Centralized manufacturing at specialized facilities vs. point-of-care manufacturing. Each has tradeoffs in quality control, scalability, and cost.
- **COGS**: Cell therapies are extremely expensive to manufacture ($50K-150K+ COGS per patient). This limits pricing flexibility and market access.

### Key Safety Signals
- **CRS**: Universal with TCEs and CAR-T. Management with tocilizumab is well-established but adds cost and complexity.
- **ICANS**: Neurotoxicity that can range from confusion to seizures to cerebral edema. Monitoring requirements affect where patients can be treated.
- **Prolonged cytopenias**: Extended periods of low blood counts post-treatment.
- **Secondary malignancies**: T-cell lymphomas have been reported in rare cases — an emerging concern that FDA is monitoring.

---

## Checkpoint Inhibitors

Anti-PD-1, anti-PD-L1, anti-CTLA-4, anti-LAG-3, anti-TIGIT, and other immune checkpoint antibodies.

### PK/PD Considerations
- **PD-1/PD-L1 receptor occupancy**: Most anti-PD-1 agents achieve near-complete receptor occupancy at approved doses. Dose optimization for lower doses is an emerging trend (e.g., pembrolizumab 200mg vs 400mg Q6W).
- **Combination strategies**: The field is saturated with anti-PD-1 combinations. Novel checkpoint targets (LAG-3, TIGIT, TIM-3) are being tested in combination.
- **Biomarker selection**: PD-L1 expression (TPS, CPS), TMB, MSI/dMMR, and gene expression signatures. Better biomarker selection improves response rates but narrows the addressable market.

### Manufacturing/CMC
- Standard antibody manufacturing — well-understood process. Not a major differentiator at this point.

### Key Safety Signals
- **Immune-related adverse events (irAEs)**: Colitis, hepatitis, pneumonitis, endocrinopathies (thyroid, adrenal, pituitary), dermatologic toxicity. Generally manageable with steroids but some can be life-threatening or permanent.
- **Combination toxicity**: Dual checkpoint blockade (e.g., nivo + ipi) significantly increases Grade 3+ irAE rates (40-60% vs 10-20% for monotherapy).

---

## Cancer Vaccines

Includes neoantigen vaccines (personalized and shared), tumor-associated antigen vaccines, and mRNA-based approaches.

### PK/PD Considerations
- **Immune response measurement**: T-cell responses (ELISpot, intracellular cytokine staining, multimer staining) — quality matters as much as magnitude.
- **Neoantigen selection**: Personalized vaccines target patient-specific mutations. The algorithm for neoantigen prediction and selection is critical IP.
- **Adjuvant setting**: Vaccines work best with minimal disease burden. Most promising in adjuvant (post-surgery) settings rather than advanced disease.
- **Combination with checkpoint inhibitors**: Near-universal combination strategy. Vaccines prime the immune response, checkpoints prevent its suppression.

### Manufacturing/CMC
- **Personalized vaccines**: Each vaccine is manufactured for a single patient. Turnaround time from biopsy to vaccine delivery is a critical metric (typically 4-8 weeks).
- **Scalability**: Personalized manufacturing limits scalability. Shared/off-the-shelf neoantigen approaches are more scalable but may be less effective.
- **mRNA platform advantages**: mRNA vaccines can be manufactured relatively quickly once the sequence is designed. The COVID vaccine infrastructure has de-risked mRNA manufacturing.

### Key Safety Signals
- Generally very favorable safety profiles — mostly injection site reactions and flu-like symptoms. This is an advantage in combination strategies.

---

## Radioligand Therapy

Targeted radiopharmaceuticals that deliver radioactive payloads to tumor cells (e.g., 177Lu-PSMA-617 / Pluvicto).

### PK/PD Considerations
- **Target specificity**: The targeting moiety (antibody, peptide, small molecule) must bind selectively to tumor cells. Off-target binding drives toxicity.
- **Radioisotope selection**: 177Lu (beta emitter, medium range), 225Ac (alpha emitter, short range/high potency), 131I. Different isotopes have different tissue penetration and potency.
- **Dosimetry**: Patient-specific dosimetry (measuring radiation dose to tumor vs. organs) is an emerging field. Not all patients absorb the same dose.

### Manufacturing/CMC
- **Radioisotope supply**: Limited global supply of certain isotopes (especially 225Ac). Supply chain constraints can limit commercial scale.
- **Shelf life**: Radioactive decay means short shelf life (days to weeks depending on isotope). This creates logistics challenges for distribution.
- **Specialized facilities**: Manufacturing and handling require nuclear pharmacy infrastructure. This limits which sites can administer the therapy.

### Key Safety Signals
- **Hematologic toxicity**: Bone marrow is radiation-sensitive. Myelosuppression is the most common dose-limiting toxicity.
- **Kidney toxicity**: Some targets are expressed in kidneys (e.g., PSMA at low levels in proximal tubules).
- **Xerostomia**: Salivary gland uptake is common with several targets, causing dry mouth.

---

## Gene Therapy

Includes oncolytic viruses, gene editing (CRISPR-based), and gene transfer approaches in oncology.

### PK/PD Considerations
- **Vector selection**: AAV, lentivirus, adenovirus, herpes simplex virus. Each has different tropism, immunogenicity, and payload capacity.
- **Immune response to vector**: Pre-existing immunity to viral vectors (especially AAV) limits eligible patient populations and redosing.
- **Tumor selectivity**: For oncolytic viruses, selectivity for tumor cells vs. normal tissue is critical.
- **Durability**: One-time vs repeat dosing. True one-time gene therapy is the goal but immunogenicity often prevents redosing.

### Manufacturing/CMC
- **Viral vector manufacturing**: Low yields, complex purification, batch-to-batch variability. This remains the biggest bottleneck.
- **Potency assays**: Defining and measuring potency for gene therapy products is challenging.
- **Scale-up**: Moving from clinical to commercial scale manufacturing is a major hurdle. Several gene therapies have faced manufacturing-related delays.

### Key Safety Signals
- **Insertional mutagenesis**: With integrating vectors (lentivirus), there's a theoretical risk of activating oncogenes.
- **Immune-mediated toxicity**: Inflammatory responses to the vector or transgene product.
- **Off-target effects**: For CRISPR-based approaches, off-target editing is a safety concern.
