function InsightList({ title, items }) {
  if (!items?.length) {
    return null
  }

  return (
    <section className="ai-list">
      <h3>{title}</h3>
      <ul>
        {items.map((item, idx) => (
          <li key={`${title}-${idx}`}>{item}</li>
        ))}
      </ul>
    </section>
  )
}

export function AiInsightsCard({ insights }) {
  if (!insights) {
    return null
  }

  return (
    <section className="ai-card reveal reveal-5">
      <header className="card-header">
        <h2>AI deep insight</h2>
        <p>{insights.model || 'custom model'}</p>
      </header>

      {insights.status === 'ready' ? (
        <>
          <p className="ai-summary">{insights.summary}</p>
          <div className="ai-grid">
            <InsightList title="Strengths" items={insights.strengths} />
            <InsightList title="Risks" items={insights.risks} />
            <InsightList title="Recommendations" items={insights.recommendations} />
          </div>
        </>
      ) : (
        <p className="ai-status">{insights.detail || 'AI insights are unavailable for this query.'}</p>
      )}
    </section>
  )
}
