/**
 * LandscapeChart — Reusable grouped bar chart for clinical endpoint comparisons.
 *
 * Designed to produce Wedbush-quality landscape visuals showing drug efficacy
 * (e.g., EASI-75 for AD, ORR for oncology, HbA1c for metabolic) grouped by
 * mechanism of action. Works for any indication.
 *
 * Usage:
 *   <LandscapeChart
 *     data={[
 *       { drug: "dupilumab", trial: "SOLO 2", mechanism: "IL-4Rα/IL-13",
 *         pbo_adjusted: 36, absolute: 49 },
 *       ...
 *     ]}
 *     endpoint="EASI-75"
 *     indication="Atopic Dermatitis"
 *   />
 */

import { useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  Label,
} from 'recharts'

// ─── Types ─────────────────────────────────────────────────────────────────

export interface LandscapeDataPoint {
  drug: string
  trial?: string
  mechanism: string
  pbo_adjusted?: number | null
  absolute?: number | null
  dose?: string
  phase?: string
  company?: string
  ticker?: string
  note?: string  // e.g., "#: Value not reported"
}

interface LandscapeChartProps {
  data: LandscapeDataPoint[]
  endpoint: string        // e.g., "EASI-75", "ORR", "PFS"
  indication: string      // e.g., "Atopic Dermatitis", "NSCLC"
  valueUnit?: string      // e.g., "%" (default), "months"
  title?: string          // Override auto-generated title
  height?: number         // Chart height in px (default 420)
  showAbsolute?: boolean  // Show absolute bars alongside pbo-adjusted
  compactLabels?: boolean // Use short drug names only (no trial names)
  highlightDrug?: string  // Highlight a specific drug (e.g., your company's drug)
}

// ─── Color palette per mechanism ─────────────────────────────────────────────

const MECHANISM_COLORS: Record<string, string> = {
  // AD-specific
  'IL-4Rα/IL-13':    '#4A6FA5',
  'IL-4Ra/IL-13':    '#4A6FA5',
  'IL-13':           '#6B8EC2',
  'IL-31':           '#8B6C3F',
  'OX40/OX40L':      '#2E7D6B',
  'OX40':            '#2E7D6B',
  'TSLP':            '#9B59B6',
  'JAK':             '#E67E22',
  'JAK1':            '#E67E22',
  'JAK1/2':          '#D35400',
  'IL-2':            '#27AE60',
  'IL-18':           '#C0392B',
  'IL-22':           '#E74C3C',
  'IL-17':           '#E91E63',
  'STAT6':           '#3498DB',
  // Oncology
  'KRAS G12C':       '#E74C3C',
  'KRAS G12D':       '#C0392B',
  'KRAS multi':      '#922B21',
  'PD-1':            '#2980B9',
  'PD-L1':           '#3498DB',
  'EGFR':            '#27AE60',
  'ALK':             '#8E44AD',
  'ADC':             '#D35400',
  'CDK4/6':          '#F39C12',
  // Metabolic
  'GLP-1':           '#1ABC9C',
  'GIP/GLP-1':       '#16A085',
  'THR-beta':        '#2C3E50',
  'FGF21':           '#7F8C8D',
  // Default
  'Other':           '#95A5A6',
}

function getMechanismColor(mechanism: string): string {
  // Try exact match first
  if (MECHANISM_COLORS[mechanism]) return MECHANISM_COLORS[mechanism]
  // Try partial match
  for (const [key, color] of Object.entries(MECHANISM_COLORS)) {
    if (mechanism.toLowerCase().includes(key.toLowerCase())) return color
  }
  return MECHANISM_COLORS['Other']
}

// ─── Custom tooltip ──────────────────────────────────────────────────────────

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null
  const data = payload[0]?.payload
  if (!data) return null

  return (
    <div style={{
      background: '#1E1B18',
      border: '1px solid #3D3A36',
      borderRadius: 8,
      padding: '10px 14px',
      color: '#F0EBE4',
      fontSize: 13,
      maxWidth: 280,
      lineHeight: 1.5,
    }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{data.drug}</div>
      {data.trial && <div style={{ color: '#A09A92', fontSize: 12 }}>Trial: {data.trial}</div>}
      {data.company && <div style={{ color: '#A09A92', fontSize: 12 }}>{data.company} {data.ticker ? `(${data.ticker})` : ''}</div>}
      <div style={{ color: getMechanismColor(data.mechanism), fontSize: 12, fontWeight: 500 }}>
        {data.mechanism}
      </div>
      <div style={{ marginTop: 6, borderTop: '1px solid #3D3A36', paddingTop: 6 }}>
        {data.pbo_adjusted != null && (
          <div>Pbo-adjusted: <strong>{data.pbo_adjusted}%</strong></div>
        )}
        {data.absolute != null && (
          <div>Absolute: <strong>{data.absolute}%</strong></div>
        )}
        {data.dose && <div style={{ color: '#A09A92', fontSize: 11 }}>Dose: {data.dose}</div>}
        {data.phase && <div style={{ color: '#A09A92', fontSize: 11 }}>Phase: {data.phase}</div>}
      </div>
      {data.note && (
        <div style={{ marginTop: 4, color: '#C1A87C', fontSize: 11, fontStyle: 'italic' }}>
          {data.note}
        </div>
      )}
    </div>
  )
}

// ─── Main component ──────────────────────────────────────────────────────────

export default function LandscapeChart({
  data,
  endpoint,
  indication,
  valueUnit = '%',
  title,
  height = 420,
  showAbsolute = true,
  compactLabels = false,
  highlightDrug,
}: LandscapeChartProps) {

  // Group and sort data by mechanism
  const chartData = useMemo(() => {
    // Sort: group by mechanism, within group sort by pbo_adjusted descending
    const mechanismOrder: string[] = []
    const seen = new Set<string>()
    for (const d of data) {
      if (!seen.has(d.mechanism)) {
        mechanismOrder.push(d.mechanism)
        seen.add(d.mechanism)
      }
    }

    return [...data].sort((a, b) => {
      const mechA = mechanismOrder.indexOf(a.mechanism)
      const mechB = mechanismOrder.indexOf(b.mechanism)
      if (mechA !== mechB) return mechA - mechB
      return (b.pbo_adjusted ?? b.absolute ?? 0) - (a.pbo_adjusted ?? a.absolute ?? 0)
    }).map(d => ({
      ...d,
      label: compactLabels
        ? d.drug
        : d.trial
          ? `${d.drug}; ${d.trial}`
          : d.drug,
      color: getMechanismColor(d.mechanism),
      absoluteColor: getMechanismColor(d.mechanism) + '66', // 40% opacity
    }))
  }, [data, compactLabels])

  // Generate mechanism groups for x-axis labels
  const mechanismGroups = useMemo(() => {
    const groups: { mechanism: string; startIdx: number; endIdx: number; color: string }[] = []
    let currentMech = ''
    let startIdx = 0

    chartData.forEach((d, i) => {
      if (d.mechanism !== currentMech) {
        if (currentMech) {
          groups.push({
            mechanism: currentMech,
            startIdx,
            endIdx: i - 1,
            color: getMechanismColor(currentMech),
          })
        }
        currentMech = d.mechanism
        startIdx = i
      }
    })
    if (currentMech) {
      groups.push({
        mechanism: currentMech,
        startIdx,
        endIdx: chartData.length - 1,
        color: getMechanismColor(currentMech),
      })
    }
    return groups
  }, [chartData])

  const chartTitle = title || `${indication} Landscape: ${endpoint} Response`

  if (!data.length) {
    return (
      <div style={{
        padding: 24,
        textAlign: 'center',
        color: '#A09A92',
        background: '#161412',
        borderRadius: 12,
        border: '1px solid #2C2925',
      }}>
        No endpoint data available for {endpoint} in {indication}.
        <br />
        <span style={{ fontSize: 12 }}>
          Upload clinical trial results or run endpoint extraction to populate this chart.
        </span>
      </div>
    )
  }

  return (
    <div style={{
      background: '#161412',
      borderRadius: 12,
      border: '1px solid #2C2925',
      padding: '20px 16px 12px',
    }}>
      {/* Title */}
      <div style={{
        fontSize: 15,
        fontWeight: 600,
        color: '#F0EBE4',
        marginBottom: 4,
        paddingLeft: 8,
      }}>
        {chartTitle}
      </div>
      <div style={{
        fontSize: 12,
        color: '#A09A92',
        marginBottom: 16,
        paddingLeft: 8,
      }}>
        {endpoint} response rate ({valueUnit}) by drug, grouped by mechanism of action
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={chartData}
          margin={{ top: 10, right: 20, left: 10, bottom: 80 }}
          barCategoryGap="15%"
          barGap={1}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#2C2925"
            vertical={false}
          />
          <XAxis
            dataKey="label"
            tick={{
              fill: '#A09A92',
              fontSize: 10,
              dy: 5,
            }}
            angle={-45}
            textAnchor="end"
            interval={0}
            tickLine={false}
            axisLine={{ stroke: '#3D3A36' }}
            height={80}
          />
          <YAxis
            tick={{ fill: '#A09A92', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#3D3A36' }}
            domain={[0, 'auto']}
            tickFormatter={(v) => `${v}${valueUnit}`}
          >
            <Label
              value={`${endpoint} Response`}
              angle={-90}
              position="insideLeft"
              style={{ fill: '#A09A92', fontSize: 12 }}
              offset={-5}
            />
          </YAxis>
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />

          {/* Pbo-adjusted bars */}
          <Bar
            dataKey="pbo_adjusted"
            name="Pbo-adjusted"
            radius={[3, 3, 0, 0]}
          >
            {chartData.map((entry, idx) => (
              <Cell
                key={`pbo-${idx}`}
                fill={entry.color}
                stroke={highlightDrug && entry.drug === highlightDrug ? '#F0EBE4' : 'none'}
                strokeWidth={highlightDrug && entry.drug === highlightDrug ? 2 : 0}
              />
            ))}
          </Bar>

          {/* Absolute bars (lighter shade, behind) */}
          {showAbsolute && (
            <Bar
              dataKey="absolute"
              name="Absolute"
              radius={[3, 3, 0, 0]}
            >
              {chartData.map((entry, idx) => (
                <Cell
                  key={`abs-${idx}`}
                  fill={entry.absoluteColor}
                  stroke={highlightDrug && entry.drug === highlightDrug ? '#F0EBE4' : 'none'}
                  strokeWidth={highlightDrug && entry.drug === highlightDrug ? 2 : 0}
                />
              ))}
            </Bar>
          )}

          <Legend
            verticalAlign="top"
            height={30}
            wrapperStyle={{ color: '#A09A92', fontSize: 11 }}
          />
        </BarChart>
      </ResponsiveContainer>

      {/* Mechanism group labels */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        gap: 12,
        flexWrap: 'wrap',
        marginTop: 8,
        paddingTop: 8,
        borderTop: '1px solid #2C2925',
      }}>
        {mechanismGroups.map(g => (
          <div key={g.mechanism} style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            fontSize: 11,
            color: '#A09A92',
          }}>
            <span style={{
              width: 10,
              height: 10,
              borderRadius: 2,
              background: g.color,
              display: 'inline-block',
            }} />
            {g.mechanism}
          </div>
        ))}
      </div>

      {/* Notes */}
      <div style={{
        marginTop: 8,
        fontSize: 10,
        color: '#706B63',
        paddingLeft: 8,
      }}>
        Source: ClinicalTrials.gov, company presentations, published trial results.
        Values shown are placebo-adjusted (dark) and absolute (light) response rates.
      </div>
    </div>
  )
}
