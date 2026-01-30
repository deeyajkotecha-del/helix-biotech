/**
 * Company and Catalyst type definitions
 */

export interface Catalyst {
  event: string;           // "SHASTA-3/4 Phase 3 data"
  date: string;            // "2026-06-15" (ISO format) or "2026-Q3" for quarterly estimates
  status: 'upcoming' | 'completed' | 'delayed';
  outcome?: string;        // "Positive - met primary endpoint" (for completed)
  source?: string;         // Link to press release
  importance?: 'high' | 'medium' | 'low';
  drug?: string;           // Associated drug/asset name
}

export interface CompanyData {
  ticker: string;
  name: string;
  platform: string;
  description: string;
  marketCap: string;
  pipelineCount: number | string;
  phase3Count: number;
  approvedCount?: number;
  therapeuticAreas: string[];
  catalysts: Catalyst[];
  irUrl?: string;
  website?: string;
}

// All 8 featured companies with accurate catalyst data
export const FEATURED_COMPANIES: CompanyData[] = [
  {
    ticker: 'ARWR',
    name: 'Arrowhead Pharmaceuticals',
    platform: 'RNAi',
    description: 'Leader in RNAi therapeutics with TRiM platform enabling targeted delivery to liver, lung, muscle, and CNS. First approved drug (Plozasiran) in Dec 2024.',
    marketCap: '$4.2B',
    pipelineCount: 15,
    phase3Count: 3,
    approvedCount: 1,
    therapeuticAreas: ['Cardiometabolic', 'CNS', 'Pulmonary'],
    irUrl: 'https://ir.arrowheadpharma.com',
    catalysts: [
      // Completed catalysts
      {
        event: 'Plozasiran FDA approval (FCS)',
        date: '2024-12-19',
        status: 'completed',
        outcome: 'Approved - REDEMPLO for Familial Chylomicronemia Syndrome',
        source: 'https://ir.arrowheadpharma.com/news-releases',
        importance: 'high',
        drug: 'Plozasiran'
      },
      {
        event: 'PALISADE Phase 3 data (FCS)',
        date: '2025-08-29',
        status: 'completed',
        outcome: 'Positive - 80% TG reduction at Week 10',
        source: 'https://ir.arrowheadpharma.com',
        importance: 'high',
        drug: 'Plozasiran'
      },
      {
        event: 'ARCHES-2 Phase 2b data (Zodasiran)',
        date: '2025-08-31',
        status: 'completed',
        outcome: 'Positive - 60% LDL reduction, 73% TG reduction',
        source: 'https://ir.arrowheadpharma.com',
        importance: 'high',
        drug: 'Zodasiran'
      },
      {
        event: 'ARO-INHBE/ALK7 interim obesity data',
        date: '2026-01-06',
        status: 'completed',
        outcome: 'Positive - Weight loss demonstrated in diabetic obese patients',
        source: 'https://ir.arrowheadpharma.com',
        importance: 'medium',
        drug: 'ARO-INHBE/ARO-ALK7'
      },
      {
        event: 'SHASTA-3/4 enrollment complete',
        date: '2025-06-23',
        status: 'completed',
        outcome: 'Completed - ~2,200 patients enrolled across 24 countries',
        source: 'https://ir.arrowheadpharma.com',
        importance: 'medium',
        drug: 'Plozasiran'
      },
      // Upcoming catalysts
      {
        event: 'ARO-INHBE/ALK7 full obesity cohort data',
        date: '2026-06-30',
        status: 'upcoming',
        importance: 'high',
        drug: 'ARO-INHBE/ARO-ALK7'
      },
      {
        event: 'SHASTA-3/4 Phase 3 topline data (sHTG)',
        date: '2026-09-15',
        status: 'upcoming',
        importance: 'high',
        drug: 'Plozasiran'
      },
      {
        event: 'Plozasiran sNDA submission (sHTG)',
        date: '2026-12-31',
        status: 'upcoming',
        importance: 'high',
        drug: 'Plozasiran'
      },
      {
        event: 'YOSEMITE Phase 3 progress (Zodasiran HoFH)',
        date: '2026-06-30',
        status: 'upcoming',
        importance: 'medium',
        drug: 'Zodasiran'
      },
      {
        event: 'ARO-MAPT Phase 1 CNS data',
        date: '2026-12-31',
        status: 'upcoming',
        importance: 'medium',
        drug: 'ARO-MAPT'
      }
    ]
  },
  {
    ticker: 'ALNY',
    name: 'Alnylam Pharmaceuticals',
    platform: 'RNAi',
    description: 'Pioneer in RNAi therapeutics with 5 approved drugs including Onpattro and Amvuttra. GalNAc conjugate platform for liver-targeted delivery.',
    marketCap: '$28.5B',
    pipelineCount: 12,
    phase3Count: 3,
    approvedCount: 5,
    therapeuticAreas: ['Rare Disease', 'Cardiometabolic', 'CNS'],
    irUrl: 'https://investors.alnylam.com',
    catalysts: [
      // Completed catalysts
      {
        event: 'KARDIA-2 Phase 2 data (Zilebesiran)',
        date: '2024-03-05',
        status: 'completed',
        outcome: 'Positive - Clinically significant BP reduction',
        importance: 'high',
        drug: 'Zilebesiran'
      },
      {
        event: 'KARDIA-3 Phase 2 data at ESC 2025',
        date: '2025-08-30',
        status: 'completed',
        outcome: 'Positive - Clinically meaningful BP reductions at month 3',
        importance: 'high',
        drug: 'Zilebesiran'
      },
      {
        event: 'ZENITH Phase 3 CVOT first patient dosed',
        date: '2025-11-15',
        status: 'completed',
        outcome: 'Initiated - 11,000 patient cardiovascular outcomes trial',
        importance: 'high',
        drug: 'Zilebesiran'
      },
      {
        event: 'Roche partnership for Zilebesiran',
        date: '2025-08-30',
        status: 'completed',
        outcome: 'Completed - Co-development and co-commercialization deal',
        importance: 'high',
        drug: 'Zilebesiran'
      },
      // Upcoming catalysts
      {
        event: 'Vutrisiran HELIOS-B ATTR-CM data',
        date: '2026-06-30',
        status: 'upcoming',
        importance: 'high',
        drug: 'Vutrisiran'
      },
      {
        event: 'ALN-APP Phase 1 data (Alzheimer\'s)',
        date: '2026-12-31',
        status: 'upcoming',
        importance: 'medium',
        drug: 'ALN-APP'
      },
      {
        event: 'ZENITH Phase 3 enrollment update',
        date: '2026-06-30',
        status: 'upcoming',
        importance: 'medium',
        drug: 'Zilebesiran'
      }
    ]
  },
  {
    ticker: 'IONS',
    name: 'Ionis Pharmaceuticals',
    platform: 'Antisense',
    description: 'Leading antisense technology company with 4 approved drugs. LICA platform enables next-gen delivery. Major partnerships with Biogen, AZ, Roche.',
    marketCap: '$7.8B',
    pipelineCount: '40+',
    phase3Count: 5,
    approvedCount: 4,
    therapeuticAreas: ['Rare Disease', 'CNS', 'Cardiometabolic'],
    irUrl: 'https://ir.ionis.com',
    catalysts: [
      // Completed catalysts
      {
        event: 'Olezarsen FDA approval (FCS)',
        date: '2024-12-19',
        status: 'completed',
        outcome: 'Approved - TRYNGOLZA for Familial Chylomicronemia Syndrome',
        importance: 'high',
        drug: 'Olezarsen'
      },
      {
        event: 'CORE/CORE2 Phase 3 enrollment complete (sHTG)',
        date: '2025-06-30',
        status: 'completed',
        outcome: 'Completed - Over 1,000 sHTG patients enrolled',
        importance: 'medium',
        drug: 'Olezarsen'
      },
      {
        event: 'ESSENCE Phase 3 topline data (sHTG)',
        date: '2025-06-15',
        status: 'completed',
        outcome: 'Positive - Supportive study met endpoints',
        importance: 'high',
        drug: 'Olezarsen'
      },
      {
        event: 'CORE/CORE2 Phase 3 topline data (sHTG)',
        date: '2025-09-30',
        status: 'completed',
        outcome: 'Positive - Pivotal studies met endpoints',
        importance: 'high',
        drug: 'Olezarsen'
      },
      // Upcoming catalysts
      {
        event: 'Olezarsen sNDA submission (sHTG)',
        date: '2026-03-31',
        status: 'upcoming',
        importance: 'high',
        drug: 'Olezarsen'
      },
      {
        event: 'Olezarsen FDA approval decision (sHTG)',
        date: '2026-12-31',
        status: 'upcoming',
        importance: 'high',
        drug: 'Olezarsen'
      },
      {
        event: 'Zilganersen BLA submission (Alexander disease)',
        date: '2026-06-30',
        status: 'upcoming',
        importance: 'high',
        drug: 'Zilganersen'
      },
      {
        event: 'CARDIO-TTRansform Phase 3 data (Eplontersen ATTR-CM)',
        date: '2026-12-31',
        status: 'upcoming',
        importance: 'high',
        drug: 'Eplontersen'
      }
    ]
  },
  {
    ticker: 'XENE',
    name: 'Xenon Pharmaceuticals',
    platform: 'Ion Channel',
    description: 'Focused on ion channel drug discovery for epilepsy and pain. Lead asset azetukalner (XEN1101) in Phase 3 for focal epilepsy with breakthrough therapy designation.',
    marketCap: '$3.1B',
    pipelineCount: 4,
    phase3Count: 2,
    therapeuticAreas: ['CNS', 'Epilepsy', 'Pain'],
    irUrl: 'https://investor.xenon-pharma.com',
    catalysts: [
      // Completed catalysts
      {
        event: 'X-TOLE2 Phase 3 enrollment complete',
        date: '2025-09-30',
        status: 'completed',
        outcome: 'Completed - 380 patients randomized',
        importance: 'high',
        drug: 'Azetukalner'
      },
      {
        event: 'AES 2025 - 48-month OLE data',
        date: '2025-12-06',
        status: 'completed',
        outcome: 'Positive - >90% seizure frequency reduction at 48 months',
        importance: 'medium',
        drug: 'Azetukalner'
      },
      // Upcoming catalysts
      {
        event: 'X-TOLE2 Phase 3 topline data (focal epilepsy)',
        date: '2026-03-31',
        status: 'upcoming',
        importance: 'high',
        drug: 'Azetukalner'
      },
      {
        event: 'X-NOVA2 Phase 3 progress (MDD)',
        date: '2026-08-31',
        status: 'upcoming',
        importance: 'medium',
        drug: 'Azetukalner'
      },
      {
        event: 'X-TOLE3 Phase 3 topline data (focal epilepsy)',
        date: '2026-10-31',
        status: 'upcoming',
        importance: 'high',
        drug: 'Azetukalner'
      },
      {
        event: 'NDA submission (focal epilepsy)',
        date: '2026-12-31',
        status: 'upcoming',
        importance: 'high',
        drug: 'Azetukalner'
      }
    ]
  },
  {
    ticker: 'MLTX',
    name: 'MoonLake Immunotherapeutics',
    platform: 'Antibody',
    description: 'Developing sonelokimab, a tri-specific nanobody targeting IL-17A/F for psoriatic diseases. Phase 3 programs in HS, PsA, and axSpA.',
    marketCap: '$4.8B',
    pipelineCount: 1,
    phase3Count: 3,
    therapeuticAreas: ['Immunology', 'Dermatology'],
    irUrl: 'https://ir.moonlaketx.com',
    catalysts: [
      // Completed catalysts
      {
        event: 'VELA Phase 3 Week 16 data (HS)',
        date: '2025-09-15',
        status: 'completed',
        outcome: 'Mixed - VELA-1 met endpoints; VELA-2 narrowly missed composite primary',
        importance: 'high',
        drug: 'Sonelokimab'
      },
      {
        event: 'IZAR Phase 3 initiation (PsA)',
        date: '2025-06-30',
        status: 'completed',
        outcome: 'Initiated - IZAR-1 and IZAR-2 studies started',
        importance: 'high',
        drug: 'Sonelokimab'
      },
      // Upcoming catalysts
      {
        event: 'S-OLARIS Phase 2 data (axSpA)',
        date: '2026-03-31',
        status: 'upcoming',
        importance: 'medium',
        drug: 'Sonelokimab'
      },
      {
        event: 'IZAR-1/IZAR-2 Phase 3 primary endpoint (PsA)',
        date: '2026-06-30',
        status: 'upcoming',
        importance: 'high',
        drug: 'Sonelokimab'
      },
      {
        event: 'VELA-TEEN Phase 3 data (adolescent HS)',
        date: '2026-06-30',
        status: 'upcoming',
        importance: 'medium',
        drug: 'Sonelokimab'
      },
      {
        event: 'BLA submission (HS)',
        date: '2026-06-30',
        status: 'upcoming',
        importance: 'high',
        drug: 'Sonelokimab'
      }
    ]
  },
  {
    ticker: 'VKTX',
    name: 'Viking Therapeutics',
    platform: 'Small Molecule',
    description: 'Developing oral GLP-1/GIP agonist VK2735 for obesity/MASH. Best-in-class oral weight loss profile with 14.7% weight loss at 13 weeks.',
    marketCap: '$6.2B',
    pipelineCount: 3,
    phase3Count: 2,
    therapeuticAreas: ['Metabolic', 'Obesity', 'MASH'],
    irUrl: 'https://ir.vikingtherapeutics.com',
    catalysts: [
      // Completed catalysts
      {
        event: 'VENTURE Phase 2 data publication',
        date: '2025-11-06',
        status: 'completed',
        outcome: 'Published - Up to 14.7% weight loss at 13 weeks',
        importance: 'medium',
        drug: 'VK2735'
      },
      {
        event: 'VANQUISH-1 Phase 3 enrollment complete',
        date: '2025-11-15',
        status: 'completed',
        outcome: 'Completed ahead of schedule - ~4,650 patients enrolled',
        importance: 'high',
        drug: 'VK2735'
      },
      {
        event: 'Maintenance dosing study enrollment complete',
        date: '2026-01-15',
        status: 'completed',
        outcome: 'Completed - ~180 adults enrolled',
        importance: 'medium',
        drug: 'VK2735'
      },
      // Upcoming catalysts
      {
        event: 'VANQUISH-2 Phase 3 enrollment complete (T2D)',
        date: '2026-03-31',
        status: 'upcoming',
        importance: 'high',
        drug: 'VK2735'
      },
      {
        event: 'Oral VK2735 Phase 2 data',
        date: '2026-06-30',
        status: 'upcoming',
        importance: 'high',
        drug: 'VK2735 Oral'
      },
      {
        event: 'VANQUISH-1 Phase 3 topline data (52 weeks)',
        date: '2026-12-31',
        status: 'upcoming',
        importance: 'high',
        drug: 'VK2735'
      }
    ]
  },
  {
    ticker: 'IMVT',
    name: 'Immunovant',
    platform: 'Antibody',
    description: 'Developing batoclimab and IMVT-1402, anti-FcRn antibodies for autoimmune diseases. Phase 3 programs in MG, TED, and CIDP.',
    marketCap: '$5.1B',
    pipelineCount: 2,
    phase3Count: 3,
    therapeuticAreas: ['Immunology', 'Rare Disease'],
    irUrl: 'https://www.immunovant.com/investors',
    catalysts: [
      // Completed catalysts
      {
        event: 'Batoclimab Phase 3 MG topline data',
        date: '2025-03-19',
        status: 'completed',
        outcome: 'Positive - Met primary endpoint; 5.6-point MG-ADL improvement at 680mg',
        importance: 'high',
        drug: 'Batoclimab'
      },
      {
        event: 'Batoclimab Phase 2b CIDP topline data',
        date: '2025-03-19',
        status: 'completed',
        outcome: 'Positive - Met primary endpoint',
        importance: 'high',
        drug: 'Batoclimab'
      },
      {
        event: 'IMVT-1402 IND clearance (MG & CIDP)',
        date: '2025-06-30',
        status: 'completed',
        outcome: 'Cleared - FDA cleared INDs for both indications',
        importance: 'high',
        drug: 'IMVT-1402'
      },
      // Upcoming catalysts
      {
        event: 'Batoclimab Phase 3 TED topline data',
        date: '2026-06-30',
        status: 'upcoming',
        importance: 'high',
        drug: 'Batoclimab'
      },
      {
        event: 'IMVT-1402 pivotal study initiation (MG)',
        date: '2026-03-31',
        status: 'upcoming',
        importance: 'high',
        drug: 'IMVT-1402'
      },
      {
        event: 'IMVT-1402 pivotal study initiation (CIDP)',
        date: '2026-06-30',
        status: 'upcoming',
        importance: 'high',
        drug: 'IMVT-1402'
      }
    ]
  },
  {
    ticker: 'RCKT',
    name: 'Rocket Pharmaceuticals',
    platform: 'Gene Therapy',
    description: 'Gene therapy company with KRESLADI for LAD-I pending FDA approval. Pipeline includes FA, PKD, and Danon disease programs.',
    marketCap: '$1.8B',
    pipelineCount: 4,
    phase3Count: 1,
    approvedCount: 0,
    therapeuticAreas: ['Rare Disease', 'Hematology'],
    irUrl: 'https://ir.rocketpharma.com',
    catalysts: [
      // Completed catalysts
      {
        event: 'KRESLADI BLA resubmission accepted',
        date: '2025-10-13',
        status: 'completed',
        outcome: 'Accepted - FDA set PDUFA date for March 28, 2026',
        importance: 'high',
        drug: 'KRESLADI'
      },
      {
        event: 'RP-A501 clinical hold lifted (Danon)',
        date: '2025-09-30',
        status: 'completed',
        outcome: 'Resolved - FDA lifted hold in under 3 months',
        importance: 'high',
        drug: 'RP-A501'
      },
      // Upcoming catalysts
      {
        event: 'KRESLADI PDUFA decision (LAD-I)',
        date: '2026-03-28',
        status: 'upcoming',
        importance: 'high',
        drug: 'KRESLADI'
      },
      {
        event: 'RP-A501 Phase 2 additional patient dosing (Danon)',
        date: '2026-06-30',
        status: 'upcoming',
        importance: 'high',
        drug: 'RP-A501'
      },
      {
        event: 'RP-A601 pivotal Phase 2 initiation (PKP2-ACM)',
        date: '2026-06-30',
        status: 'upcoming',
        importance: 'medium',
        drug: 'RP-A601'
      },
      {
        event: 'KRESLADI commercial launch (if approved)',
        date: '2026-09-30',
        status: 'upcoming',
        importance: 'high',
        drug: 'KRESLADI'
      }
    ]
  }
];

// Helper to get company by ticker
export function getCompanyByTicker(ticker: string): CompanyData | undefined {
  return FEATURED_COMPANIES.find(c => c.ticker.toUpperCase() === ticker.toUpperCase());
}
