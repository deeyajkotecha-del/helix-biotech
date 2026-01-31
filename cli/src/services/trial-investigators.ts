/**
 * Clinical Trial Investigators Service
 * Searches ClinicalTrials.gov for trial investigators
 * Uses API: https://clinicaltrials.gov/api/v2/
 */

import axios from 'axios';
import { extractCountry } from './pubmed-authors';

export interface TrialInvestigator {
  name: string;
  firstName: string;
  lastName: string;
  affiliation: string;
  country: string;
  role: 'PI' | 'Study Chair' | 'Study Director';
  trialCount: number;
  trials: TrialInfo[];
}

export interface TrialInfo {
  nctId: string;
  title: string;
  phase: string;
  status: string;
  sponsor: string;
  role: string;
}

interface CTGovResponse {
  studies?: CTGovStudy[];
  totalCount?: number;
}

interface CTGovStudy {
  protocolSection?: {
    identificationModule?: {
      nctId?: string;
      briefTitle?: string;
      officialTitle?: string;
    };
    statusModule?: {
      overallStatus?: string;
    };
    designModule?: {
      phases?: string[];
    };
    sponsorCollaboratorsModule?: {
      leadSponsor?: {
        name?: string;
      };
    };
    contactsLocationsModule?: {
      overallOfficials?: OverallOfficial[];
      locations?: Location[];
    };
  };
}

interface OverallOfficial {
  name?: string;
  affiliation?: string;
  role?: string;
}

interface Location {
  facility?: string;
  city?: string;
  state?: string;
  country?: string;
  contacts?: LocationContact[];
}

interface LocationContact {
  name?: string;
  role?: string;
  email?: string;
  phone?: string;
}

const CTGOV_API_BASE = 'https://clinicaltrials.gov/api/v2';

/**
 * Search ClinicalTrials.gov for investigators working on a specific topic
 */
export async function searchTrialInvestigators(
  query: string,
  maxTrials: number = 100
): Promise<TrialInvestigator[]> {
  try {
    // Search for trials matching the query
    const searchUrl = `${CTGOV_API_BASE}/studies`;
    const response = await axios.get<CTGovResponse>(searchUrl, {
      params: {
        'query.term': query,
        pageSize: Math.min(maxTrials, 100),
        fields: [
          'NCTId',
          'BriefTitle',
          'OfficialTitle',
          'OverallStatus',
          'Phase',
          'LeadSponsorName',
          'OverallOfficialName',
          'OverallOfficialAffiliation',
          'OverallOfficialRole',
          'LocationFacility',
          'LocationCity',
          'LocationState',
          'LocationCountry',
          'LocationContactName',
          'LocationContactRole',
          'LocationContactEMail',
        ].join(','),
      },
      timeout: 20000,
    });

    const studies = response.data?.studies || [];
    if (studies.length === 0) {
      return [];
    }

    // Aggregate investigators
    const investigatorMap = new Map<string, TrialInvestigator>();

    for (const study of studies) {
      const protocol = study.protocolSection;
      if (!protocol) continue;

      const nctId = protocol.identificationModule?.nctId || '';
      const title = protocol.identificationModule?.briefTitle ||
                    protocol.identificationModule?.officialTitle || '';
      const status = protocol.statusModule?.overallStatus || '';
      const phases = protocol.designModule?.phases || [];
      const phase = phases.length > 0 ? phases.join('/') : 'N/A';
      const sponsor = protocol.sponsorCollaboratorsModule?.leadSponsor?.name || '';

      const trialInfo: TrialInfo = {
        nctId,
        title,
        phase,
        status,
        sponsor,
        role: '',
      };

      // Process overall officials
      const officials = protocol.contactsLocationsModule?.overallOfficials || [];
      for (const official of officials) {
        if (!official.name) continue;

        const { firstName, lastName } = parseNameParts(official.name);
        const key = normalizeInvestigatorName(lastName, firstName);
        const role = mapRole(official.role || '');

        if (investigatorMap.has(key)) {
          const existing = investigatorMap.get(key)!;
          existing.trialCount++;
          existing.trials.push({ ...trialInfo, role: official.role || '' });
          // Update affiliation if better
          if (official.affiliation && (!existing.affiliation || existing.affiliation.length < official.affiliation.length)) {
            existing.affiliation = official.affiliation;
            existing.country = extractCountry(official.affiliation);
          }
        } else {
          investigatorMap.set(key, {
            name: official.name,
            firstName,
            lastName,
            affiliation: official.affiliation || '',
            country: extractCountry(official.affiliation || ''),
            role,
            trialCount: 1,
            trials: [{ ...trialInfo, role: official.role || '' }],
          });
        }
      }

      // Process location contacts (often includes site PIs)
      const locations = protocol.contactsLocationsModule?.locations || [];
      for (const location of locations) {
        const contacts = location.contacts || [];
        for (const contact of contacts) {
          if (!contact.name || !contact.role) continue;
          // Only include Principal Investigators
          if (!contact.role.toLowerCase().includes('principal investigator')) continue;

          const { firstName, lastName } = parseNameParts(contact.name);
          const key = normalizeInvestigatorName(lastName, firstName);

          // Construct affiliation from location data
          const affiliationParts = [
            location.facility,
            location.city,
            location.state,
            location.country,
          ].filter(Boolean);
          const affiliation = affiliationParts.join(', ');
          const country = mapCountryName(location.country || '') || extractCountry(affiliation);

          if (investigatorMap.has(key)) {
            const existing = investigatorMap.get(key)!;
            // Check if this trial is already counted
            if (!existing.trials.some(t => t.nctId === nctId)) {
              existing.trialCount++;
              existing.trials.push({ ...trialInfo, role: 'Site PI' });
            }
            if (!existing.country && country) {
              existing.country = country;
            }
            if (!existing.affiliation && affiliation) {
              existing.affiliation = affiliation;
            }
          } else {
            investigatorMap.set(key, {
              name: contact.name,
              firstName,
              lastName,
              affiliation,
              country,
              role: 'PI',
              trialCount: 1,
              trials: [{ ...trialInfo, role: 'Site PI' }],
            });
          }
        }
      }
    }

    // Sort by trial count and return top 50
    const sortedInvestigators = Array.from(investigatorMap.values())
      .sort((a, b) => b.trialCount - a.trialCount)
      .slice(0, 50);

    return sortedInvestigators;
  } catch (error) {
    console.error('ClinicalTrials.gov search error:', error);
    return [];
  }
}

/**
 * Parse name into first and last name parts
 */
function parseNameParts(fullName: string): { firstName: string; lastName: string } {
  // Handle "Last, First" format
  if (fullName.includes(',')) {
    const parts = fullName.split(',').map(p => p.trim());
    return {
      lastName: parts[0] || '',
      firstName: parts.slice(1).join(' ').replace(/,\s*M\.?D\.?.*$/i, '').trim(),
    };
  }

  // Handle "First Last" format
  const parts = fullName.replace(/,?\s*M\.?D\.?.*$/i, '').trim().split(/\s+/);
  if (parts.length === 1) {
    return { firstName: '', lastName: parts[0] };
  }

  return {
    firstName: parts.slice(0, -1).join(' '),
    lastName: parts[parts.length - 1],
  };
}

/**
 * Normalize investigator name for deduplication
 */
function normalizeInvestigatorName(lastName: string, firstName: string): string {
  const normalizedLast = lastName.toLowerCase().replace(/[^a-z]/g, '');
  const normalizedFirst = firstName.toLowerCase().replace(/[^a-z]/g, '');
  return `${normalizedLast}_${normalizedFirst.charAt(0) || ''}`;
}

/**
 * Map ClinicalTrials.gov role to standard role
 */
function mapRole(role: string): 'PI' | 'Study Chair' | 'Study Director' {
  const roleLower = role.toLowerCase();
  if (roleLower.includes('principal investigator') || roleLower.includes('pi')) {
    return 'PI';
  }
  if (roleLower.includes('chair')) {
    return 'Study Chair';
  }
  if (roleLower.includes('director')) {
    return 'Study Director';
  }
  return 'PI';
}

/**
 * Map full country name to country code
 */
function mapCountryName(country: string): string {
  const countryMap: Record<string, string> = {
    'united states': 'US',
    'usa': 'US',
    'china': 'CN',
    'united kingdom': 'UK',
    'germany': 'DE',
    'france': 'FR',
    'japan': 'JP',
    'south korea': 'KR',
    'korea, republic of': 'KR',
    'canada': 'CA',
    'australia': 'AU',
    'italy': 'IT',
    'spain': 'ES',
    'netherlands': 'NL',
    'switzerland': 'CH',
    'sweden': 'SE',
    'brazil': 'BR',
    'india': 'IN',
    'taiwan': 'TW',
    'israel': 'IL',
    'belgium': 'BE',
    'austria': 'AT',
    'poland': 'PL',
    'denmark': 'DK',
    'norway': 'NO',
    'finland': 'FI',
    'ireland': 'IE',
    'portugal': 'PT',
    'greece': 'GR',
    'czech republic': 'CZ',
    'czechia': 'CZ',
    'hungary': 'HU',
    'romania': 'RO',
    'russia': 'RU',
    'russian federation': 'RU',
    'turkey': 'TR',
    'mexico': 'MX',
    'argentina': 'AR',
    'chile': 'CL',
    'colombia': 'CO',
    'peru': 'PE',
    'singapore': 'SG',
    'malaysia': 'MY',
    'thailand': 'TH',
    'philippines': 'PH',
    'indonesia': 'ID',
    'vietnam': 'VN',
    'hong kong': 'HK',
    'new zealand': 'NZ',
    'south africa': 'ZA',
    'egypt': 'EG',
    'saudi arabia': 'SA',
    'united arab emirates': 'AE',
  };

  return countryMap[country.toLowerCase()] || '';
}
