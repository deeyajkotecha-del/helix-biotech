"use strict";
/**
 * Molecules Service
 *
 * Aggregates drug/molecule information from clinical trials.
 * Builds a molecule database with phase tracking and mechanism identification.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.extractMoleculesFromTrials = extractMoleculesFromTrials;
exports.getMoleculeByName = getMoleculeByName;
exports.searchByMechanism = searchByMechanism;
exports.searchByTarget = searchByTarget;
exports.getMoleculesForCondition = getMoleculesForCondition;
exports.groupByMechanism = groupByMechanism;
exports.groupByPhase = groupByPhase;
exports.getTopMoleculeSponsors = getTopMoleculeSponsors;
exports.normalizeDrugName = normalizeDrugName;
exports.generateMoleculeId = generateMoleculeId;
exports.identifyDrugType = identifyDrugType;
exports.inferMechanism = inferMechanism;
exports.inferTarget = inferTarget;
exports.isControlIntervention = isControlIntervention;
exports.getCompetitors = getCompetitors;
exports.getMechanismLandscape = getMechanismLandscape;
// ============================================
// Main Functions
// ============================================
/**
 * Extract and aggregate molecules from trials
 */
function extractMoleculesFromTrials(trials) {
    const moleculeMap = new Map();
    for (const trial of trials) {
        for (const intervention of trial.interventions) {
            // Skip non-drug interventions
            if (!isDrugIntervention(intervention))
                continue;
            // Skip placebo/control
            if (isControlIntervention(intervention.name))
                continue;
            // Normalize the name
            const normalizedName = normalizeDrugName(intervention.name);
            if (!normalizedName || normalizedName.length < 2)
                continue;
            const id = generateMoleculeId(normalizedName);
            // Get or create molecule entry
            let molecule = moleculeMap.get(id);
            if (!molecule) {
                molecule = {
                    id,
                    name: intervention.name, // Keep original case
                    aliases: [],
                    type: identifyDrugType(intervention.name),
                    mechanism: inferMechanism(intervention.name, intervention.description),
                    target: inferTarget(intervention.name, intervention.description),
                    sponsors: [],
                    highestPhase: trial.phase,
                    trialCount: 0,
                    activeTrialCount: 0,
                    trialIds: [],
                    leadTrialId: null,
                    conditions: [],
                };
                moleculeMap.set(id, molecule);
            }
            // Update molecule data
            molecule.trialCount++;
            molecule.trialIds.push(trial.nctId);
            // Add alias if different from primary name
            if (intervention.name !== molecule.name && !molecule.aliases.includes(intervention.name)) {
                molecule.aliases.push(intervention.name);
            }
            // Add other names as aliases
            if (intervention.otherNames) {
                for (const alias of intervention.otherNames) {
                    if (alias && !molecule.aliases.includes(alias) && alias !== molecule.name) {
                        molecule.aliases.push(alias);
                    }
                }
            }
            // Update sponsor
            if (trial.leadSponsor.name && !molecule.sponsors.includes(trial.leadSponsor.name)) {
                molecule.sponsors.push(trial.leadSponsor.name);
            }
            // Update highest phase
            if (getPhaseRank(trial.phase) > getPhaseRank(molecule.highestPhase)) {
                molecule.highestPhase = trial.phase;
                molecule.leadTrialId = trial.nctId;
            }
            // Track active trials
            if (isActiveStatus(trial.status)) {
                molecule.activeTrialCount++;
            }
            // Add conditions
            for (const condition of trial.conditions) {
                if (!molecule.conditions.includes(condition)) {
                    molecule.conditions.push(condition);
                }
            }
            // Try to infer mechanism from trial description if not already set
            if (!molecule.mechanism && trial.briefTitle) {
                const inferred = inferMechanism(trial.briefTitle, intervention.description);
                if (inferred) {
                    molecule.mechanism = inferred;
                }
            }
        }
    }
    // Sort by highest phase then trial count
    return Array.from(moleculeMap.values())
        .sort((a, b) => {
        const phaseDiff = getPhaseRank(b.highestPhase) - getPhaseRank(a.highestPhase);
        if (phaseDiff !== 0)
            return phaseDiff;
        return b.trialCount - a.trialCount;
    });
}
/**
 * Get molecule by name (searches primary name and aliases)
 */
function getMoleculeByName(molecules, name) {
    const normalized = normalizeDrugName(name);
    for (const mol of molecules) {
        // Check primary name
        if (normalizeDrugName(mol.name) === normalized) {
            return mol;
        }
        // Check aliases
        for (const alias of mol.aliases) {
            if (normalizeDrugName(alias) === normalized) {
                return mol;
            }
        }
    }
    return null;
}
/**
 * Search molecules by mechanism
 */
function searchByMechanism(molecules, mechanism) {
    const searchTerm = mechanism.toLowerCase();
    return molecules.filter(m => m.mechanism && m.mechanism.toLowerCase().includes(searchTerm));
}
/**
 * Search molecules by target
 */
function searchByTarget(molecules, target) {
    const searchTerm = target.toLowerCase();
    return molecules.filter(m => m.target && m.target.toLowerCase().includes(searchTerm));
}
/**
 * Get molecules for a specific condition
 */
function getMoleculesForCondition(molecules, condition) {
    const searchTerm = condition.toLowerCase();
    return molecules.filter(m => m.conditions.some(c => c.toLowerCase().includes(searchTerm)));
}
/**
 * Group molecules by mechanism
 */
function groupByMechanism(molecules) {
    const grouped = {};
    for (const mol of molecules) {
        const mechanism = mol.mechanism || 'Unknown';
        if (!grouped[mechanism]) {
            grouped[mechanism] = [];
        }
        grouped[mechanism].push(mol);
    }
    return grouped;
}
/**
 * Group molecules by phase
 */
function groupByPhase(molecules) {
    const grouped = {};
    for (const mol of molecules) {
        if (!grouped[mol.highestPhase]) {
            grouped[mol.highestPhase] = [];
        }
        grouped[mol.highestPhase].push(mol);
    }
    return grouped;
}
/**
 * Get top sponsors across molecules
 */
function getTopMoleculeSponsors(molecules, limit = 10) {
    const sponsorCounts = {};
    for (const mol of molecules) {
        for (const sponsor of mol.sponsors) {
            if (!sponsorCounts[sponsor]) {
                sponsorCounts[sponsor] = { count: 0, molecules: [] };
            }
            sponsorCounts[sponsor].count++;
            sponsorCounts[sponsor].molecules.push(mol.name);
        }
    }
    return Object.entries(sponsorCounts)
        .map(([sponsor, data]) => ({
        sponsor,
        moleculeCount: data.count,
        molecules: data.molecules,
    }))
        .sort((a, b) => b.moleculeCount - a.moleculeCount)
        .slice(0, limit);
}
// ============================================
// Name Normalization
// ============================================
/**
 * Normalize drug name for comparison
 */
function normalizeDrugName(name) {
    return name
        .toLowerCase()
        .replace(/\s*\([^)]*\)/g, '') // Remove parenthetical info
        .replace(/\s*\[[^\]]*\]/g, '') // Remove bracketed info
        .replace(/\s+/g, ' ')
        .replace(/[®™©]/g, '') // Remove trademark symbols
        .trim();
}
/**
 * Generate molecule ID from name
 */
function generateMoleculeId(name) {
    return normalizeDrugName(name)
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '');
}
// ============================================
// Type Identification
// ============================================
/**
 * Identify drug type from name/description
 */
function identifyDrugType(name, description) {
    const text = (name + ' ' + (description || '')).toLowerCase();
    // Biologics (monoclonal antibodies)
    if (/-mab$/.test(text) || /umab|zumab|ximab|mumab/.test(text)) {
        return 'Biologic';
    }
    // ADCs
    if (/adc|antibody.drug.conjugate|vedotin|mafodotin|ozogamicin/.test(text)) {
        return 'Biologic';
    }
    // Cell therapies
    if (/car-t|car t|cart|cell therap|chimeric antigen|autologous|tcr/.test(text)) {
        return 'Cell Therapy';
    }
    // Gene therapies
    if (/gene therap|aav|adeno.associated|lentivir|\-vec$/.test(text)) {
        return 'Gene Therapy';
    }
    // Oligonucleotides
    if (/sirna|antisense|oligonucleotide|aso|\-sen$|mrna/.test(text)) {
        return 'Oligonucleotide';
    }
    // Vaccines
    if (/vaccine|vax|immunization/.test(text)) {
        return 'Vaccine';
    }
    // Small molecules (kinase inhibitors, etc.)
    if (/-nib$|tinib|ciclib|rafenib|lisib/.test(text)) {
        return 'Small Molecule';
    }
    // Default to small molecule
    return 'Small Molecule';
}
/**
 * Infer mechanism of action from name/description
 */
function inferMechanism(name, description) {
    const text = (name + ' ' + (description || '')).toLowerCase();
    // Cytokine inhibitors
    if (/il-?17|secukinumab|ixekizumab|brodalumab/.test(text))
        return 'IL-17 Inhibitor';
    if (/il-?23|guselkumab|risankizumab|tildrakizumab|mirikizumab/.test(text))
        return 'IL-23 Inhibitor';
    if (/il-?6|tocilizumab|sarilumab/.test(text))
        return 'IL-6 Inhibitor';
    if (/il-?4|il-?13|dupilumab|lebrikizumab|tralokinumab/.test(text))
        return 'IL-4/IL-13 Inhibitor';
    if (/il-?1[^0-9]|anakinra|canakinumab|rilonacept/.test(text))
        return 'IL-1 Inhibitor';
    // TNF inhibitors
    if (/tnf|adalimumab|infliximab|etanercept|certolizumab|golimumab/.test(text))
        return 'TNF Inhibitor';
    // JAK inhibitors
    if (/jak|tofacitinib|baricitinib|upadacitinib|filgotinib|ruxolitinib/.test(text))
        return 'JAK Inhibitor';
    // S1P modulators
    if (/s1p|sphingosine|ozanimod|etrasimod|ponesimod|siponimod/.test(text))
        return 'S1P Receptor Modulator';
    // Integrin inhibitors
    if (/integrin|vedolizumab|natalizumab|etrolizumab/.test(text))
        return 'Integrin Inhibitor';
    // PDE4 inhibitors
    if (/pde4|apremilast|roflumilast/.test(text))
        return 'PDE4 Inhibitor';
    // Checkpoint inhibitors
    if (/pd-?1|pembrolizumab|nivolumab|cemiplimab|dostarlimab/.test(text))
        return 'PD-1 Inhibitor';
    if (/pd-?l1|atezolizumab|durvalumab|avelumab/.test(text))
        return 'PD-L1 Inhibitor';
    if (/ctla-?4|ipilimumab|tremelimumab/.test(text))
        return 'CTLA-4 Inhibitor';
    if (/lag-?3/.test(text))
        return 'LAG-3 Inhibitor';
    if (/tim-?3/.test(text))
        return 'TIM-3 Inhibitor';
    if (/tigit/.test(text))
        return 'TIGIT Inhibitor';
    // Growth factor inhibitors
    if (/vegf|bevacizumab|ramucirumab|aflibercept/.test(text))
        return 'VEGF Inhibitor';
    if (/egfr|cetuximab|panitumumab|necitumumab/.test(text))
        return 'EGFR Inhibitor';
    if (/her2|trastuzumab|pertuzumab/.test(text))
        return 'HER2 Inhibitor';
    // Kinase inhibitors
    if (/bcr.?abl|imatinib|dasatinib|nilotinib|bosutinib|ponatinib/.test(text))
        return 'BCR-ABL Inhibitor';
    if (/braf|vemurafenib|dabrafenib|encorafenib/.test(text))
        return 'BRAF Inhibitor';
    if (/mek|trametinib|cobimetinib|binimetinib/.test(text))
        return 'MEK Inhibitor';
    if (/cdk|palbociclib|ribociclib|abemaciclib/.test(text))
        return 'CDK Inhibitor';
    if (/btk|ibrutinib|acalabrutinib|zanubrutinib/.test(text))
        return 'BTK Inhibitor';
    if (/alk|crizotinib|alectinib|ceritinib|lorlatinib|brigatinib/.test(text))
        return 'ALK Inhibitor';
    if (/flt3|midostaurin|gilteritinib|quizartinib/.test(text))
        return 'FLT3 Inhibitor';
    // Other mechanisms
    if (/parp|olaparib|niraparib|rucaparib|talazoparib/.test(text))
        return 'PARP Inhibitor';
    if (/proteasome|bortezomib|carfilzomib|ixazomib/.test(text))
        return 'Proteasome Inhibitor';
    if (/bcl-?2|venetoclax/.test(text))
        return 'BCL-2 Inhibitor';
    if (/hdac|vorinostat|romidepsin|panobinostat/.test(text))
        return 'HDAC Inhibitor';
    if (/cd20|rituximab|obinutuzumab|ofatumumab|ocrelizumab/.test(text))
        return 'Anti-CD20';
    if (/cd19|blinatumomab/.test(text))
        return 'Anti-CD19';
    if (/cd38|daratumumab|isatuximab/.test(text))
        return 'Anti-CD38';
    if (/bcma/.test(text))
        return 'Anti-BCMA';
    if (/tgf.?beta|tgfb/.test(text))
        return 'TGF-beta Inhibitor';
    // CAR-T specific
    if (/car-?t|chimeric antigen/.test(text)) {
        if (/cd19/.test(text))
            return 'CD19 CAR-T';
        if (/bcma/.test(text))
            return 'BCMA CAR-T';
        return 'CAR-T Cell Therapy';
    }
    // Gene therapy
    if (/gene therap|aav/.test(text))
        return 'Gene Therapy';
    // Generic antibody
    if (/-mab$/.test(name.toLowerCase()))
        return 'Monoclonal Antibody';
    return null;
}
/**
 * Infer target from name/description
 */
function inferTarget(name, description) {
    const text = (name + ' ' + (description || '')).toLowerCase();
    // Direct target mentions
    const targetPatterns = [
        [/il-?17/i, 'IL-17'],
        [/il-?23/i, 'IL-23'],
        [/il-?6/i, 'IL-6'],
        [/il-?4/i, 'IL-4'],
        [/il-?13/i, 'IL-13'],
        [/il-?1[^0-9]/i, 'IL-1'],
        [/tnf-?[aα]/i, 'TNF-alpha'],
        [/jak[123]?/i, 'JAK'],
        [/s1p/i, 'S1P'],
        [/α4β7|alpha4beta7|integrin/i, 'α4β7 Integrin'],
        [/pd-?1/i, 'PD-1'],
        [/pd-?l1/i, 'PD-L1'],
        [/ctla-?4/i, 'CTLA-4'],
        [/vegf/i, 'VEGF'],
        [/egfr/i, 'EGFR'],
        [/her2|erbb2/i, 'HER2'],
        [/bcr-?abl/i, 'BCR-ABL'],
        [/braf/i, 'BRAF'],
        [/mek/i, 'MEK'],
        [/cdk[46]/i, 'CDK4/6'],
        [/btk/i, 'BTK'],
        [/alk/i, 'ALK'],
        [/flt3/i, 'FLT3'],
        [/parp/i, 'PARP'],
        [/bcl-?2/i, 'BCL-2'],
        [/cd20/i, 'CD20'],
        [/cd19/i, 'CD19'],
        [/cd38/i, 'CD38'],
        [/bcma/i, 'BCMA'],
    ];
    for (const [pattern, target] of targetPatterns) {
        if (pattern.test(text)) {
            return target;
        }
    }
    return null;
}
// ============================================
// Helper Functions
// ============================================
/**
 * Check if intervention is a drug/biologic
 */
function isDrugIntervention(intervention) {
    return intervention.type === 'Drug' || intervention.type === 'Biological';
}
/**
 * Check if intervention is placebo/control
 */
function isControlIntervention(name) {
    const controls = [
        'placebo', 'standard of care', 'standard care', 'soc',
        'best supportive care', 'bsc', 'observation', 'no intervention',
        'usual care', 'control', 'sham', 'active comparator', 'comparator',
        'vehicle', 'saline', 'normal saline', 'matching placebo',
    ];
    const lower = name.toLowerCase();
    return controls.some(c => lower.includes(c));
}
/**
 * Check if trial status is active
 */
function isActiveStatus(status) {
    const active = ['recruiting', 'active', 'enrolling', 'not yet recruiting'];
    return active.some(a => status.toLowerCase().includes(a));
}
/**
 * Get numeric rank for phase (for sorting)
 */
function getPhaseRank(phase) {
    const ranks = {
        'Phase 4': 100,
        'Phase 3': 80,
        'Phase 2/3': 70,
        'Phase 2': 60,
        'Phase 1/2': 50,
        'Phase 1': 40,
        'Preclinical': 20,
        'Not Applicable': 0,
    };
    return ranks[phase] || 0;
}
// ============================================
// Competitive Analysis
// ============================================
/**
 * Get competitors (same mechanism/target)
 */
function getCompetitors(molecule, allMolecules) {
    return allMolecules.filter(m => {
        if (m.id === molecule.id)
            return false;
        // Same mechanism
        if (molecule.mechanism && m.mechanism === molecule.mechanism)
            return true;
        // Same target
        if (molecule.target && m.target === molecule.target)
            return true;
        return false;
    });
}
/**
 * Get mechanism landscape
 */
function getMechanismLandscape(molecules, mechanism) {
    const filtered = searchByMechanism(molecules, mechanism);
    const byPhase = {};
    const sponsors = new Set();
    let leadMolecule = null;
    for (const mol of filtered) {
        byPhase[mol.highestPhase] = (byPhase[mol.highestPhase] || 0) + 1;
        mol.sponsors.forEach(s => sponsors.add(s));
        if (!leadMolecule || getPhaseRank(mol.highestPhase) > getPhaseRank(leadMolecule.highestPhase)) {
            leadMolecule = mol;
        }
    }
    return {
        molecules: filtered,
        byPhase: byPhase,
        leadMolecule,
        sponsors: Array.from(sponsors),
    };
}
//# sourceMappingURL=molecules.js.map