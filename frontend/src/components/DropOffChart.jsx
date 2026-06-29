import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const STAGE_LABELS = {
  INTRO: 'Intro',
  PERMISSION: 'Permission',
  COMPANY_INFO: 'Company Info',
  CALL_VOLUME: 'Call Volume',
  CURRENT_PROCESS: 'Current Process',
  PAIN_POINTS: 'Pain Points',
  BUDGET: 'Budget',
  TIMELINE: 'Timeline',
  LEAD_SCORING: 'Scoring',
  BOOKING: 'Booking',
}

export default function DropOffChart({ stages }) {
  const data = Object.entries(stages || {}).map(([stage, count]) => ({
    stage: STAGE_LABELS[stage] || stage,
    count,
  }))

  if (data.length === 0) {
    return <div className="empty-chart">No drop-off data yet</div>
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis type="number" tick={{ fontSize: 12 }} />
        <YAxis dataKey="stage" type="category" width={110} tick={{ fontSize: 11 }} />
        <Tooltip />
        <Bar dataKey="count" fill="#ef4444" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
