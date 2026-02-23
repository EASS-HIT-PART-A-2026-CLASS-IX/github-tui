import { formatDate, formatNumber } from '../utils/formatters'

export function RepoTable({ repositories }) {
  return (
    <section className="repos-card reveal reveal-5">
      <header className="card-header">
        <h2>Repositories</h2>
        <p>{formatNumber(repositories.length)} scanned</p>
      </header>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Repository</th>
              <th>Stars</th>
              <th>Forks</th>
              <th>Issues</th>
              <th>Language</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {repositories.map((repo) => (
              <tr key={repo.name}>
                <td>
                  {repo.html_url ? (
                    <a href={repo.html_url} target="_blank" rel="noreferrer">
                      {repo.name}
                    </a>
                  ) : (
                    repo.name
                  )}
                </td>
                <td>{formatNumber(repo.stars)}</td>
                <td>{formatNumber(repo.forks)}</td>
                <td>{formatNumber(repo.open_issues)}</td>
                <td>{repo.language}</td>
                <td>{formatDate(repo.updated_date)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

