export function SearchForm({
  username,
  onUsernameChange,
  transport,
  onTransportChange,
  llm,
  onLlmChange,
  isLoading,
  onSubmit,
}) {
  return (
    <form className="query-panel reveal reveal-2" onSubmit={onSubmit}>
      <label className="field">
        <span className="field-label">GitHub handle</span>
        <input
          name="username"
          type="text"
          value={username}
          onChange={(event) => onUsernameChange(event.target.value)}
          placeholder="openai, torvalds, microsoft..."
          autoComplete="off"
          required
        />
      </label>

      <label className="field compact">
        <span className="field-label">Transport</span>
        <select
          name="transport"
          value={transport}
          onChange={(event) => onTransportChange(event.target.value)}
          disabled={isLoading}
        >
          <option value="httpx">httpx</option>
          <option value="curl">curl</option>
        </select>
      </label>

      <label className="field compact">
        <span className="field-label">AI deep insight</span>
        <select
          name="llm"
          value={llm ? 'on' : 'off'}
          onChange={(event) => onLlmChange(event.target.value === 'on')}
          disabled={isLoading}
        >
          <option value="on">enabled</option>
          <option value="off">disabled</option>
        </select>
      </label>

      <button className="primary-button" type="submit" disabled={isLoading}>
        {isLoading ? 'Loading...' : 'Load insights'}
      </button>
    </form>
  )
}
