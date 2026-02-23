const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim() || ''

function buildUrl(pathname, params = {}) {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      query.set(key, String(value))
    }
  })

  const suffix = query.toString() ? `?${query.toString()}` : ''
  return `${API_BASE_URL}${pathname}${suffix}`
}

export async function fetchInsights(username, options = {}) {
  const trimmed = username.trim()
  if (!trimmed) {
    throw new Error('GitHub username is required.')
  }

  const transport = options.transport || 'httpx'
  const llm = Boolean(options.llm)
  const requestUrl = buildUrl(
    `/api/v1/insights/${encodeURIComponent(trimmed)}`,
    { transport, llm: llm ? 'true' : undefined },
  )

  const response = await fetch(requestUrl, {
    method: 'GET',
    signal: options.signal,
    headers: { Accept: 'application/json' },
  })

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}.`
    try {
      const payload = await response.json()
      if (payload?.detail && typeof payload.detail === 'string') {
        detail = payload.detail
      }
    } catch {
      // Ignore JSON parsing errors and return default detail.
    }
    throw new Error(detail)
  }

  return response.json()
}
