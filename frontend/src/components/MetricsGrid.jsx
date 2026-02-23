import { formatNumber } from '../utils/formatters'

const METRIC_KEYS = [
  { key: 'total_stars', label: 'Total stars' },
  { key: 'total_forks', label: 'Total forks' },
  { key: 'followers', label: 'Followers' },
  { key: 'following', label: 'Following' },
  { key: 'public_repos', label: 'Public repos' },
  { key: 'score', label: 'OctoLens score' },
]

export function MetricsGrid({ metrics }) {
  return (
    <section className="metrics-card reveal reveal-4">
      <header className="card-header">
        <h2>Key metrics</h2>
        <p>
          Top language: <strong>{metrics.top_language}</strong>
        </p>
      </header>
      <div className="metrics-grid">
        {METRIC_KEYS.map((item) => (
          <article className="metric-tile" key={item.key}>
            <span>{item.label}</span>
            <strong>{formatNumber(metrics[item.key])}</strong>
          </article>
        ))}
      </div>
      <p className="metric-caption">
        Top repository: <strong>{metrics.top_repo_name}</strong> (
        {formatNumber(metrics.top_repo_stars)} stars)
      </p>
    </section>
  )
}

