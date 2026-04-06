import { useState, useEffect } from 'react'

// ============================================================
// Types
// ============================================================

interface PrivateCompany {
  id: number
  name: string
  slug: string
  hq_location: string
  founded_year: number | null
  employee_count: string
  therapeutic_areas: string[]
  modality: string
  lead_programs: string
  stage: string
  description: string
  website: string
  source_url: string
  source_type: string
  last_updated: string | null
}

interface DirectoryFilters {
  stages: string[]
  modalities: string[]
  therapeutic_areas: string[]
}

interface AddFormData {
  name: string
  hq_location: string
  founded_year: string
  employee_count: string
  therapeutic_areas: string
  modality: string
  lead_programs: string
  stage: string
  description: string
  website: string
}

const STAGE_LABELS: Record<string, string> = {
  preclinical: 'Preclinical',
  phase1: 'Phase 1',
  phase2: 'Phase 2',
  phase3: 'Phase 3',
  discovery: 'Discovery',
  approved: 'Approved',
}

const STAGE_COLORS: Record<string, string> = {
  discovery: '#9B8EC4',
  preclinical: '#7B93C0',
  phase1: '#3B6DAB',
  phase2: '#C4603C',
  phase3: '#3D8B5E',
  approved: '#2D6B4E',
}

// ============================================================
// Component
// ============================================================

interface Props {
  onCompanySearch?: (name: string) => void
}

export default function DirectoryPanel({ onCompanySearch }: Props) {
  const [companies, setCompanies] = useState<PrivateCompany[]>([])
  const [filters, setFilters] = useState<DirectoryFilters>({ stages: [], modalities: [], therapeutic_areas: [] })
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  // Filter state
  const [query, setQuery] = useState('')
  const [stageFilter, setStageFilter] = useState('')
  const [modalityFilter, setModalityFilter] = useState('')
  const [areaFilter, setAreaFilter] = useState('')

  // Detail / add state
  const [selectedCompany, setSelectedCompany] = useState<PrivateCompany | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [addForm, setAddForm] = useState<AddFormData>({
    name: '', hq_location: '', founded_year: '', employee_count: '',
    therapeutic_areas: '', modality: '', lead_programs: '', stage: '',
    description: '', website: '',
  })
  const [saving, setSaving] = useState(false)

  // Load companies
  async function loadCompanies() {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (query) params.set('q', query)
      if (stageFilter) params.set('stage', stageFilter)
      if (modalityFilter) params.set('modality', modalityFilter)
      if (areaFilter) params.set('therapeutic_area', areaFilter)

      const res = await fetch(`/extract/api/directory/companies?${params}`)
      if (res.ok) {
        const data = await res.json()
        setCompanies(data.companies || [])
        setTotal(data.total || 0)
        setFilters(data.filters || { stages: [], modalities: [], therapeutic_areas: [] })
      }
    } catch (e) {
      console.error('Directory load error:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadCompanies() }, [stageFilter, modalityFilter, areaFilter])

  // Search on enter
  function handleSearchKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter') loadCompanies()
  }

  // Add company
  async function handleAdd() {
    if (!addForm.name.trim()) return
    setSaving(true)
    try {
      const body = {
        ...addForm,
        founded_year: addForm.founded_year ? parseInt(addForm.founded_year) : null,
        therapeutic_areas: addForm.therapeutic_areas
          ? addForm.therapeutic_areas.split(',').map(s => s.trim()).filter(Boolean)
          : [],
        source_type: 'manual',
      }
      const res = await fetch('/extract/api/directory/companies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (res.ok) {
        setShowAddForm(false)
        setAddForm({
          name: '', hq_location: '', founded_year: '', employee_count: '',
          therapeutic_areas: '', modality: '', lead_programs: '', stage: '',
          description: '', website: '',
        })
        loadCompanies()
      }
    } catch (e) {
      console.error('Add company error:', e)
    } finally {
      setSaving(false)
    }
  }

  // ============================================================
  // Detail view
  // ============================================================

  if (selectedCompany) {
    const c = selectedCompany
    return (
      <div className="ev-company-panel">
        <div className="ev-panel-header">
          <button className="ev-back-btn" onClick={() => setSelectedCompany(null)}>&larr; Back</button>
          <h3>{c.name}</h3>
        </div>
        <div className="ev-dir-detail">
          {c.stage && (
            <span
              className="ev-dir-stage-badge"
              style={{ background: STAGE_COLORS[c.stage] || '#888' }}
            >
              {STAGE_LABELS[c.stage] || c.stage}
            </span>
          )}
          {c.modality && <span className="ev-dir-modality-tag">{c.modality}</span>}

          {c.description && (
            <p className="ev-dir-description">{c.description}</p>
          )}

          <div className="ev-dir-fields">
            {c.therapeutic_areas.length > 0 && (
              <div className="ev-dir-field">
                <label>Therapeutic Areas</label>
                <div className="ev-dir-tags">
                  {c.therapeutic_areas.map(ta => (
                    <span key={ta} className="ev-dir-ta-tag">{ta}</span>
                  ))}
                </div>
              </div>
            )}
            {c.lead_programs && (
              <div className="ev-dir-field">
                <label>Lead Programs</label>
                <p>{c.lead_programs}</p>
              </div>
            )}
            {c.hq_location && (
              <div className="ev-dir-field">
                <label>HQ</label>
                <p>{c.hq_location}</p>
              </div>
            )}
            {c.founded_year && (
              <div className="ev-dir-field">
                <label>Founded</label>
                <p>{c.founded_year}</p>
              </div>
            )}
            {c.employee_count && (
              <div className="ev-dir-field">
                <label>Employees</label>
                <p>{c.employee_count}</p>
              </div>
            )}
            {c.website && (
              <div className="ev-dir-field">
                <label>Website</label>
                <a href={c.website} target="_blank" rel="noopener noreferrer" className="ev-dir-link">
                  {c.website.replace(/^https?:\/\//, '')}
                </a>
              </div>
            )}
            {c.source_url && (
              <div className="ev-dir-field">
                <label>Source</label>
                <a href={c.source_url} target="_blank" rel="noopener noreferrer" className="ev-dir-link">
                  {c.source_type || 'View source'}
                </a>
              </div>
            )}
          </div>

          {onCompanySearch && (
            <button
              className="ev-forecast-btn"
              style={{ marginTop: 12 }}
              onClick={() => onCompanySearch(c.name)}
            >
              Search library for {c.name}
            </button>
          )}
        </div>
      </div>
    )
  }

  // ============================================================
  // Add form
  // ============================================================

  if (showAddForm) {
    return (
      <div className="ev-company-panel">
        <div className="ev-panel-header">
          <button className="ev-back-btn" onClick={() => setShowAddForm(false)}>&larr; Back</button>
          <h3>Add Company</h3>
        </div>
        <div className="ev-dir-add-form">
          <input placeholder="Company name *" value={addForm.name}
            onChange={e => setAddForm(f => ({ ...f, name: e.target.value }))} className="ev-panel-search" />
          <input placeholder="Stage (e.g. preclinical, phase1, phase2)" value={addForm.stage}
            onChange={e => setAddForm(f => ({ ...f, stage: e.target.value }))} className="ev-panel-search" />
          <input placeholder="Modality (e.g. ADC, small molecule, cell therapy)" value={addForm.modality}
            onChange={e => setAddForm(f => ({ ...f, modality: e.target.value }))} className="ev-panel-search" />
          <input placeholder="Therapeutic areas (comma-separated)" value={addForm.therapeutic_areas}
            onChange={e => setAddForm(f => ({ ...f, therapeutic_areas: e.target.value }))} className="ev-panel-search" />
          <input placeholder="Lead programs" value={addForm.lead_programs}
            onChange={e => setAddForm(f => ({ ...f, lead_programs: e.target.value }))} className="ev-panel-search" />
          <textarea placeholder="Description" value={addForm.description}
            onChange={e => setAddForm(f => ({ ...f, description: e.target.value }))}
            className="ev-panel-search" style={{ minHeight: 60, resize: 'vertical' }} />
          <input placeholder="HQ location" value={addForm.hq_location}
            onChange={e => setAddForm(f => ({ ...f, hq_location: e.target.value }))} className="ev-panel-search" />
          <input placeholder="Founded year" value={addForm.founded_year}
            onChange={e => setAddForm(f => ({ ...f, founded_year: e.target.value }))} className="ev-panel-search" />
          <input placeholder="Employee count (e.g. 11-50)" value={addForm.employee_count}
            onChange={e => setAddForm(f => ({ ...f, employee_count: e.target.value }))} className="ev-panel-search" />
          <input placeholder="Website" value={addForm.website}
            onChange={e => setAddForm(f => ({ ...f, website: e.target.value }))} className="ev-panel-search" />
          <button className="ev-forecast-btn" onClick={handleAdd} disabled={saving || !addForm.name.trim()}>
            {saving ? 'Saving...' : 'Add Company'}
          </button>
        </div>
      </div>
    )
  }

  // ============================================================
  // List view
  // ============================================================

  return (
    <div className="ev-company-panel">
      <div className="ev-panel-header">
        <h3>Private Co Directory</h3>
        <span className="ev-panel-count">{total} companies</span>
      </div>

      {/* Search */}
      <input
        className="ev-panel-search"
        placeholder="Search by name, program, or description..."
        value={query}
        onChange={e => setQuery(e.target.value)}
        onKeyDown={handleSearchKey}
      />

      {/* Filters */}
      <div className="ev-dir-filters">
        <select className="ev-dir-filter-select" value={stageFilter}
          onChange={e => setStageFilter(e.target.value)}>
          <option value="">All stages</option>
          {filters.stages.map(s => (
            <option key={s} value={s}>{STAGE_LABELS[s] || s}</option>
          ))}
        </select>
        <select className="ev-dir-filter-select" value={modalityFilter}
          onChange={e => setModalityFilter(e.target.value)}>
          <option value="">All modalities</option>
          {filters.modalities.map(m => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        {filters.therapeutic_areas.length > 0 && (
          <select className="ev-dir-filter-select" value={areaFilter}
            onChange={e => setAreaFilter(e.target.value)}>
            <option value="">All areas</option>
            {filters.therapeutic_areas.map(a => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        )}
      </div>

      {/* Add button */}
      <button className="ev-dir-add-btn" onClick={() => setShowAddForm(true)}>
        + Add Company
      </button>

      {/* Company list */}
      <div className="ev-panel-list">
        {loading ? (
          <div className="ev-panel-loading">Loading directory...</div>
        ) : companies.length === 0 ? (
          <div className="ev-panel-empty">
            No companies yet. Add your first company or run the BioPharma Dive scraper to populate the directory.
          </div>
        ) : (
          companies.map(c => (
            <button key={c.id} className="ev-company-row" onClick={() => setSelectedCompany(c)}>
              <div className="ev-dir-row-main">
                <span className="ev-company-name">{c.name}</span>
                {c.stage && (
                  <span
                    className="ev-dir-stage-pill"
                    style={{ background: STAGE_COLORS[c.stage] || '#888' }}
                  >
                    {STAGE_LABELS[c.stage] || c.stage}
                  </span>
                )}
              </div>
              <div className="ev-dir-row-meta">
                {c.modality && <span className="ev-dir-row-modality">{c.modality}</span>}
                {c.therapeutic_areas.length > 0 && (
                  <span className="ev-dir-row-area">{c.therapeutic_areas[0]}</span>
                )}
                {c.hq_location && <span className="ev-dir-row-hq">{c.hq_location}</span>}
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  )
}
