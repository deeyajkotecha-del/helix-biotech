import type { PipelineSection as PipelineData } from '../../types';

interface Props {
  data: PipelineData;
}

export default function PipelineSection({ data }: Props) {
  const getStageColor = (stage: string) => {
    const lower = stage.toLowerCase();
    if (lower.includes('approved')) return 'bg-green-100 text-green-800';
    if (lower.includes('phase 3') || lower.includes('phase3')) return 'bg-blue-100 text-blue-800';
    if (lower.includes('phase 2') || lower.includes('phase2')) return 'bg-yellow-100 text-yellow-800';
    if (lower.includes('phase 1') || lower.includes('phase1')) return 'bg-orange-100 text-orange-800';
    return 'bg-gray-100 text-gray-800';
  };

  return (
    <div>
      <h3 className="section-title">Pipeline Overview</h3>

      {/* Lead Asset Highlight */}
      {data.lead_asset && (
        <div className="bg-biotech-50 border border-biotech-200 rounded-lg p-5 mb-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-biotech-600 font-medium mb-1">Lead Asset</p>
              <h4 className="text-xl font-bold text-biotech-800">{data.lead_asset}</h4>
              {data.lead_asset_indication && (
                <p className="text-gray-600 mt-1">{data.lead_asset_indication}</p>
              )}
            </div>
            {data.lead_asset_stage && (
              <span className={`badge ${getStageColor(data.lead_asset_stage)} text-sm px-3 py-1`}>
                {data.lead_asset_stage}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Pipeline Programs */}
      <div className="mb-4">
        <h4 className="font-semibold text-gray-800 mb-3">
          Pipeline Programs ({data.total_programs})
        </h4>

        {data.programs.length > 0 ? (
          <div className="space-y-3">
            {data.programs.map((program, index) => (
              <div
                key={index}
                className="border border-gray-200 rounded-lg p-4 hover:border-biotech-300 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <h5 className="font-medium text-gray-800">{program.name}</h5>
                  <span className={`badge ${getStageColor(program.stage)}`}>
                    {program.stage}
                  </span>
                </div>
                <p className="text-gray-600 text-sm mb-1">
                  <span className="font-medium">Indication:</span> {program.indication}
                </p>
                {program.description && (
                  <p className="text-gray-500 text-sm">{program.description}</p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-400 italic">No pipeline data available</p>
        )}
      </div>

      {/* Pipeline Visual */}
      {data.programs.length > 0 && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h4 className="font-semibold text-gray-800 mb-4">Pipeline by Stage</h4>
          <div className="grid grid-cols-4 gap-2 text-center text-xs">
            <div className="bg-orange-100 p-2 rounded">Phase 1</div>
            <div className="bg-yellow-100 p-2 rounded">Phase 2</div>
            <div className="bg-blue-100 p-2 rounded">Phase 3</div>
            <div className="bg-green-100 p-2 rounded">Approved</div>
          </div>
          <div className="grid grid-cols-4 gap-2 mt-2">
            {['phase 1', 'phase 2', 'phase 3', 'approved'].map((stage) => {
              const programs = data.programs.filter(p =>
                p.stage.toLowerCase().includes(stage)
              );
              return (
                <div key={stage} className="text-center">
                  {programs.map((p, i) => (
                    <div
                      key={i}
                      className="text-xs bg-gray-50 p-1 rounded mb-1 truncate"
                      title={p.name}
                    >
                      {p.name}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
