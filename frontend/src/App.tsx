import { useEffect, useState } from 'react'
import { api, setToken, getToken, clearToken } from './api'

type Stage = 'idle' | 'waiting' | 'authed'

type Me = { id: string; telegram_id: number; username: string | null }
type Profile = {
  birth_date: string | null
  birth_year: number | null
  gender: string | null
  occupation: string | null
  interests: string[] | null
  style: string[] | null
  budget_range: string | null
  city: string | null
}

const OCCUPATIONS = ['it', 'creative', 'business', 'science', 'healthcare', 'services', 'blue_collar', 'finance', 'education', 'student', 'other']
const BUDGETS = ['symbolic', 'standard', 'solid', 'premium']
const INTERESTS = ['tech', 'gaming', 'books_fiction', 'books_nonfiction', 'coffee', 'cooking', 'travel', 'sport', 'art', 'music', 'cinema', 'fashion', 'beauty', 'home', 'gardening', 'pets', 'photography', 'science']

export default function App() {
  const [stage, setStage] = useState<Stage>(getToken() ? 'authed' : 'idle')
  const [deepLink, setDeepLink] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [error, setError] = useState('')
  const [me, setMe] = useState<Me | null>(null)
  const [profile, setProfile] = useState<Profile | null>(null)
  const [profileLoaded, setProfileLoaded] = useState(false)

  useEffect(() => {
    if (stage !== 'authed') return
    api.me().then(setMe).catch(() => setMe(null))
    api.getProfile().then((p) => { setProfile(p as Profile | null); setProfileLoaded(true) })
      .catch(() => setProfileLoaded(true))
  }, [stage])

  useEffect(() => {
    if (stage !== 'waiting' || !sessionId) return
    const timer = setInterval(async () => {
      try {
        const s = await api.getSession(sessionId)
        if (s.status === 'confirmed' && s.access_token) {
          setToken(s.access_token); clearInterval(timer); setStage('authed')
        } else if (s.status === 'expired') {
          clearInterval(timer); setError('Сессия истекла'); setStage('idle')
        }
      } catch (e) { clearInterval(timer); setError(String(e)); setStage('idle') }
    }, 2000)
    return () => clearInterval(timer)
  }, [stage, sessionId])

  async function startLogin() {
    setError('')
    try {
      const s = await api.createSession(); setSessionId(s.session_id); setDeepLink(s.deep_link); setStage('waiting')
    } catch (e) { setError(String(e)) }
  }

  if (stage === 'idle') {
    return (
      <div style={{ maxWidth: 480, margin: '40px auto', fontFamily: 'system-ui', textAlign: 'center' }}>
        <h1>CooBee</h1>
        <p>Рекомендательный сервис подарков</p>
        <button onClick={startLogin} style={{ padding: '12px 24px', fontSize: 16 }}>Войти через Telegram</button>
        {error && <p style={{ color: 'crimson' }}>{error}</p>}
      </div>
    )
  }

  if (stage === 'waiting') {
    return (
      <div style={{ maxWidth: 480, margin: '40px auto', fontFamily: 'system-ui', textAlign: 'center' }}>
        <h1>CooBee</h1>
        <p>Откройте Telegram и подтвердите вход:</p>
        <a href={deepLink} target="_blank" rel="noreferrer">{deepLink}</a>
        <p style={{ color: '#888' }}>Ждём подтверждения…</p>
      </div>
    )
  }

  if (!profileLoaded) return <div style={{ padding: 40 }}>Загрузка…</div>

  if (!profile) {
    return <Onboarding onSaved={(p) => setProfile(p)} username={me?.username ?? null} />
  }

  return (
    <div style={{ maxWidth: 480, margin: '40px auto', fontFamily: 'system-ui' }}>
      <h1>CooBee</h1>
      <p>Вы вошли как @{me?.username ?? me?.telegram_id}. Профиль заполнен.</p>
      <pre style={{ background: '#f4f4f4', padding: 12, borderRadius: 8 }}>{JSON.stringify(profile, null, 2)}</pre>
      <button onClick={() => { clearToken(); setStage('idle'); setMe(null); setProfile(null); setProfileLoaded(false) }}>Выйти</button>
    </div>
  )
}

function Onboarding({ onSaved, username }: { onSaved: (p: Profile) => void; username: string | null }) {
  const [mode, setMode] = useState<'date' | 'year'>('year')
  const [birthDate, setBirthDate] = useState('')
  const [birthYear, setBirthYear] = useState('')
  const [gender, setGender] = useState('')
  const [occupation, setOccupation] = useState('')
  const [budget, setBudget] = useState('standard')
  const [city, setCity] = useState('')
  const [interests, setInterests] = useState<string[]>([])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  function toggle(i: string) {
    setInterests((s) => s.includes(i) ? s.filter((x) => x !== i) : [...s, i])
  }

  async function save() {
    setError(''); setSaving(true)
    try {
      const payload: Record<string, unknown> = { gender: gender || null, occupation: occupation || null, budget_range: budget, city: city || null, interests }
      if (mode === 'date' && birthDate) payload.birth_date = birthDate
      else if (mode === 'year' && birthYear) payload.birth_year = Number(birthYear)
      else throw new Error('укажите дату или год рождения')
      const p = await api.putProfile(payload)
      onSaved(p as Profile)
    } catch (e) { setError(String(e)) } finally { setSaving(false) }
  }

  return (
    <div style={{ maxWidth: 560, margin: '40px auto', fontFamily: 'system-ui' }}>
      <h1>CooBee</h1>
      <p>Привет{username ? `, @${username}` : ''}! Расскажите о себе — так подбор будет точнее.</p>

      <fieldset style={{ marginBottom: 16 }}>
        <legend>Возраст</legend>
        <label><input type="radio" checked={mode === 'date'} onChange={() => setMode('date')} /> Дата рождения</label>
        <label style={{ marginLeft: 16 }}><input type="radio" checked={mode === 'year'} onChange={() => setMode('year')} /> Только год</label>
        <div style={{ marginTop: 8 }}>
          {mode === 'date'
            ? <input type="date" value={birthDate} onChange={(e) => setBirthDate(e.target.value)} />
            : <input type="number" min={1930} max={2012} placeholder="1990" value={birthYear} onChange={(e) => setBirthYear(e.target.value)} />}
        </div>
      </fieldset>

      <div style={{ marginBottom: 12 }}>
        <label>Пол:&nbsp;
          <select value={gender} onChange={(e) => setGender(e.target.value)}>
            <option value="">не указан</option>
            <option value="male">мужской</option>
            <option value="female">женский</option>
          </select>
        </label>
      </div>

      <div style={{ marginBottom: 12 }}>
        <label>Сфера:&nbsp;
          <select value={occupation} onChange={(e) => setOccupation(e.target.value)}>
            <option value="">не указана</option>
            {OCCUPATIONS.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        </label>
      </div>

      <div style={{ marginBottom: 12 }}>
        <label>Бюджет:&nbsp;
          <select value={budget} onChange={(e) => setBudget(e.target.value)}>
            {BUDGETS.map((b) => <option key={b} value={b}>{b}</option>)}
          </select>
        </label>
      </div>

      <div style={{ marginBottom: 12 }}>
        <label>Город: <input value={city} onChange={(e) => setCity(e.target.value)} placeholder="Москва" /></label>
      </div>

      <fieldset style={{ marginBottom: 16 }}>
        <legend>Интересы</legend>
        {INTERESTS.map((i) => (
          <label key={i} style={{ display: 'inline-block', marginRight: 12 }}>
            <input type="checkbox" checked={interests.includes(i)} onChange={() => toggle(i)} /> {i}
          </label>
        ))}
      </fieldset>

      {error && <p style={{ color: 'crimson' }}>{error}</p>}
      <button onClick={save} disabled={saving} style={{ padding: '10px 20px' }}>{saving ? 'Сохраняем…' : 'Сохранить'}</button>
    </div>
  )
}
