import { useState, useEffect } from 'react'
import { fetchDashboard } from '../api/client'
import MetricsCard from './MetricsCard'
import DropOffChart from './DropOffChart'
import CallsTable from './CallsTable'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [days, setDays] = useState(30)

  useEffect(() => {
    setLoading(true)
    fetchDashboard(days)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [days])

  if (loading) return <div className="loading">Loading analytics...</div>
  if (error) return <div className="error">Error: {error}</div>
  if (!data) return null

  const { metrics, time_series, recent_calls } = data

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div>
          <h1>Karta SDR</h1>
          <p className="subtitle">AI Voice Sales Development Analytics</p>
        </div>
        <select value={days} onChange={e => setDays(Number(e.target.value))} className="period-select">
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </header>

      <div className="metrics-grid">
        <MetricsCard title="Total Calls" value={metrics.total_calls} />
        <MetricsCard title="Qualification Rate" value={`${metrics.qualification_rate}%`} accent="green" />
        <MetricsCard title="Booking Rate" value={`${metrics.booking_rate}%`} accent="blue" />
        <MetricsCard title="Avg Duration" value={`${metrics.avg_duration_seconds}s`} />
        <MetricsCard title="Avg Latency" value={`${metrics.avg_latency_ms}ms`} accent={metrics.avg_latency_ms < 500 ? 'green' : 'orange'} />
        <MetricsCard title="Completion Rate" value={`${metrics.completion_rate}%`} />
        <MetricsCard title="Cost / Conversation" value={`$${metrics.cost_per_conversation}`} />
        <MetricsCard title="Active Sessions" value={metrics.active_sessions} accent="purple" />
      </div>

      <div className="charts-row">
        <div className="chart-card">
          <h3>Call Volume & Qualification</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={time_series}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="calls" stroke="#6366f1" strokeWidth={2} name="Calls" />
              <Line type="monotone" dataKey="qualified" stroke="#22c55e" strokeWidth={2} name="Qualified" />
              <Line type="monotone" dataKey="booked" stroke="#3b82f6" strokeWidth={2} name="Booked" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Drop-off by Stage</h3>
          <DropOffChart stages={metrics.drop_off_stages} />
        </div>
      </div>

      <div className="chart-card full-width">
        <h3>Latency Trend</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={time_series}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} unit="ms" />
            <Tooltip />
            <Line type="monotone" dataKey="avg_latency_ms" stroke="#f59e0b" strokeWidth={2} name="Avg Latency (ms)" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <CallsTable calls={recent_calls} />
    </div>
  )
}
