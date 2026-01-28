/**
 * Helix Intelligence Database Schema
 *
 * Core data types for the biotech analyst platform.
 * Designed to compete with Citeline/Evaluate.
 */

// ============================================
// Core Enums
// ============================================

export type TrialPhase =
  | 'Preclinical'
  | 'Phase 1'
  | 'Phase 1/2'
  | 'Phase 2'
  | 'Phase 2/3'
  | 'Phase 3'
  | 'Phase 4'
  | 'Not Applicable';

export type TrialStatus =
  | 'Not yet recruiting'
  | 'Recruiting'
  | 'Enrolling by invitation'
  | 'Active, not recruiting'
  | 'Completed'
  | 'Suspended'
  | 'Terminated'
  | 'Withdrawn'
  | 'Unknown';

export type DealType =
  | 'Acquisition'
  | 'Merger'
  | 'Licensing'
  | 'Partnership'
  | 'Collaboration'
  | 'Co-development'
  | 'Option'
  | 'Asset Purchase'
  | 'Funding'
  | 'IPO'
  | 'SPAC';

export type PatentType =
  | 'Composition of Matter'
  | 'Method of Use'
  | 'Formulation'
  | 'Process'
  | 'Combination';

export type PatentStatus =
  | 'Active'
  | 'Expired'
  | 'Pending'
  | 'Abandoned'
  | 'Challenged';

export type AdverseEventGrade = 1 | 2 | 3 | 4 | 5; // CTCAE grades

export type Region =
  | 'United States'
  | 'Europe'
  | 'Japan'
  | 'China'
  | 'Rest of World'
  | 'Global';

// ============================================
// 1. Trials
// ============================================

export interface Trial {
  // Identifiers
  nctId: string;                        // Primary key (e.g., "NCT01234567")
  otherIds?: string[];                  // Sponsor IDs, EudraCT numbers, etc.

  // Basic info
  briefTitle: string;
  officialTitle?: string;
  acronym?: string;

  // Classification
  phase: TrialPhase;
  status: TrialStatus;
  studyType: 'Interventional' | 'Observational' | 'Expanded Access';

  // Sponsor & Collaborators
  leadSponsor: {
    name: string;
    type: 'Industry' | 'Academic' | 'Government' | 'Other';
  };
  collaborators?: string[];

  // Conditions & Interventions
  conditions: string[];                  // MeSH terms or free text
  conditionMeshTerms?: string[];         // Standardized MeSH IDs
  interventions: Intervention[];

  // Design
  design?: {
    allocation?: 'Randomized' | 'Non-randomized' | 'N/A';
    interventionModel?: 'Single Group' | 'Parallel' | 'Crossover' | 'Sequential' | 'Factorial';
    primaryPurpose?: 'Treatment' | 'Prevention' | 'Diagnostic' | 'Supportive Care' | 'Screening' | 'Other';
    masking?: 'None' | 'Single' | 'Double' | 'Triple' | 'Quadruple';
  };

  // Enrollment
  enrollment?: {
    count: number;
    type: 'Actual' | 'Anticipated';
  };

  // Key dates
  startDate?: string;                    // ISO date string
  primaryCompletionDate?: string;        // Primary endpoint data collection complete
  completionDate?: string;               // Study completion
  firstPostedDate?: string;
  lastUpdateDate?: string;

  // Outcomes
  primaryOutcomes?: Outcome[];
  secondaryOutcomes?: Outcome[];

  // Results
  resultsAvailable: boolean;
  resultsFirstPosted?: string;

  // Locations
  locations?: TrialLocation[];
  countries?: string[];

  // Links
  publications?: string[];               // PMIDs

  // Metadata
  fetchedAt: string;
  source: 'ClinicalTrials.gov' | 'EudraCT' | 'WHO ICTRP';
}

export interface Intervention {
  type: 'Drug' | 'Biological' | 'Device' | 'Procedure' | 'Radiation' | 'Behavioral' | 'Dietary' | 'Other';
  name: string;
  description?: string;
  armGroupLabels?: string[];
  otherNames?: string[];                 // Aliases, brand names
}

export interface Outcome {
  measure: string;
  description?: string;
  timeFrame?: string;
}

export interface TrialLocation {
  facility?: string;
  city?: string;
  state?: string;
  country: string;
  status?: string;
}

// ============================================
// 2. Trial Results
// ============================================

export interface TrialResults {
  nctId: string;                         // Foreign key to Trial

  // Participant flow
  participantFlow?: {
    recruitmentDetails?: string;
    preAssignmentDetails?: string;
    groups: ParticipantGroup[];
    periods: FlowPeriod[];
  };

  // Baseline characteristics
  baselineCharacteristics?: {
    groups: ParticipantGroup[];
    measures: BaselineMeasure[];
  };

  // Outcome results
  primaryOutcomes: OutcomeResult[];
  secondaryOutcomes?: OutcomeResult[];

  // Adverse events summary
  adverseEventsSummary?: {
    timeFrame: string;
    description?: string;
    groups: ParticipantGroup[];
    seriousEvents: AdverseEventCategory[];
    otherEvents: AdverseEventCategory[];
  };

  // Analysis
  pointOfContactOrg?: string;
  limitations?: string;

  fetchedAt: string;
}

export interface ParticipantGroup {
  id: string;
  title: string;
  description?: string;
}

export interface FlowPeriod {
  title: string;
  milestones: {
    type: 'Started' | 'Completed' | 'Not Completed';
    counts: { groupId: string; count: number }[];
  }[];
}

export interface BaselineMeasure {
  title: string;
  description?: string;
  units?: string;
  param: 'Count' | 'Mean' | 'Median' | 'Number' | 'Least Squares Mean' | 'Geometric Mean' | 'Log Mean';
  dispersion?: 'Standard Deviation' | 'Standard Error' | '95% Confidence Interval' | 'Inter-Quartile Range' | 'Full Range';
  classes: {
    title?: string;
    categories: {
      title?: string;
      measurements: {
        groupId: string;
        value?: string;
        spread?: string;
        lowerLimit?: string;
        upperLimit?: string;
      }[];
    }[];
  }[];
}

export interface OutcomeResult {
  title: string;
  description?: string;
  timeFrame?: string;
  type: 'Primary' | 'Secondary' | 'Post-Hoc' | 'Other Pre-specified';
  populationDescription?: string;
  reportingStatus: 'Posted' | 'Not Posted';

  // Results by arm
  groups: ParticipantGroup[];
  measures: OutcomeMeasure[];

  // Statistical analysis
  analyses?: OutcomeAnalysis[];
}

export interface OutcomeMeasure {
  title: string;
  description?: string;
  units?: string;
  param: 'Count' | 'Mean' | 'Median' | 'Number' | 'Least Squares Mean' | 'Geometric Mean' | 'Log Mean';
  dispersion?: 'Standard Deviation' | 'Standard Error' | '95% Confidence Interval' | 'Inter-Quartile Range' | 'Full Range';
  classes: {
    title?: string;
    categories: {
      title?: string;
      measurements: ArmMeasurement[];
    }[];
  }[];
}

export interface ArmMeasurement {
  groupId: string;
  value?: string;
  spread?: string;                       // SD, SE, etc.
  lowerLimit?: string;                   // For CI
  upperLimit?: string;                   // For CI
  comment?: string;
}

export interface OutcomeAnalysis {
  groupIds: string[];                    // Which arms are compared
  groupDescription?: string;
  nonInferiorityType?: 'Superiority' | 'Non-Inferiority' | 'Equivalence' | 'Other';
  pValue?: string;
  pValueComment?: string;
  statisticalMethod?: string;
  statisticalComment?: string;
  paramType?: string;
  paramValue?: string;
  ciPctValue?: string;
  ciNumSides?: 'One-Sided' | 'Two-Sided';
  ciLowerLimit?: string;
  ciUpperLimit?: string;
  estimateComment?: string;
}

// ============================================
// 3. Safety Data
// ============================================

export interface SafetyData {
  nctId: string;                         // Foreign key to Trial

  timeFrame: string;
  description?: string;

  // Arms/groups
  groups: ParticipantGroup[];

  // Serious adverse events
  seriousEvents: AdverseEventCategory[];

  // Other adverse events
  otherEvents: AdverseEventCategory[];

  // Totals
  totals?: {
    groupId: string;
    seriousNumAffected: number;
    seriousNumAtRisk: number;
    otherNumAffected: number;
    otherNumAtRisk: number;
  }[];

  fetchedAt: string;
}

export interface AdverseEventCategory {
  term: string;                          // MedDRA preferred term
  organSystem?: string;                  // System Organ Class
  sourceVocabulary?: string;             // e.g., "MedDRA 24.0"
  assessmentType?: 'Systematic' | 'Non-systematic';

  // By arm
  stats: AdverseEventStats[];
}

export interface AdverseEventStats {
  groupId: string;
  numEvents?: number;                    // Total events
  numAffected: number;                   // Participants affected
  numAtRisk: number;                     // Participants at risk

  // By grade (CTCAE)
  byGrade?: {
    grade: AdverseEventGrade;
    count: number;
  }[];
}

// ============================================
// 4. Molecules
// ============================================

export interface Molecule {
  // Identifiers
  id: string;                            // Internal ID (slug of primary name)
  primaryName: string;                   // INN or most common name
  aliases: string[];                     // Brand names, research codes, etc.

  // Classification
  type: 'Small Molecule' | 'Biologic' | 'Cell Therapy' | 'Gene Therapy' | 'Vaccine' | 'Oligonucleotide' | 'Other';
  mechanismOfAction?: string;            // e.g., "IL-23 inhibitor"
  target?: string;                       // e.g., "IL-23p19"
  targetClass?: string;                  // e.g., "Cytokine"

  // Development
  originatorCompany?: string;
  currentOwners: string[];               // Companies with rights
  highestPhase: TrialPhase;
  approvalStatus?: {
    region: Region;
    status: 'Approved' | 'Filed' | 'Not Approved';
    date?: string;
    indication?: string;
    brandName?: string;
  }[];

  // Indications
  indications: {
    condition: string;
    phase: TrialPhase;
    status: 'Active' | 'Discontinued' | 'Approved';
  }[];

  // Linked data
  trialIds: string[];                    // NCT IDs
  patentIds?: string[];
  dealIds?: string[];
  publicationPmids?: string[];

  // Metadata
  lastUpdated: string;
}

// ============================================
// 5. Publications
// ============================================

export interface Publication {
  // Identifiers
  pmid: string;                          // Primary key
  doi?: string;
  pmcid?: string;

  // Bibliographic
  title: string;
  abstract?: string;
  journal: {
    name: string;
    abbreviation?: string;
    issn?: string;
  };
  publicationDate: string;               // ISO date
  publicationType: string[];             // e.g., ["Journal Article", "Clinical Trial"]

  // Authors
  authors: Author[];

  // Content
  meshTerms?: string[];
  keywords?: string[];

  // Links
  linkedTrials?: string[];               // NCT IDs mentioned in abstract/text
  linkedMolecules?: string[];            // Drug names mentioned

  // Metrics
  citationCount?: number;

  // Full text
  fullTextAvailable: boolean;
  fullTextUrl?: string;

  // Metadata
  fetchedAt: string;
}

export interface Author {
  lastName: string;
  foreName?: string;
  initials?: string;
  fullName: string;                      // Computed: "LastName ForeName"
  affiliation?: string;
  email?: string;
  orcid?: string;
  isCorresponding?: boolean;
  authorPosition: 'First' | 'Last' | 'Middle';
}

// ============================================
// 6. Key Opinion Leaders (KOLs)
// ============================================

export interface KOL {
  // Identifier
  id: string;                            // Normalized name slug

  // Name (normalized)
  primaryName: string;                   // e.g., "Smith John A"
  nameVariations: string[];              // Other forms seen in publications

  // Affiliation
  currentInstitution?: string;
  institutionHistory?: {
    institution: string;
    from?: string;
    to?: string;
  }[];
  country?: string;

  // Contact
  email?: string;
  orcid?: string;

  // Metrics
  publicationCount: number;
  recentPublicationCount: number;        // Last 3 years
  hIndex?: number;
  citationCount?: number;

  // Activity
  firstPublicationDate?: string;
  lastPublicationDate: string;
  isActive: boolean;                     // Published in last 3 years

  // Specialization
  therapeuticAreas: string[];            // Derived from publication MeSH terms
  topConditions: { condition: string; count: number }[];
  topDrugs: { drug: string; count: number }[];

  // Linked data
  publicationPmids: string[];
  trialInvolvement?: {
    nctId: string;
    role: 'Principal Investigator' | 'Study Chair' | 'Study Director';
  }[];

  // Industry ties
  industryCollaborations?: {
    company: string;
    type: 'Consultant' | 'Speaker' | 'Investigator' | 'Advisory Board';
    source?: string;
  }[];

  // Metadata
  lastUpdated: string;
}

// ============================================
// 7. Patents
// ============================================

export interface Patent {
  // Identifiers
  patentNumber: string;                  // Primary key (e.g., "US10123456")
  applicationNumber?: string;

  // Type & Status
  patentType: PatentType;
  status: PatentStatus;

  // Dates
  filingDate?: string;
  grantDate?: string;
  expiryDate?: string;                   // Including extensions
  originalExpiryDate?: string;           // Before extensions

  // Extensions
  extensions?: {
    type: 'PTE' | 'PED' | 'SPC';         // Patent Term Extension, Pediatric Exclusivity, Supplementary Protection Certificate
    days: number;
    grantDate?: string;
  }[];

  // Content
  title: string;
  abstract?: string;
  claims?: string[];

  // Ownership
  assignee: string;                      // Current owner
  originalAssignee?: string;
  inventors?: string[];

  // Drug linkage
  drugName?: string;
  activeIngredient?: string;
  ndc?: string;                          // National Drug Code

  // Orange Book specific
  orangeBookListed?: boolean;
  therapeuticEquivalence?: string;

  // Litigation
  challenges?: {
    type: 'IPR' | 'PGR' | 'ANDA' | 'Hatch-Waxman';
    challenger?: string;
    filingDate?: string;
    status?: string;
    outcome?: string;
  }[];

  // Metadata
  source: 'USPTO' | 'Orange Book' | 'EPO' | 'WIPO';
  fetchedAt: string;
}

// ============================================
// 8. Deals
// ============================================

export interface Deal {
  // Identifier
  id: string;                            // Internal ID

  // Parties
  acquirer?: string;                     // For M&A
  target?: string;                       // For M&A
  licensor?: string;                     // For licensing
  licensee?: string;                     // For licensing
  parties: string[];                     // All companies involved

  // Classification
  dealType: DealType;
  stage?: 'Announced' | 'Pending' | 'Completed' | 'Terminated';

  // Dates
  announcementDate: string;
  closingDate?: string;

  // Asset
  asset?: {
    name: string;                        // Drug/technology name
    type: 'Drug' | 'Platform' | 'Company' | 'Division' | 'Rights';
    indications?: string[];
    phase?: TrialPhase;
    moleculeId?: string;                 // Link to Molecule
  };

  // Terms
  terms?: {
    upfrontPayment?: number;             // In millions USD
    milestones?: number;                 // Total potential milestones
    royalties?: string;                  // e.g., "tiered royalties up to low double digits"
    totalValue?: number;                 // In millions USD
    equityComponent?: string;
    otherTerms?: string;
  };

  // Geography
  territories?: string[];                // e.g., ["US", "EU", "Japan"]

  // Sources
  sourceUrl?: string;
  pressReleaseUrl?: string;
  secFilingUrl?: string;

  // Metadata
  source: 'SEC Filing' | 'Press Release' | 'News' | 'Manual';
  fetchedAt: string;
}

// ============================================
// 9. Markets
// ============================================

export interface Market {
  // Identifier
  id: string;                            // e.g., "ulcerative-colitis-us-2024"

  // Classification
  indication: string;
  therapeuticArea?: string;
  region: Region;
  year: number;

  // Size
  marketSizeBillion: number;             // USD billions
  patientPopulation?: number;
  treatedPatients?: number;

  // Growth
  growthRatePct?: number;                // YoY growth
  cagr5Year?: number;                    // 5-year CAGR

  // Projections
  projections?: {
    year: number;
    sizeBillion: number;
    source?: string;
  }[];

  // Competitive landscape
  marketLeaders?: {
    company: string;
    drug: string;
    marketSharePct?: number;
    revenueBillion?: number;
  }[];

  // Pricing
  averageAnnualCost?: number;            // Per patient USD

  // Source
  source: string;                        // e.g., "IQVIA", "Company 10-K"
  sourceUrl?: string;

  // Metadata
  fetchedAt: string;
}

// ============================================
// 10. Endpoint Definitions
// ============================================

export interface EndpointDefinition {
  // Identifier
  id: string;                            // Slug of canonical name

  // Classification
  therapeuticArea: string;               // e.g., "Gastroenterology"
  condition?: string;                    // e.g., "Ulcerative Colitis"

  // Naming
  canonicalName: string;                 // e.g., "Clinical Remission (Mayo Score)"
  variations: string[];                  // Other ways it's written
  abbreviations?: string[];              // e.g., ["CR", "MCS"]

  // Definition
  definition: string;                    // What it measures
  components?: string[];                 // Sub-scores if composite

  // Scoring
  scoreRange?: {
    min: number;
    max: number;
  };
  responseThreshold?: string;            // e.g., "Mayo score <= 2 with no subscore > 1"
  remissionThreshold?: string;

  // Regulatory
  regulatoryAcceptance?: {
    agency: 'FDA' | 'EMA' | 'PMDA';
    status: 'Accepted' | 'Preferred' | 'Exploratory';
    guidance?: string;
  }[];

  // References
  validationStudies?: string[];          // PMIDs

  // Notes
  notes?: string;

  // Metadata
  lastUpdated: string;
}

// ============================================
// Aggregate/View Types
// ============================================

/**
 * Competitive landscape view for a condition
 */
export interface CompetitiveLandscape {
  condition: string;
  asOfDate: string;

  // Pipeline
  trialsByPhase: Record<TrialPhase, number>;
  activeMolecules: {
    molecule: string;
    company: string;
    phase: TrialPhase;
    mechanism: string;
  }[];

  // Market
  marketSize?: number;
  marketLeaders?: {
    company: string;
    drug: string;
    sharePercent: number;
  }[];

  // Recent activity
  recentDeals: Deal[];
  recentPublications: Publication[];

  // Key players
  topCompanies: { company: string; trialCount: number }[];
  topKOLs: { name: string; institution: string; pubCount: number }[];
}

/**
 * Drug profile view
 */
export interface DrugProfile {
  molecule: Molecule;
  trials: Trial[];
  results: TrialResults[];
  safety: SafetyData[];
  patents: Patent[];
  deals: Deal[];
  publications: Publication[];
  competitors: Molecule[];
}

// ============================================
// Database Collections (for future DB)
// ============================================

export interface HelixDatabase {
  trials: Map<string, Trial>;                    // Key: nctId
  trialResults: Map<string, TrialResults>;       // Key: nctId
  safetyData: Map<string, SafetyData>;           // Key: nctId
  molecules: Map<string, Molecule>;              // Key: molecule.id
  publications: Map<string, Publication>;        // Key: pmid
  kols: Map<string, KOL>;                        // Key: kol.id
  patents: Map<string, Patent>;                  // Key: patentNumber
  deals: Map<string, Deal>;                      // Key: deal.id
  markets: Map<string, Market>;                  // Key: market.id
  endpointDefinitions: Map<string, EndpointDefinition>; // Key: endpoint.id
}
