/**
 * Helix Intelligence Database Schema
 *
 * Core data types for the biotech analyst platform.
 * Designed to compete with Citeline/Evaluate.
 */
export type TrialPhase = 'Preclinical' | 'Phase 1' | 'Phase 1/2' | 'Phase 2' | 'Phase 2/3' | 'Phase 3' | 'Phase 4' | 'Not Applicable';
export type TrialStatus = 'Not yet recruiting' | 'Recruiting' | 'Enrolling by invitation' | 'Active, not recruiting' | 'Completed' | 'Suspended' | 'Terminated' | 'Withdrawn' | 'Unknown';
export type DealType = 'Acquisition' | 'Merger' | 'Licensing' | 'Partnership' | 'Collaboration' | 'Co-development' | 'Option' | 'Asset Purchase' | 'Funding' | 'IPO' | 'SPAC';
export type PatentType = 'Composition of Matter' | 'Method of Use' | 'Formulation' | 'Process' | 'Combination';
export type PatentStatus = 'Active' | 'Expired' | 'Pending' | 'Abandoned' | 'Challenged';
export type AdverseEventGrade = 1 | 2 | 3 | 4 | 5;
export type Region = 'United States' | 'Europe' | 'Japan' | 'China' | 'Rest of World' | 'Global';
export interface Trial {
    nctId: string;
    otherIds?: string[];
    briefTitle: string;
    officialTitle?: string;
    acronym?: string;
    phase: TrialPhase;
    status: TrialStatus;
    studyType: 'Interventional' | 'Observational' | 'Expanded Access';
    leadSponsor: {
        name: string;
        type: 'Industry' | 'Academic' | 'Government' | 'Other';
    };
    collaborators?: string[];
    conditions: string[];
    conditionMeshTerms?: string[];
    interventions: Intervention[];
    design?: {
        allocation?: 'Randomized' | 'Non-randomized' | 'N/A';
        interventionModel?: 'Single Group' | 'Parallel' | 'Crossover' | 'Sequential' | 'Factorial';
        primaryPurpose?: 'Treatment' | 'Prevention' | 'Diagnostic' | 'Supportive Care' | 'Screening' | 'Other';
        masking?: 'None' | 'Single' | 'Double' | 'Triple' | 'Quadruple';
    };
    enrollment?: {
        count: number;
        type: 'Actual' | 'Anticipated';
    };
    startDate?: string;
    primaryCompletionDate?: string;
    completionDate?: string;
    firstPostedDate?: string;
    lastUpdateDate?: string;
    primaryOutcomes?: Outcome[];
    secondaryOutcomes?: Outcome[];
    resultsAvailable: boolean;
    resultsFirstPosted?: string;
    locations?: TrialLocation[];
    countries?: string[];
    publications?: string[];
    fetchedAt: string;
    source: 'ClinicalTrials.gov' | 'EudraCT' | 'WHO ICTRP';
}
export interface Intervention {
    type: 'Drug' | 'Biological' | 'Device' | 'Procedure' | 'Radiation' | 'Behavioral' | 'Dietary' | 'Other';
    name: string;
    description?: string;
    armGroupLabels?: string[];
    otherNames?: string[];
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
export interface TrialResults {
    nctId: string;
    participantFlow?: {
        recruitmentDetails?: string;
        preAssignmentDetails?: string;
        groups: ParticipantGroup[];
        periods: FlowPeriod[];
    };
    baselineCharacteristics?: {
        groups: ParticipantGroup[];
        measures: BaselineMeasure[];
    };
    primaryOutcomes: OutcomeResult[];
    secondaryOutcomes?: OutcomeResult[];
    adverseEventsSummary?: {
        timeFrame: string;
        description?: string;
        groups: ParticipantGroup[];
        seriousEvents: AdverseEventCategory[];
        otherEvents: AdverseEventCategory[];
    };
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
        counts: {
            groupId: string;
            count: number;
        }[];
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
    groups: ParticipantGroup[];
    measures: OutcomeMeasure[];
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
    spread?: string;
    lowerLimit?: string;
    upperLimit?: string;
    comment?: string;
}
export interface OutcomeAnalysis {
    groupIds: string[];
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
export interface SafetyData {
    nctId: string;
    timeFrame: string;
    description?: string;
    groups: ParticipantGroup[];
    seriousEvents: AdverseEventCategory[];
    otherEvents: AdverseEventCategory[];
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
    term: string;
    organSystem?: string;
    sourceVocabulary?: string;
    assessmentType?: 'Systematic' | 'Non-systematic';
    stats: AdverseEventStats[];
}
export interface AdverseEventStats {
    groupId: string;
    numEvents?: number;
    numAffected: number;
    numAtRisk: number;
    byGrade?: {
        grade: AdverseEventGrade;
        count: number;
    }[];
}
export interface Molecule {
    id: string;
    primaryName: string;
    aliases: string[];
    type: 'Small Molecule' | 'Biologic' | 'Cell Therapy' | 'Gene Therapy' | 'Vaccine' | 'Oligonucleotide' | 'Other';
    mechanismOfAction?: string;
    target?: string;
    targetClass?: string;
    originatorCompany?: string;
    currentOwners: string[];
    highestPhase: TrialPhase;
    approvalStatus?: {
        region: Region;
        status: 'Approved' | 'Filed' | 'Not Approved';
        date?: string;
        indication?: string;
        brandName?: string;
    }[];
    indications: {
        condition: string;
        phase: TrialPhase;
        status: 'Active' | 'Discontinued' | 'Approved';
    }[];
    trialIds: string[];
    patentIds?: string[];
    dealIds?: string[];
    publicationPmids?: string[];
    lastUpdated: string;
}
export interface Publication {
    pmid: string;
    doi?: string;
    pmcid?: string;
    title: string;
    abstract?: string;
    journal: {
        name: string;
        abbreviation?: string;
        issn?: string;
    };
    publicationDate: string;
    publicationType: string[];
    authors: Author[];
    meshTerms?: string[];
    keywords?: string[];
    linkedTrials?: string[];
    linkedMolecules?: string[];
    citationCount?: number;
    fullTextAvailable: boolean;
    fullTextUrl?: string;
    fetchedAt: string;
}
export interface Author {
    lastName: string;
    foreName?: string;
    initials?: string;
    fullName: string;
    affiliation?: string;
    email?: string;
    orcid?: string;
    isCorresponding?: boolean;
    authorPosition: 'First' | 'Last' | 'Middle';
}
export interface KOL {
    id: string;
    primaryName: string;
    nameVariations: string[];
    currentInstitution?: string;
    institutionHistory?: {
        institution: string;
        from?: string;
        to?: string;
    }[];
    country?: string;
    email?: string;
    orcid?: string;
    publicationCount: number;
    recentPublicationCount: number;
    hIndex?: number;
    citationCount?: number;
    firstPublicationDate?: string;
    lastPublicationDate: string;
    isActive: boolean;
    therapeuticAreas: string[];
    topConditions: {
        condition: string;
        count: number;
    }[];
    topDrugs: {
        drug: string;
        count: number;
    }[];
    publicationPmids: string[];
    trialInvolvement?: {
        nctId: string;
        role: 'Principal Investigator' | 'Study Chair' | 'Study Director';
    }[];
    industryCollaborations?: {
        company: string;
        type: 'Consultant' | 'Speaker' | 'Investigator' | 'Advisory Board';
        source?: string;
    }[];
    lastUpdated: string;
}
export interface Patent {
    patentNumber: string;
    applicationNumber?: string;
    patentType: PatentType;
    status: PatentStatus;
    filingDate?: string;
    grantDate?: string;
    expiryDate?: string;
    originalExpiryDate?: string;
    extensions?: {
        type: 'PTE' | 'PED' | 'SPC';
        days: number;
        grantDate?: string;
    }[];
    title: string;
    abstract?: string;
    claims?: string[];
    assignee: string;
    originalAssignee?: string;
    inventors?: string[];
    drugName?: string;
    activeIngredient?: string;
    ndc?: string;
    orangeBookListed?: boolean;
    therapeuticEquivalence?: string;
    challenges?: {
        type: 'IPR' | 'PGR' | 'ANDA' | 'Hatch-Waxman';
        challenger?: string;
        filingDate?: string;
        status?: string;
        outcome?: string;
    }[];
    source: 'USPTO' | 'Orange Book' | 'EPO' | 'WIPO';
    fetchedAt: string;
}
export interface Deal {
    id: string;
    acquirer?: string;
    target?: string;
    licensor?: string;
    licensee?: string;
    parties: string[];
    dealType: DealType;
    stage?: 'Announced' | 'Pending' | 'Completed' | 'Terminated';
    announcementDate: string;
    closingDate?: string;
    asset?: {
        name: string;
        type: 'Drug' | 'Platform' | 'Company' | 'Division' | 'Rights';
        indications?: string[];
        phase?: TrialPhase;
        moleculeId?: string;
    };
    terms?: {
        upfrontPayment?: number;
        milestones?: number;
        royalties?: string;
        totalValue?: number;
        equityComponent?: string;
        otherTerms?: string;
    };
    territories?: string[];
    sourceUrl?: string;
    pressReleaseUrl?: string;
    secFilingUrl?: string;
    source: 'SEC Filing' | 'Press Release' | 'News' | 'Manual';
    fetchedAt: string;
}
export interface Market {
    id: string;
    indication: string;
    therapeuticArea?: string;
    region: Region;
    year: number;
    marketSizeBillion: number;
    patientPopulation?: number;
    treatedPatients?: number;
    growthRatePct?: number;
    cagr5Year?: number;
    projections?: {
        year: number;
        sizeBillion: number;
        source?: string;
    }[];
    marketLeaders?: {
        company: string;
        drug: string;
        marketSharePct?: number;
        revenueBillion?: number;
    }[];
    averageAnnualCost?: number;
    source: string;
    sourceUrl?: string;
    fetchedAt: string;
}
export interface EndpointDefinition {
    id: string;
    therapeuticArea: string;
    condition?: string;
    canonicalName: string;
    variations: string[];
    abbreviations?: string[];
    definition: string;
    components?: string[];
    scoreRange?: {
        min: number;
        max: number;
    };
    responseThreshold?: string;
    remissionThreshold?: string;
    regulatoryAcceptance?: {
        agency: 'FDA' | 'EMA' | 'PMDA';
        status: 'Accepted' | 'Preferred' | 'Exploratory';
        guidance?: string;
    }[];
    validationStudies?: string[];
    notes?: string;
    lastUpdated: string;
}
/**
 * Competitive landscape view for a condition
 */
export interface CompetitiveLandscape {
    condition: string;
    asOfDate: string;
    trialsByPhase: Record<TrialPhase, number>;
    activeMolecules: {
        molecule: string;
        company: string;
        phase: TrialPhase;
        mechanism: string;
    }[];
    marketSize?: number;
    marketLeaders?: {
        company: string;
        drug: string;
        sharePercent: number;
    }[];
    recentDeals: Deal[];
    recentPublications: Publication[];
    topCompanies: {
        company: string;
        trialCount: number;
    }[];
    topKOLs: {
        name: string;
        institution: string;
        pubCount: number;
    }[];
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
export interface HelixDatabase {
    trials: Map<string, Trial>;
    trialResults: Map<string, TrialResults>;
    safetyData: Map<string, SafetyData>;
    molecules: Map<string, Molecule>;
    publications: Map<string, Publication>;
    kols: Map<string, KOL>;
    patents: Map<string, Patent>;
    deals: Map<string, Deal>;
    markets: Map<string, Market>;
    endpointDefinitions: Map<string, EndpointDefinition>;
}
//# sourceMappingURL=schema.d.ts.map