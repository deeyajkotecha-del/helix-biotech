/**
 * Molecules Service
 *
 * Aggregates drug/molecule information from clinical trials.
 * Builds a molecule database with phase tracking and mechanism identification.
 */
import { Molecule, TrialPhase, Trial } from '../types/schema';
export interface MoleculeSummary {
    id: string;
    name: string;
    aliases: string[];
    type: Molecule['type'];
    mechanism: string | null;
    target: string | null;
    sponsors: string[];
    highestPhase: TrialPhase;
    trialCount: number;
    activeTrialCount: number;
    trialIds: string[];
    leadTrialId: string | null;
    conditions: string[];
}
/**
 * Extract and aggregate molecules from trials
 */
export declare function extractMoleculesFromTrials(trials: Trial[]): MoleculeSummary[];
/**
 * Get molecule by name (searches primary name and aliases)
 */
export declare function getMoleculeByName(molecules: MoleculeSummary[], name: string): MoleculeSummary | null;
/**
 * Search molecules by mechanism
 */
export declare function searchByMechanism(molecules: MoleculeSummary[], mechanism: string): MoleculeSummary[];
/**
 * Search molecules by target
 */
export declare function searchByTarget(molecules: MoleculeSummary[], target: string): MoleculeSummary[];
/**
 * Get molecules for a specific condition
 */
export declare function getMoleculesForCondition(molecules: MoleculeSummary[], condition: string): MoleculeSummary[];
/**
 * Group molecules by mechanism
 */
export declare function groupByMechanism(molecules: MoleculeSummary[]): Record<string, MoleculeSummary[]>;
/**
 * Group molecules by phase
 */
export declare function groupByPhase(molecules: MoleculeSummary[]): Record<TrialPhase, MoleculeSummary[]>;
/**
 * Get top sponsors across molecules
 */
export declare function getTopMoleculeSponsors(molecules: MoleculeSummary[], limit?: number): {
    sponsor: string;
    moleculeCount: number;
    molecules: string[];
}[];
/**
 * Normalize drug name for comparison
 */
export declare function normalizeDrugName(name: string): string;
/**
 * Generate molecule ID from name
 */
export declare function generateMoleculeId(name: string): string;
/**
 * Identify drug type from name/description
 */
export declare function identifyDrugType(name: string, description?: string): Molecule['type'];
/**
 * Infer mechanism of action from name/description
 */
export declare function inferMechanism(name: string, description?: string): string | null;
/**
 * Infer target from name/description
 */
export declare function inferTarget(name: string, description?: string): string | null;
/**
 * Check if intervention is placebo/control
 */
export declare function isControlIntervention(name: string): boolean;
/**
 * Get competitors (same mechanism/target)
 */
export declare function getCompetitors(molecule: MoleculeSummary, allMolecules: MoleculeSummary[]): MoleculeSummary[];
/**
 * Get mechanism landscape
 */
export declare function getMechanismLandscape(molecules: MoleculeSummary[], mechanism: string): {
    molecules: MoleculeSummary[];
    byPhase: Record<TrialPhase, number>;
    leadMolecule: MoleculeSummary | null;
    sponsors: string[];
};
//# sourceMappingURL=molecules.d.ts.map