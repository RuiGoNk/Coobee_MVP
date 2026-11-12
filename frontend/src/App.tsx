import { useEffect, useState } from 'react'
import { api, setToken, getToken, clearToken } from './api'
import Tabs from './Tabs'
import RecipientProfile from './RecipientProfile'
import MyProfile from './MyProfile'

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
  notifications_enabled: boolean
}

const OCCUPATIONS = ['it', 'creative', 'business', 'science', 'healthcare', 'services', 'blue_collar', 'finance', 'education', 'student', 'other']
const BUDGETS = ['symbolic', 'standard', 'solid', 'premium']
const INTERESTS = ['tech', 'gaming', 'books_fiction', 'books_nonfiction', 'coffee', 'cooking', 'travel', 'sport', 'art', 'music', 'cinema', 'fashion', 'beauty', 'home', 'gardening', 'pets', 'photography', 'science']

const RELATIONSHIP_LABELS: Record<string, string> = {
  mother: 'мама', father: 'папа', wife: 'жена', husband: 'муж',
  boyfriend: 'парень', girlfriend: 'девушка', brother: 'брат', sister: 'сестра',
  friend_m: 'друг', friend_f: 'подруга', colleague: 'коллега', boss: 'начальник',
  child: 'ребёнок', other: 'другое',
}

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
  const [showAddForm, setShowAddForm] = useState(false)
  const [showMyProfile, setShowMyProfile] = useState(false)

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
      <div className="max-w-md mx-auto mt-20 px-6 text-center">
        <h1 className="text-3xl font-bold mb-2">CooBee</h1>
        <p className="text-gray-500 mb-8">Рекомендательный сервис подарков</p>
        <button onClick={startLogin} className="px-6 py-3 rounded-xl bg-blue-600 text-white font-medium active:scale-95">
          Войти через Telegram
        </button>
        {error && <p className="text-red-600 mt-4">{error}</p>}
      </div>
    )
  }

  if (stage === 'waiting') {
    return (
      <div className="max-w-md mx-auto mt-20 px-6 text-center">
        <h1 className="text-3xl font-bold mb-2">CooBee</h1>
        <p className="text-gray-600 mb-6">Подтвердите вход в Telegram</p>
        <a href={deepLink} target="_blank" rel="noreferrer"
           className="inline-block px-6 py-3 rounded-xl bg-blue-600 text-white font-medium active:scale-95">
          Открыть Telegram
        </a>
        <div className="mt-4 text-sm text-gray-500">
          Не открылось?{' '}
          <button onClick={() => { navigator.clipboard.writeText(deepLink); }}
                  className="text-blue-600 underline">
            Скопировать ссылку
          </button>
        </div>
        <p className="text-gray-400 mt-6">Ждём подтверждения…</p>
      </div>
    )
  }

  if (!profileLoaded) return <div className="p-10 text-center text-gray-500">Загрузка…</div>

  if (!profile) {
    return <Onboarding onSaved={(p) => { setProfile(p); api.listRecipients().then((r) => setRecipients(r as unknown as Recipient[])).catch(() => {}) }} username={me?.username ?? null} />
  }

  if (selectedRecipient) {
    return (
      <RecipientProfile
        recipient={selectedRecipient}
        relationshipLabel={RELATIONSHIP_LABELS[selectedRecipient.relationship] ?? selectedRecipient.relationship}
        onBack={() => setSelectedRecipient(null)}
        onUpdated={(r) => {
          setSelectedRecipient(r)
          setRecipients((rs) => rs.map((x) => x.id === r.id ? r : x))
        }}
      />
    )
  }

  if (showMyProfile && profile) {
    return (
      <div className="max-w-2xl mx-auto p-4">
        <button onClick={() => setShowMyProfile(false)} className="text-sm text-gray-600 mb-4">← Назад</button>
        <h1 className="text-xl font-bold mb-4">Мой профиль</h1>
        <MyProfile profile={profile} onUpdated={(p) => setProfile(p)} />
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto p-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">CooBee</h1>
          <p className="text-sm text-gray-500">@{me?.username ?? me?.telegram_id}</p>
        </div>
        <button onClick={() => setShowMyProfile(true)}
                className="w-10 h-10 rounded-full bg-blue-100 text-blue-600 font-bold flex items-center justify-center active:scale-95"
                aria-label="Мой профиль">
          {(me?.username ?? 'U').charAt(0).toUpperCase()}
        </button>
      </div>

      <div className="flex flex-wrap gap-2 my-4">
        <button onClick={() => setMainTab('recipients')}
                className={`px-4 py-2 rounded-lg text-sm font-medium ${mainTab === 'recipients' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>
          Мои получатели
        </button>
        <button onClick={() => setMainTab('feed')}
                className={`px-4 py-2 rounded-lg text-sm font-medium ${mainTab === 'feed' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>
          Для себя
        </button>
      </div>

      {mainTab === 'feed' && <Tabs />}

      {mainTab === 'recipients' && <>
        <div className="flex items-center justify-between mt-6 mb-3">
          <h2 className="text-lg font-semibold">Мои получатели</h2>
          <button onClick={() => setShowAddForm(true)}
                  className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm active:scale-95">
            + Добавить получателя
          </button>
        </div>

        {recipients.length === 0 && <p className="text-gray-500">Пока никого нет.</p>}

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {recipients.map((r) => (
            <button key={r.id} onClick={() => setSelectedRecipient(r)}
                    className="text-left border border-gray-200 rounded-xl p-4 bg-white hover:shadow-md active:scale-95 transition">
              <div className="font-semibold">{r.name}</div>
              <div className="text-xs text-gray-500 mt-1">{RELATIONSHIP_LABELS[r.relationship] ?? r.relationship}</div>
            </button>
          ))}
        </div>

        {showAddForm && (
          <RecipientForm
            onCreated={(r) => { setRecipients((rs) => [...rs, r]); setShowAddForm(false) }}
            onCancel={() => setShowAddForm(false)}
          />
        )}
      </>}

      <button onClick={() => { clearToken(); setStage('idle'); setMe(null); setProfile(null); setProfileLoaded(false); setRecipients([]); setMainTab('recipients') }}
              className="mt-8 text-sm text-gray-500 underline">
        Выйти
      </button>
    </div>
  )
}

function RecipientForm({ onCreated, onCancel }: { onCreated: (r: Recipient) => void; onCancel: () => void }) {
  const [name, setName] = useState('')
  const [relationship, setRelationship] = useState('mother')
  const [gender, setGender] = useState('unisex')
  const [mode, setMode] = useState<'date' | 'age'>('date')
  const [birthDate, setBirthDate] = useState('')
  const [age, setAge] = useState('')
  const [occasion, setOccasion] = useState('birthday')
  const [budget, setBudget] = useState('standard')
  const [notify, setNotify] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function submit() {
    setError(''); setSaving(true)
    try {
      const payload: Record<string, unknown> = {
        name, relationship, gender, occasion, budget_range: budget, notifications_enabled: notify,
      }
      if (mode === 'date' && birthDate) payload.birth_date = birthDate
      else if (mode === 'age' && age) payload.age = Number(age)
      else throw new Error('укажите дату или возраст')
      const r = await api.createRecipient(payload)
      onCreated(r as unknown as Recipient)
    } catch (e) { setError(String(e)) } finally { setSaving(false) }
  }

  return (
    <div className="mt-6 border border-gray-200 rounded-xl p-4 bg-white">
      <h2 className="text-lg font-semibold mb-3">Добавить получателя</h2>
      <div className="grid gap-3">
        <input placeholder="Имя" value={name} onChange={(e) => setName(e.target.value)}
               className="border border-gray-300 rounded-lg px-3 py-2" />
        <select value={relationship} onChange={(e) => setRelationship(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2">
          {Object.entries(RELATIONSHIP_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={gender} onChange={(e) => setGender(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2">
          <option value="unisex">унисекс</option>
          <option value="male">мужской</option>
          <option value="female">женский</option>
        </select>
        <div className="flex gap-4 text-sm">
          <label><input type="radio" checked={mode === 'date'} onChange={() => setMode('date')} /> Дата рождения</label>
          <label><input type="radio" checked={mode === 'age'} onChange={() => setMode('age')} /> Только возраст</label>
        </div>
        {mode === 'date'
          ? <input type="date" value={birthDate} onChange={(e) => setBirthDate(e.target.value)}
                   className="border border-gray-300 rounded-lg px-3 py-2" />
          : <input type="number" min={0} max={120} placeholder="35" value={age} onChange={(e) => setAge(e.target.value)}
                   className="border border-gray-300 rounded-lg px-3 py-2" />}
        <select value={occasion} onChange={(e) => setOccasion(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2">
          <option value="birthday">День рождения</option>
          <option value="new_year">Новый год</option>
          <option value="feb23">23 февраля</option>
          <option value="mar8">8 марта</option>
          <option value="wedding">Свадьба</option>
          <option value="anniversary">Годовщина</option>
          <option value="newborn">Рождение ребёнка</option>
          <option value="sep1">1 сентября</option>
          <option value="teacher_day">День учителя</option>
          <option value="just_because">Просто так</option>
          <option value="housewarming">Новоселье</option>
          <option value="other">Другое</option>
        </select>
        <select value={budget} onChange={(e) => setBudget(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2">
          <option value="symbolic">символический (до 1000)</option>
          <option value="standard">стандартный (1000–5000)</option>
          <option value="solid">солидный (5000–15000)</option>
          <option value="premium">премиум (15000+)</option>
        </select>
        <label className="text-sm">
          <input type="checkbox" checked={notify} onChange={(e) => setNotify(e.target.checked)} /> Напоминать о праздниках
        </label>
        {error && <p className="text-red-600 text-sm">{error}</p>}
        <div className="flex gap-2">
          <button onClick={onCancel} className="flex-1 py-2 rounded-lg border border-gray-300">Отмена</button>
          <button onClick={submit} disabled={saving || !name}
                  className="flex-1 py-2 rounded-lg bg-blue-600 text-white disabled:opacity-60">
            {saving ? 'Сохраняем…' : 'Добавить'}
          </button>
        </div>
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
    <div className="max-w-xl mx-auto p-4">
      <h1 className="text-2xl font-bold">CooBee</h1>
      <p className="text-gray-600 mb-4">Привет{username ? `, @${username}` : ''}! Расскажите о себе — так подбор будет точнее.</p>

      <fieldset className="mb-4 border border-gray-200 rounded-xl p-4">
        <legend className="px-2 text-sm text-gray-600">Возраст</legend>
        <div className="flex gap-4 text-sm mb-2">
          <label><input type="radio" checked={mode === 'date'} onChange={() => setMode('date')} /> Дата рождения</label>
          <label><input type="radio" checked={mode === 'year'} onChange={() => setMode('year')} /> Только год</label>
        </div>
        {mode === 'date'
          ? <input type="date" value={birthDate} onChange={(e) => setBirthDate(e.target.value)}
                   className="border border-gray-300 rounded-lg px-3 py-2" />
          : <input type="number" min={1930} max={2012} placeholder="1990" value={birthYear} onChange={(e) => setBirthYear(e.target.value)}
                   className="border border-gray-300 rounded-lg px-3 py-2" />}
      </fieldset>

      <div className="grid gap-3">
        <select value={gender} onChange={(e) => setGender(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2">
          <option value="">пол не указан</option>
          <option value="male">мужской</option>
          <option value="female">женский</option>
        </select>
        <select value={occupation} onChange={(e) => setOccupation(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2">
          <option value="">сфера не указана</option>
          {OCCUPATIONS.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
        <select value={budget} onChange={(e) => setBudget(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2">
          {BUDGETS.map((b) => <option key={b} value={b}>{b}</option>)}
        </select>
        <input value={city} onChange={(e) => setCity(e.target.value)} placeholder="Город"
               className="border border-gray-300 rounded-lg px-3 py-2" />
      </div>

      <fieldset className="my-4 border border-gray-200 rounded-xl p-4">
        <legend className="px-2 text-sm text-gray-600">Интересы</legend>
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {INTERESTS.map((i) => (
            <label key={i} className="text-sm">
              <input type="checkbox" checked={interests.includes(i)} onChange={() => toggle(i)} /> {i}
            </label>
          ))}
        </div>
      </fieldset>

      {error && <p className="text-red-600 text-sm mb-2">{error}</p>}
      <button onClick={save} disabled={saving}
              className="px-5 py-2 rounded-lg bg-blue-600 text-white disabled:opacity-60">
        {saving ? 'Сохраняем…' : 'Сохранить'}
      </button>
    </div>
  )
}