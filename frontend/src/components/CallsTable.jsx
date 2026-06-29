export default function CallsTable({ calls }) {
  if (!calls || calls.length === 0) {
    return (
      <div className="chart-card full-width">
        <h3>Recent Calls</h3>
        <div className="empty-chart">No calls recorded yet</div>
      </div>
    )
  }

  return (
    <div className="chart-card full-width">
      <h3>Recent Calls</h3>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Company</th>
              <th>Status</th>
              <th>State</th>
              <th>Duration</th>
              <th>Score</th>
              <th>Tier</th>
              <th>Qualified</th>
              <th>Booked</th>
              <th>Latency</th>
              <th>Cost</th>
            </tr>
          </thead>
          <tbody>
            {calls.map(call => (
              <tr key={call.id}>
                <td>{call.lead_data?.company_name || call.lead_data?.name || '—'}</td>
                <td><span className={`badge badge-${call.status}`}>{call.status}</span></td>
                <td>{call.drop_off_stage || call.current_state}</td>
                <td>{call.duration_seconds ? `${Math.round(call.duration_seconds)}s` : '—'}</td>
                <td>{call.scoring?.total_score ?? '—'}</td>
                <td>{call.scoring?.tier ?? '—'}</td>
                <td>{call.qualified ? '✓' : '—'}</td>
                <td>{call.booked ? '✓' : '—'}</td>
                <td>{call.avg_latency_ms ? `${Math.round(call.avg_latency_ms)}ms` : '—'}</td>
                <td>{call.cost_usd ? `$${call.cost_usd}` : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
