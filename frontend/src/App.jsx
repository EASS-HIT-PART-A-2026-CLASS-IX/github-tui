import { useEffect, useMemo, useRef, useState } from 'react'
import { fetchInsights } from './api/client'
import { AiInsightsCard } from './components/AiInsightsCard'
import { MetricsGrid } from './components/MetricsGrid'
import { ProfileCard } from './components/ProfileCard'
import { RepoTable } from './components/RepoTable'
import { SearchForm } from './components/SearchForm'

const DEFAULT_USERNAME = 'openai'

function App() {
  const [username, setUsername] = useState(DEFAULT_USERNAME)
  const [transport, setTransport] = useState('httpx')
  const [llm, setLlm] = useState(true)
  const [snapshot, setSnapshot] = useState(null)
  const [error, setError] = useState('')
  const [lastQuery, setLastQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const abortRef = useRef(null)

  const repositories = useMemo(() => snapshot?.repositories ?? [], [snapshot])

  useEffect(() => {
    return () => {
      if (abortRef.current) {
        abortRef.current.abort()
      }
    }
  }, [])

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!username.trim()) {
      setError('Please enter a GitHub username.')
      return
    }

    if (abortRef.current) {
      abortRef.current.abort()
    }
    const controller = new AbortController()
    abortRef.current = controller

    setIsLoading(true)
    setError('')
    setLastQuery(username.trim())

    try {
      const data = await fetchInsights(username, {
        transport,
        llm,
        signal: controller.signal,
      })
      setSnapshot(data)
    } catch (requestError) {
      if (requestError.name !== 'AbortError') {
        setSnapshot(null)
        setError(requestError.message || 'Failed to load insights.')
      }
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null
      }
      setIsLoading(false)
    }
  }

  return (
    <div className="page-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <header className="hero reveal reveal-1">
        <p className="kicker">OctoLens Web</p>
        <h1>GitHub intelligence beyond the TUI</h1>
        <p>
          Search any public profile and inspect repository impact, language mix,
          and contribution signals from your existing Python backend.
        </p>
      </header>

      <SearchForm
        username={username}
        onUsernameChange={setUsername}
        transport={transport}
        onTransportChange={setTransport}
        llm={llm}
        onLlmChange={setLlm}
        isLoading={isLoading}
        onSubmit={handleSubmit}
      />

      {lastQuery ? (
        <p className="query-meta">
          Last query: <strong>@{lastQuery}</strong> using {transport} with AI{' '}
          {llm ? 'enabled' : 'disabled'}
        </p>
      ) : null}

      {error ? <p className="error-banner">{error}</p> : null}

      {snapshot ? (
        <main className="dashboard">
          <ProfileCard user={snapshot.user} />
          <MetricsGrid metrics={snapshot.metrics} />
          <AiInsightsCard insights={snapshot.ai_insights} />
          <RepoTable repositories={repositories} />
        </main>
      ) : (
        <section className="empty-state reveal reveal-3">
          <h2>Ready when you are</h2>
          <p>Run your first lookup to populate profile, metrics, and repo data.</p>
        </section>
      )}
    </div>
  )
}

export default App
