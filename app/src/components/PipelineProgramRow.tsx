import { useState } from 'react';
import type { PipelineProgram } from '../types';
import Citation from './Citation';
import ClinicalFigures from './ClinicalFigures';

interface Props {
  program: PipelineProgram;
  sectionName: string;
}

type ExpandedSection = 'satya' | 'mechanism' | 'clinical' | 'competitive' | 'catalysts' | 'figures';

export default function PipelineProgramRow({ program, sectionName }: Props) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Set<ExpandedSection>>(
    new Set(['satya'])
  );

  const toggleSection = (section: ExpandedSection) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  const getStageColor = (stage: string) => {
    const lower = stage.toLowerCase();
    if (lower.includes('approved')) return 'bg-green-100 text-green-800 border-green-200';
    if (lower.includes('phase 3') || lower.includes('phase3')) return 'bg-blue-100 text-blue-800 border-blue-200';
    if (lower.includes('phase 2') || lower.includes('phase2')) return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    if (lower.includes('phase 1') || lower.includes('phase1')) return 'bg-orange-100 text-orange-800 border-orange-200';
    return 'bg-gray-100 text-gray-800 border-gray-200';
  };

  const hasExpandedContent = program.satya_view || program.mechanism ||
    program.clinical_data?.length || program.competitors?.length ||
    program.catalysts?.length || program.figures?.length;

  return (
    <div className="pipeline-row border border-gray-200 rounded-lg overflow-hidden">
      {/* Main Row - Always Visible */}
      <div
        className={`pipeline-row-header p-4 cursor-pointer transition-colors ${
          isExpanded ? 'bg-gray-50' : 'hover:bg-gray-50'
        } ${hasExpandedContent ? '' : 'cursor-default'}`}
        onClick={() => hasExpandedContent && setIsExpanded(!isExpanded)}
      >
        {/* Desktop Grid Layout */}
        <div className="hidden md:grid grid-cols-12 gap-4 items-center">
          {/* Expand Icon */}
          <div className="col-span-1 flex items-center">
            {hasExpandedContent && (
              <svg
                className={`w-5 h-5 text-gray-400 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            )}
          </div>

          {/* Drug Name */}
          <div className="col-span-2">
            <span className="font-semibold text-gray-900">{program.name}</span>
          </div>

          {/* Target */}
          <div className="col-span-1">
            <span className="text-sm text-gray-600">{program.target || '-'}</span>
          </div>

          {/* Phase */}
          <div className="col-span-1">
            <span className={`badge ${getStageColor(program.stage)} text-xs`}>
              {program.stage}
            </span>
          </div>

          {/* Indication */}
          <div className="col-span-2">
            <span className="text-sm text-gray-600">{program.indication}</span>
          </div>

          {/* Partner */}
          <div className="col-span-1">
            <span className="text-sm text-gray-600">{program.partner || '-'}</span>
          </div>

          {/* Key Data */}
          <div className="col-span-2">
            <span className="text-sm text-gray-600">{program.key_data || '-'}</span>
          </div>

          {/* Next Catalyst */}
          <div className="col-span-2">
            <span className="text-sm text-gray-600">{program.next_catalyst || '-'}</span>
          </div>
        </div>

        {/* Mobile Card Layout */}
        <div className="md:hidden">
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center gap-2">
              {hasExpandedContent && (
                <svg
                  className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              )}
              <span className="font-semibold text-gray-900">{program.name}</span>
            </div>
            <span className={`badge ${getStageColor(program.stage)} text-xs`}>
              {program.stage}
            </span>
          </div>
          <div className="space-y-1 text-sm pl-6">
            <p><span className="text-gray-500">Indication:</span> <span className="text-gray-700">{program.indication}</span></p>
            {program.target && <p><span className="text-gray-500">Target:</span> <span className="text-gray-700">{program.target}</span></p>}
            {program.partner && <p><span className="text-gray-500">Partner:</span> <span className="text-gray-700">{program.partner}</span></p>}
            {program.key_data && <p><span className="text-gray-500">Key Data:</span> <span className="text-gray-700">{program.key_data}</span></p>}
            {program.next_catalyst && <p><span className="text-gray-500">Next:</span> <span className="text-gray-700">{program.next_catalyst}</span></p>}
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      <div className={`pipeline-row-content ${isExpanded ? 'expanded' : ''}`}>
        <div className="border-t border-gray-200 bg-white">
          {/* Section Tabs */}
          <div className="flex border-b border-gray-100 px-4 overflow-x-auto">
            {program.satya_view && (
              <SectionTab
                label="Satya View"
                isActive={expandedSections.has('satya')}
                onClick={() => toggleSection('satya')}
              />
            )}
            {program.mechanism && (
              <SectionTab
                label="Mechanism"
                isActive={expandedSections.has('mechanism')}
                onClick={() => toggleSection('mechanism')}
              />
            )}
            {program.clinical_data && program.clinical_data.length > 0 && (
              <SectionTab
                label="Clinical Data"
                isActive={expandedSections.has('clinical')}
                onClick={() => toggleSection('clinical')}
              />
            )}
            {program.competitors && program.competitors.length > 0 && (
              <SectionTab
                label="Competitive Context"
                isActive={expandedSections.has('competitive')}
                onClick={() => toggleSection('competitive')}
              />
            )}
            {program.catalysts && program.catalysts.length > 0 && (
              <SectionTab
                label="Catalysts"
                isActive={expandedSections.has('catalysts')}
                onClick={() => toggleSection('catalysts')}
              />
            )}
            {program.figures && program.figures.length > 0 && (
              <SectionTab
                label="Figures"
                isActive={expandedSections.has('figures')}
                onClick={() => toggleSection('figures')}
              />
            )}
          </div>

          {/* Section Content */}
          <div className="p-4 space-y-4">
            {/* Satya View Section */}
            {program.satya_view && expandedSections.has('satya') && (
              <SatyaViewSection view={program.satya_view} />
            )}

            {/* Mechanism Section */}
            {program.mechanism && expandedSections.has('mechanism') && (
              <MechanismSection mechanism={program.mechanism} />
            )}

            {/* Clinical Data Section */}
            {program.clinical_data && program.clinical_data.length > 0 && expandedSections.has('clinical') && (
              <ClinicalDataSection data={program.clinical_data} sectionName={sectionName} />
            )}

            {/* Competitive Context Section */}
            {program.competitors && program.competitors.length > 0 && expandedSections.has('competitive') && (
              <CompetitiveSection competitors={program.competitors} sectionName={sectionName} />
            )}

            {/* Catalysts Section */}
            {program.catalysts && program.catalysts.length > 0 && expandedSections.has('catalysts') && (
              <CatalystsSection catalysts={program.catalysts} />
            )}

            {/* Clinical Figures Section */}
            {program.figures && program.figures.length > 0 && expandedSections.has('figures') && (
              <ClinicalFigures
                figures={program.figures}
                assetName={program.name}
                sectionName={sectionName}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Section Tab Component
function SectionTab({ label, isActive, onClick }: { label: string; isActive: boolean; onClick: () => void }) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick(); }}
      className={`px-4 py-2 text-sm font-medium whitespace-nowrap transition-colors ${
        isActive
          ? 'text-biotech-600 border-b-2 border-biotech-600 -mb-px'
          : 'text-gray-500 hover:text-gray-700'
      }`}
    >
      {label}
    </button>
  );
}

// Satya View Section
function SatyaViewSection({ view }: { view: NonNullable<PipelineProgram['satya_view']> }) {
  return (
    <div className="satya-view-section">
      <div className="grid md:grid-cols-2 gap-4 mb-4">
        {/* Bull Thesis */}
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
            <h5 className="font-semibold text-green-800">Bull Thesis</h5>
          </div>
          <p className="text-sm text-green-900">{view.bull_thesis}</p>
        </div>

        {/* Bear Thesis */}
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0v-8m0 8l-8-8-4 4-6-6" />
            </svg>
            <h5 className="font-semibold text-red-800">Bear Thesis</h5>
          </div>
          <p className="text-sm text-red-900">{view.bear_thesis}</p>
        </div>
      </div>

      {/* Key Question */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h5 className="font-semibold text-amber-800">Key Question</h5>
        </div>
        <p className="text-sm text-amber-900">{view.key_question}</p>
      </div>
    </div>
  );
}

// Mechanism Section
function MechanismSection({ mechanism }: { mechanism: NonNullable<PipelineProgram['mechanism']> }) {
  return (
    <div className="mechanism-section">
      <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
        <h5 className="font-semibold text-purple-800 mb-2">Mechanism of Action</h5>
        <p className="text-sm text-purple-900 mb-3">{mechanism.description}</p>
        {mechanism.target_biology && (
          <div className="mt-3 pt-3 border-t border-purple-200">
            <h6 className="text-xs font-medium text-purple-700 mb-1">Target Biology</h6>
            <p className="text-sm text-purple-800">{mechanism.target_biology}</p>
          </div>
        )}
      </div>
    </div>
  );
}

// Clinical Data Section
function ClinicalDataSection({ data, sectionName }: { data: NonNullable<PipelineProgram['clinical_data']>; sectionName: string }) {
  return (
    <div className="clinical-data-section space-y-4">
      {data.map((trial, idx) => (
        <div key={idx} className="border border-gray-200 rounded-lg overflow-hidden">
          {/* Trial Header */}
          <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <h6 className="font-semibold text-gray-900">{trial.trial_name}</h6>
                <p className="text-sm text-gray-600">
                  {trial.phase} • {trial.indication}
                  {trial.nct_id && (
                    <a
                      href={`https://clinicaltrials.gov/study/${trial.nct_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ml-2 text-biotech-600 hover:underline"
                    >
                      {trial.nct_id}
                    </a>
                  )}
                </p>
              </div>
              {trial.conference && (
                <span className="text-xs text-gray-500">{trial.conference}</span>
              )}
            </div>
            {trial.design && (
              <div className="mt-2 text-xs text-gray-500">
                N={trial.design.n_enrolled}
                {trial.design.arms && ` • Arms: ${trial.design.arms.join(', ')}`}
                {trial.design.duration && ` • ${trial.design.duration}`}
              </div>
            )}
          </div>

          {/* Results */}
          {trial.results && (
            <div className="p-4">
              {/* Primary Endpoint */}
              {trial.results.primary && (
                <div className="mb-3">
                  <div className="text-xs font-medium text-gray-500 uppercase mb-1">Primary Endpoint</div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-sm text-gray-700">{trial.results.primary.endpoint}:</span>
                    <span className="text-lg font-bold text-biotech-700">{trial.results.primary.result}</span>
                    {trial.results.primary.comparator && (
                      <span className="text-sm text-gray-500">vs {trial.results.primary.comparator}</span>
                    )}
                    {trial.results.primary.p_value && (
                      <span className="text-xs text-gray-500">(p{trial.results.primary.p_value})</span>
                    )}
                    {trial.results.primary.citation_number && (
                      <Citation section={sectionName} number={trial.results.primary.citation_number} />
                    )}
                  </div>
                </div>
              )}

              {/* Secondary Endpoints */}
              {trial.results.secondary && trial.results.secondary.length > 0 && (
                <div className="mb-3">
                  <div className="text-xs font-medium text-gray-500 uppercase mb-1">Secondary Endpoints</div>
                  <div className="space-y-1">
                    {trial.results.secondary.map((sec, sidx) => (
                      <div key={sidx} className="text-sm">
                        <span className="text-gray-600">{sec.endpoint}:</span>{' '}
                        <span className="font-medium text-gray-900">{sec.result}</span>
                        {sec.citation_number && (
                          <Citation section={sectionName} number={sec.citation_number} />
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Safety */}
              {trial.results.safety && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <div className="text-xs font-medium text-gray-500 uppercase mb-1">Safety</div>
                  <div className="text-sm text-gray-600">
                    {trial.results.safety.any_ae_percent !== undefined && (
                      <span className="mr-4">Any AE: {trial.results.safety.any_ae_percent}%</span>
                    )}
                    {trial.results.safety.serious_ae_percent !== undefined && (
                      <span className="mr-4">SAE: {trial.results.safety.serious_ae_percent}%</span>
                    )}
                    {trial.results.safety.discontinuations_percent !== undefined && (
                      <span>D/C: {trial.results.safety.discontinuations_percent}%</span>
                    )}
                  </div>
                  {trial.results.safety.notable_signals && trial.results.safety.notable_signals.length > 0 && (
                    <div className="text-xs text-gray-500 mt-1">
                      {trial.results.safety.notable_signals.join(' • ')}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// Competitive Context Section
function CompetitiveSection({ competitors, sectionName }: { competitors: NonNullable<PipelineProgram['competitors']>; sectionName: string }) {
  return (
    <div className="competitive-section space-y-3">
      {competitors.map((comp, idx) => (
        <div key={idx} className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors">
          <div className="flex items-start justify-between mb-2">
            <div>
              <h6 className="font-semibold text-gray-900">{comp.drug_name}</h6>
              <p className="text-sm text-gray-600">{comp.company}</p>
            </div>
            <span className="badge bg-gray-100 text-gray-700 text-xs">{comp.stage}</span>
          </div>
          {comp.mechanism && (
            <p className="text-xs text-gray-500 mb-2">{comp.mechanism}</p>
          )}
          {comp.efficacy && (
            <p className="text-sm mb-2">
              <span className="text-gray-500">Efficacy:</span>{' '}
              <span className="font-medium text-gray-900">{comp.efficacy}</span>
            </p>
          )}
          {comp.differentiation && (
            <p className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
              <span className="font-medium">Differentiation:</span> {comp.differentiation}
              {comp.citation_number && (
                <Citation section={sectionName} number={comp.citation_number} />
              )}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

// Catalysts Section
function CatalystsSection({ catalysts }: { catalysts: NonNullable<PipelineProgram['catalysts']> }) {
  const upcomingCatalysts = catalysts.filter(c => c.status === 'upcoming' || c.status === 'planned');
  const completedCatalysts = catalysts.filter(c => c.status === 'completed');

  return (
    <div className="catalysts-section">
      <div className="grid md:grid-cols-2 gap-6">
        {/* Upcoming */}
        <div>
          <h5 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <span className="w-2 h-2 bg-green-500 rounded-full"></span>
            Upcoming Catalysts
          </h5>
          {upcomingCatalysts.length > 0 ? (
            <div className="space-y-2">
              {upcomingCatalysts.map((catalyst, idx) => (
                <div
                  key={idx}
                  className={`border-l-4 ${catalyst.status === 'upcoming' ? 'border-l-green-500 bg-green-50' : 'border-l-blue-400 bg-blue-50'} p-3 rounded-r`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-gray-600">
                      {catalyst.expected_date || 'TBD'}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded ${catalyst.status === 'upcoming' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'}`}>
                      {catalyst.status}
                    </span>
                  </div>
                  <div className="text-sm font-medium text-gray-800">{catalyst.event}</div>
                  {catalyst.significance && (
                    <div className="text-xs text-gray-600 mt-1">{catalyst.significance}</div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 italic">No upcoming catalysts</p>
          )}
        </div>

        {/* Completed */}
        <div>
          <h5 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <span className="w-2 h-2 bg-gray-400 rounded-full"></span>
            Completed Events
          </h5>
          {completedCatalysts.length > 0 ? (
            <div className="space-y-2">
              {completedCatalysts.map((catalyst, idx) => (
                <div key={idx} className="border-l-4 border-l-gray-300 bg-gray-50 p-3 rounded-r">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-500">
                      {catalyst.actual_date || catalyst.expected_date}
                    </span>
                    {catalyst.stock_reaction_1d && (
                      <span className={`text-xs font-medium ${catalyst.stock_reaction_1d.startsWith('+') ? 'text-green-600' : 'text-red-600'}`}>
                        {catalyst.stock_reaction_1d}
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-gray-800">{catalyst.event}</div>
                  {catalyst.outcome && (
                    <div className="text-xs text-gray-600 mt-1">
                      <span className="font-medium">Outcome:</span> {catalyst.outcome}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 italic">No completed events</p>
          )}
        </div>
      </div>
    </div>
  );
}
