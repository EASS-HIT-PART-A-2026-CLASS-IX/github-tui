import { formatNumber } from '../utils/formatters'

export function ProfileCard({ user }) {
  return (
    <section className="profile-card reveal reveal-3">
      <div className="profile-header">
        {user.avatar_url ? (
          <img src={user.avatar_url} alt={`${user.login} avatar`} />
        ) : (
          <div className="avatar-fallback">{user.login.slice(0, 2)}</div>
        )}
        <div>
          <h2>{user.name || user.login}</h2>
          <p>@{user.login}</p>
        </div>
      </div>

      <dl className="profile-grid">
        <div>
          <dt>Location</dt>
          <dd>{user.location || '-'}</dd>
        </div>
        <div>
          <dt>Company</dt>
          <dd>{user.company || '-'}</dd>
        </div>
        <div>
          <dt>Joined</dt>
          <dd>{user.joined_date}</dd>
        </div>
        <div>
          <dt>Public repos</dt>
          <dd>{formatNumber(user.public_repos)}</dd>
        </div>
      </dl>

      {user.bio ? <p className="bio">{user.bio}</p> : null}
      {user.html_url ? (
        <a className="profile-link" href={user.html_url} target="_blank" rel="noreferrer">
          Open GitHub profile
        </a>
      ) : null}
    </section>
  )
}

