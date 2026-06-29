export default function MetricsCard({ title, value, accent }) {
  return (
    <div className={`metric-card ${accent ? `accent-${accent}` : ''}`}>
      <span className="metric-title">{title}</span>
      <span className="metric-value">{value}</span>
    </div>
  )
}
