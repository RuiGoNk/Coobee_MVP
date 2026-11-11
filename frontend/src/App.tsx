import { useEffect, useState } from 'react'
import { api, setToken, getToken, clearToken } from './api'
import Carousel from './Carousel'
import Tabs from './Tabs'

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
type Recipient = {
  id: string
  name: string
  relationship: string
  gender: string
  birth_date: string | null
  age: number | null
  occasion: string | null
  relationship_level: string | null
  budget_range: string | null
  details: Record<string, unknown> | null
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
  const [recipients, setRecipients] = useState<Recipient[]>([])
  const [selectedRecipient, setSelectedRecipient] = useState<Recipient | null>(null)
  const [mainTab, setMainTab] = useState<'recipients' | 'feed'>('recipients')

  useEffect(() => {
    if (stage !== 'authed') return
    api.me().then(setMe).catch(() => setMe(null))
    api.getProfile().then((p) => { setProfile(p as Profile | null); setProfileLoaded(true) })
      .catch(() => setProfileLoaded(true))
    api.listRecipients().then((r) => setRecipients(r as unknown as Recipient[])).catch(() => {})
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
    return <Onboarding onSaved={(p) => { setProfile(p); api.listRecipients().then((r) => setRecipients(r as unknown as Recipient[])).catch(() => {}) }} username={me?.username ?? null} />
  }

  if (selectedRecipient) {
    return <Carousel recipientId={selectedRecipient.id} recipientName={selectedRecipient.name}
      onBack={() => setSelectedRecipient(null)} />
  }

  return (
    <div style={{ maxWidth: 960, margin: '40px auto', fontFamily: 'system-ui', padding: 16 }}>
      <h1>CooBee</h1>
      <p>Вы вошли как @{me?.username ?? me?.telegram_id}.</p>

      <div style={{ display: 'flex', gap: 8, margin: '16px 0' }}>
        <button onClick={() => setMainTab('recipients')}
                style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #ccc',
                         background: mainTab === 'recipients' ? '#1f6feb' : '#fff',
                         color: mainTab === 'recipients' ? '#fff' : '#000' }}>
          Мои получатели
        </button>
        <button onClick={() => setMainTab('feed')}
                style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #ccc',
                         background: mainTab === 'feed' ? '#1f6feb' : '#fff',
                         color: mainTab === 'feed' ? '#fff' : '#000' }}>
          Для себя
        </button>
      </div>

      {mainTab === 'feed' && <Tabs />}

      {mainTab === 'recipients' && <>
        <h2 style={{ fontSize: 18, marginTop: 24 }}>Мои получатели</h2>
        {recipients.length === 0 && <p style={{ color: '#888' }}>Пока никого нет. Добавьте получателя ниже.</p>}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
          {recipients.map((r) => (
            <div key={r.id} style={{ border: '1px solid #eee', borderRadius: 12, padding: 12 }}>
              <div style={{ fontWeight: 600 }}>{r.name}</div>
              <div style={{ fontSize: 13, color: '#666' }}>{r.relationship}</div>
              <button onClick={() => setSelectedRecipient(r)} style={{ marginTop: 8, width: '100%', padding: 8 }}>Подобрать подарок</button>
            </div>
          ))}
        </div>

        <RecipientForm onCreated={(r) => setRecipients((rs) => [...rs, r])} />
      </>}

      <button onClick={() => { clearToken(); setStage('idle'); setMe(null); setProfile(null); setProfileLoaded(false); setRecipients([]); setMainTab('recipients') }}
        style={{ marginTop: 24 }}>Выйти</button>
    </div>
  )
}

function RecipientForm({ onCreated }: { onCreated: (r: Recipient) => void }) {
  const [name, setName] = useState('')
  const [relationship, setRelationship] = useState('mother')
  const [gender, setGender] = useState('unisex')
  const [mode, setMode] = useState<'date' | 'age'>('date')
  const [birthDate, setBirthDate] = useState('')
  const [age, setAge] = useState('')
  const [occasion, setOccasion] = useState('birthday')
  const [budget, setBudget] = useState('standard')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function submit() {
    setError(''); setSaving(true)
    try {
      const payload: Record<string, unknown> = { name, relationship, gender, occasion, budget_range: budget }
      if (mode === 'date' && birthDate) payload.birth_date = birthDate
      else if (mode === 'age' && age) payload.age = Number(age)
      else throw new Error('укажите дату или возраст')
      const r = await api.createRecipient(payload)
      onCreated(r as unknown as Recipient)
      setName(''); setBirthDate(''); setAge('')
    } catch (e) { setError(String(e)) } finally { setSaving(false) }
  }

  return (
    <div style={{ marginTop: 24, border: '1px solid #eee', borderRadius: 12, padding: 16 }}>
      <h2 style={{ fontSize: 18, marginTop: 0 }}>Добавить получателя</h2>
      <div style={{ display: 'grid', gap: 8 }}>
        <input placeholder="Имя" value={name} onChange={(e) => setName(e.target.value)} />
        <select value={relationship} onChange={(e) => setRelationship(e.target.value)}>
          {['mother', 'father', 'wife', 'husband', 'boyfriend', 'girlfriend', 'brother', 'sister', 'friend_m', 'friend_f', 'colleague', 'boss', 'child', 'other'].map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <select value={gender} onChange={(e) => setGender(e.target.value)}>
          <option value="unisex">унисекс</option>
          <option value="male">мужской</option>
          <option value="female">женский</option>
        </select>
        <div>
          <label><input type="radio" checked={mode === 'date'} onChange={() => setMode('date')} /> Дата рождения</label>
          <label style={{ marginLeft: 16 }}><input type="radio" checked={mode === 'age'} onChange={() => setMode('age')} /> Только возраст</label>
        </div>
        {mode === 'date'
          ? <input type="date" value={birthDate} onChange={(e) => setBirthDate(e.target.value)} />
          : <input type="number" min={0} max={120} placeholder="35" value={age} onChange={(e) => setAge(e.target.value)} />}
        <select value={occasion} onChange={(e) => setOccasion(e.target.value)}>
          {['birthday', 'new_year', 'feb23', 'mar8', 'wedding', 'anniversary', 'newborn', 'sep1', 'teacher_day', 'just_because', 'housewarming', 'other'].map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
        <select value={budget} onChange={(e) => setBudget(e.target.value)}>
          {BUDGETS.map((b) => <option key={b} value={b}>{b}</option>)}
        </select>
        {error && <p style={{ color: 'crimson', margin: 0 }}>{error}</p>}
        <button onClick={submit} disabled={saving || !name}>{saving ? 'Сохраняем…' : 'Добавить'}</button>
      </div>
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