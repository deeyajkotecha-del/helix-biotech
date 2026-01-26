import type { ClinicalTrialsSection as ClinicalData } from '../../types';

interface Props {
  data: ClinicalData;
}

export default function ClinicalTrialsSection({ data }: Props) {
  const getStatusBadge = (status: string) => {
    const lower = status.toLowerCase();
    if (lower.includes('recruiting')) return 'badge-success';
    if (lower.includes('completed')) return 'badge-info';
    if (lower.includes('active')) return 'badge-warning';
    if (lower.includes('terminated') || lower.includes('withdrawn')) return 'badge-danger';
    return 'badge-neutral';
  };

  const getPhaseBadge = (phase?: string) => {
    if (!phase) return 'badge-neutral';
    const lower = phase.toLowerCase();
    if (lower.includes('3')) return 'bg-blue-100 text-blue-800';
    if (lower.includes('2')) return 'bg-yellow-100 text-yellow-800';
    if (lower.includes('1')) return 'bg-orange-100 text-orange-800';
    return 'badge-neutral';
  };

  return (
    <div>
      <h3 className="section-title">Clinical Trials from ClinicalTrials.gov</h3>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-biotech-50 rounded-lg p-4 text-center">
          <p className="text-3xl font-bold text-biotech-700">{data.total_trials}</p>
          <p className="text-sm text-gray-600">Total Trials</p>
        </div>
        <div className="bg-green-50 rounded-lg p-4 text-center">
          <p className="text-3xl font-bold text-green-700">{data.active_trials.length}</p>
          <p className="text-sm text-gray-600">Active</p>
        </div>
        <div className="bg-blue-50 rounded-lg p-4 text-center">
          <p className="text-3xl font-bold text-blue-700">{data.completed_trials.length}</p>
          <p className="text-sm text-gray-600">Completed</p>
        </div>
        <div className="bg-amber-50 rounded-lg p-4 text-center">
          <p className="text-3xl font-bold text-amber-700">{data.upcoming_readouts.length}</p>
          <p className="text-sm text-gray-600">Upcoming Readouts</p>
        </div>
      </div>

      {/* Phases Breakdown */}
      {Object.keys(data.phases_summary).length > 0 && (
        <div className="mb-6">
          <h4 className="font-semibold text-gray-800 mb-3">Trials by Phase</h4>
          <div className="flex flex-wrap gap-2">
            {Object.entries(data.phases_summary).map(([phase, count]) => (
              <span key={phase} className={`badge ${getPhaseBadge(phase)} px-3 py-1`}>
                {phase}: {count}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Upcoming Readouts */}
      {data.upcoming_readouts.length > 0 && (
        <div className="mb-6">
          <h4 className="font-semibold text-amber-700 mb-3 flex items-center">
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            Upcoming Data Readouts
          </h4>
          <div className="space-y-2">
            {data.upcoming_readouts.map((readout, index) => (
              <div key={index} className="flex items-center justify-between bg-amber-50 p-3 rounded-lg">
                <div>
                  <p className="font-medium text-gray-800 text-sm">{readout.title}</p>
                  <p className="text-xs text-gray-500">{readout.trial_id}</p>
                </div>
                <div className="text-right">
                  <span className="badge badge-warning">{readout.expected_date}</span>
                  {readout.phase && (
                    <span className={`badge ${getPhaseBadge(readout.phase)} ml-2`}>
                      {readout.phase}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active Trials */}
      <div className="mb-6">
        <h4 className="font-semibold text-green-700 mb-3">
          Active Trials ({data.active_trials.length})
        </h4>
        {data.active_trials.length > 0 ? (
          <div className="space-y-3">
            {data.active_trials.map((trial) => (
              <div
                key={trial.nct_id}
                className="border border-gray-200 rounded-lg p-4 hover:border-green-300 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <h5 className="font-medium text-gray-800 mb-1">{trial.title}</h5>
                    <div className="flex flex-wrap gap-2 text-xs">
                      <a
                        href={`https://clinicaltrials.gov/study/${trial.nct_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-biotech-600 hover:text-biotech-700 font-medium"
                      >
                        {trial.nct_id}
                      </a>
                      {trial.sponsor && (
                        <span className="text-gray-500">| {trial.sponsor}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1 ml-4">
                    <span className={`badge ${getStatusBadge(trial.status)}`}>
                      {trial.status}
                    </span>
                    {trial.phase && (
                      <span className={`badge ${getPhaseBadge(trial.phase)}`}>
                        {trial.phase}
                      </span>
                    )}
                  </div>
                </div>
                {trial.conditions.length > 0 && (
                  <p className="text-sm text-gray-600 mb-1">
                    <span className="font-medium">Conditions:</span>{' '}
                    {trial.conditions.join(', ')}
                  </p>
                )}
                {trial.interventions.length > 0 && (
                  <p className="text-sm text-gray-600 mb-1">
                    <span className="font-medium">Interventions:</span>{' '}
                    {trial.interventions.join(', ')}
                  </p>
                )}
                <div className="flex flex-wrap gap-4 text-xs text-gray-500 mt-2">
                  {trial.start_date && <span>Started: {trial.start_date}</span>}
                  {trial.completion_date && <span>Est. Completion: {trial.completion_date}</span>}
                  {trial.enrollment && <span>Enrollment: {trial.enrollment}</span>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-400 italic">No active trials found</p>
        )}
      </div>

      {/* Completed Trials */}
      {data.completed_trials.length > 0 && (
        <div>
          <h4 className="font-semibold text-blue-700 mb-3">
            Completed Trials ({data.completed_trials.length})
          </h4>
          <div className="space-y-3">
            {data.completed_trials.slice(0, 5).map((trial) => (
              <div
                key={trial.nct_id}
                className="border border-gray-200 rounded-lg p-4 bg-gray-50"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <h5 className="font-medium text-gray-700 mb-1">{trial.title}</h5>
                    <a
                      href={`https://clinicaltrials.gov/study/${trial.nct_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-biotech-600 hover:text-biotech-700"
                    >
                      {trial.nct_id}
                    </a>
                  </div>
                  <span className={`badge ${getStatusBadge(trial.status)}`}>
                    {trial.status}
                  </span>
                </div>
                {trial.conditions.length > 0 && (
                  <p className="text-sm text-gray-500">
                    {trial.conditions.join(', ')}
                  </p>
                )}
              </div>
            ))}
            {data.completed_trials.length > 5 && (
              <p className="text-sm text-gray-500 text-center">
                + {data.completed_trials.length - 5} more completed trials
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
