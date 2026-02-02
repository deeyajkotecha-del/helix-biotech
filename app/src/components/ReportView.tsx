import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { reportsApi } from '../services/api';
import type { Report } from '../types';
import BLUFSection from './sections/BLUFSection';
import PipelineSection from './sections/PipelineSection';
import PatentSection from './sections/PatentSection';
import ManagementSection from './sections/ManagementSection';
import PreclinicalSection from './sections/PreclinicalSection';
import ClinicalTrialsSection from './sections/ClinicalTrialsSection';

export default function ReportView() {
  const { ticker } = useParams<{ ticker: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<string>('bluf');

  useEffect(() => {
    if (ticker) {
      loadReport(ticker);
    }
  }, [ticker]);

  const loadReport = async (tickerSymbol: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await reportsApi.get(tickerSymbol);
      setReport(data);
    } catch (err) {
      setError('Failed to load report. Please try again.');
      console.error('Error loading report:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    if (!ticker) return;
    try {
      setRefreshing(true);
      const data = await reportsApi.generate(ticker, true);
      setReport(data);
    } catch (err) {
      console.error('Error refreshing report:', err);
    } finally {
      setRefreshing(false);
    }
  };

  const sections = [
    { id: 'bluf', label: 'BLUF Summary' },
    { id: 'pipeline', label: 'Pipeline' },
    { id: 'clinical', label: 'Clinical Trials' },
    { id: 'preclinical', label: 'Preclinical Data' },
    { id: 'patent', label: 'Patent & Legal' },
    { id: 'management', label: 'Management' },
  ];

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="text-center">
          <div className="loading-spinner mx-auto mb-4"></div>
          <p className="text-gray-600">
            Generating report for {ticker}...
          </p>
          <p className="text-gray-400 text-sm mt-2">
            Fetching data from PubMed & ClinicalTrials.gov
          </p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <h3 className="text-red-800 font-semibold mb-2">Error</h3>
        <p className="text-red-600">{error || 'Report not found'}</p>
        <Link
          to="/"
          className="mt-4 inline-block px-4 py-2 bg-biotech-600 text-white rounded hover:bg-biotech-700"
        >
          Back to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <Link
            to="/"
            className="text-biotech-600 hover:text-biotech-700 text-sm mb-2 inline-flex items-center"
          >
            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Dashboard
          </Link>
          <h2 className="text-3xl font-bold text-gray-800">
            <span className="text-biotech-600">{report.ticker}</span>
            {' '}{report.company_name}
          </h2>
          <p className="text-gray-500 text-sm mt-1">
            Report generated: {new Date(report.generated_at).toLocaleString()}
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="px-4 py-2 bg-biotech-600 text-white rounded-lg hover:bg-biotech-700 disabled:opacity-50 flex items-center"
        >
          {refreshing ? (
            <>
              <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full mr-2"></div>
              Refreshing...
            </>
          ) : (
            <>
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh Data
            </>
          )}
        </button>
      </div>

      {/* Section Navigation */}
      <div className="mb-6 border-b border-gray-200">
        <nav className="flex space-x-8 overflow-x-auto">
          {sections.map((section) => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              className={`py-3 px-1 border-b-2 font-medium text-sm whitespace-nowrap ${
                activeSection === section.id
                  ? 'border-biotech-600 text-biotech-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {section.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Section Content */}
      <div className="section-card">
        {activeSection === 'bluf' && report.sections.bluf && (
          <BLUFSection data={report.sections.bluf} />
        )}
        {activeSection === 'pipeline' && report.sections.pipeline && (
          <PipelineSection data={report.sections.pipeline} />
        )}
        {activeSection === 'clinical' && report.sections.clinical_trials && (
          <ClinicalTrialsSection data={report.sections.clinical_trials} />
        )}
        {activeSection === 'preclinical' && report.sections.preclinical && (
          <PreclinicalSection data={report.sections.preclinical} />
        )}
        {activeSection === 'patent' && report.sections.patent_legal && (
          <PatentSection data={report.sections.patent_legal} />
        )}
        {activeSection === 'management' && report.sections.management && (
          <ManagementSection data={report.sections.management} />
        )}
      </div>

      {/* Data Sources */}
      <div className="mt-6 text-sm text-gray-500">
        <p className="font-medium mb-1">Data Sources:</p>
        <p>{report.data_sources.join(' | ')}</p>
      </div>
    </div>
  );
}
