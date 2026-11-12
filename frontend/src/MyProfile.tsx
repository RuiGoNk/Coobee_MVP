import { useState } from 'react'
import { api } from './api'

export type Profile = {
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
const BUDGETS: Array<{ code: string; label: string }> = [
  { code: 'symbolic', label: 'символический (до 1000)' },
  { code: 'standard', label: 'стандартный (1000–5000)' },
  { code: 'solid', label: 'солидный (5000–15000)' },
  { code: 'premium', label: 'премиум (15000+)' },
]
const INTERESTS = ['tech', 'gaming', 'books_fiction', 'books_nonfiction', 'coffee', 'cooking', 'travel', 'sport', 'art', 'music', 'cinema', 'fashion', 'beauty', 'home', 'gardening', 'pets', 'photography', 'science']

const BUDGET_LABELS: Record<string, string> = Object.fromEntries(BUDGETS.map((b) => [b.code, b.label]))
const OCC_LABELS: Record<string, string> = {
  it: 'IT', creative: 'творчество/медиа', business: 'бизнес/управление', science: 'наука/образование',
  healthcare: 'здравоохранение', services: 'услуги', blue_collar: 'рабочие специальности',
  finance: 'финансы', education: 'образование', student: 'студент', other: 'другое',
}

type Props = {
  profile: Profile
  onUpdated: (p: Profile) => void
}

export default function MyProfile({ profile, onUpdated }: Props) {
  const [tab, setTab] = useState<'view' | 'edit'>('view')
  const [mode, setMode] = useState<'date' | 'year'>(profile.birth_date ? 'date' : 'year')
  const [birthDate, setBirthDate] = useState(profile.birth_date ?? '')
  const [birthYear, setBirthYear] = useState(profile.birth_year?.toString() ?? '')
  const [gender, setGender] = useState(profile.gender ?? '')
  const [occupation, setOccupation] = useState(profile.occupation ?? '')
  const [budget, setBudget] = useState(profile.budget_range ?? 'standard')
  const [city, setCity] = useState(profile.city ?? '')
  const [interests, setInterests] = useState<string[]>(profile.interests ?? [])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  function toggle(i: string) {
    setInterests((s) => s.includes(i) ? s.filter((x) => x !== i) : [...s, i])
  }

  async function save() {
    setError(''); setSaving(true)
    try {
      const payload: Record<string, unknown> = {
        gender: gender || null,
        occupation: occupation || null,
        budget_range: budget,
        city: city || null,
        interests,
      }
      if (mode === 'date' && birthDate) payload.birth_date = birthDate
      else if (mode === 'year' && birthYear) payload.birth_year = Number(birthYear)
      else throw new Error('укажите дату или год рождения')
      const p = await api.putProfile(payload)
      onUpdated(p as unknown as Profile)
      setTab('view')
    } catch (e) { setError(String(e)) } finally { setSaving(false) }
  }

  const ageLabel = profile.birth_date
    ? `д.р. ${profile.birth_date}`
    : profile.birth_year ? `год рождения ${profile.birth_year}` : '—'

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex gap-2 mb-4">
        <button onClick={() => setTab('view')}
                className={`px-3 py-1.5 rounded-lg text-sm ${tab === 'view' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>Профиль</button>
        <button onClick={() => setTab('edit')}
                className={`px-3 py-1.5 rounded-lg text-sm ${tab === 'edit' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>Редактировать</button>
      </div>

      {tab === 'view' && (
        <div className="border border-gray-200 rounded-xl p-4 text-sm space-y-1">
          <div><span className="text-gray-500">Возраст:</span> {ageLabel}</div>
          <div><span className="text-gray-500">Пол:</span> {profile.gender ?? '—'}</div>
          <div><span className="text-gray-500">Сфера:</span> {profile.occupation ? (OCC_LABELS[profile.occupation] ?? profile.occupation) : '—'}</div>
          <div><span className="text-gray-500">Бюджет:</span> {profile.budget_range ? (BUDGET_LABELS[profile.budget_range] ?? profile.budget_range) : '—'}</div>
          <div><span className="text-gray-500">Город:</span> {profile.city ?? '—'}</div>
          <div><span className="text-gray-500">Интересы:</span> {(profile.interests ?? []).join(', ') || '—'}</div>
        </div>
      )}

      {tab === 'edit' && (
        <div className="grid gap-3">
          <fieldset className="border border-gray-200 rounded-xl p-3">
            <legend className="px-2 text-sm text-gray-600">Возраст</legend>
            <div className="flex gap-4 text-sm mb-2">
              <label><input type="radio" checked={mode === 'date'} onChange={() => setMode('date')} /> Дата рождения</label>
              <label><input type="radio" checked={mode === 'year'} onChange={() => setMode('year')} /> Только год</label>
            </div>
            {mode === 'date'
              ? <input type="date" value={birthDate} onChange={(e) => setBirthDate(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-2" />
              : <input type="number" min={1930} max={2012} value={birthYear} onChange={(e) => setBirthYear(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-2" />}
          </fieldset>

          <select value={gender} onChange={(e) => setGender(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-2">
            <option value="">пол не указан</option>
            <option value="male">мужской</option>
            <option value="female">женский</option>
          </select>
          <select value={occupation} onChange={(e) => setOccupation(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-2">
            <option value="">сфера не указана</option>
            {OCCUPATIONS.map((o) => <option key={o} value={o}>{OCC_LABELS[o] ?? o}</option>)}
          </select>
          <select value={budget} onChange={(e) => setBudget(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-2">
            {BUDGETS.map((b) => <option key={b.code} value={b.code}>{b.label}</option>)}
          </select>
          <input value={city} onChange={(e) => setCity(e.target.value)} placeholder="Город" className="border border-gray-300 rounded-lg px-3 py-2" />

          <fieldset className="border border-gray-200 rounded-xl p-3">
            <legend className="px-2 text-sm text-gray-600">Интересы</legend>
            <div className="flex flex-wrap gap-x-4 gap-y-1">
              {INTERESTS.map((i) => (
                <label key={i} className="text-sm">
                  <input type="checkbox" checked={interests.includes(i)} onChange={() => toggle(i)} /> {i}
                </label>
              ))}
            </div>
          </fieldset>

          {error && <p className="text-red-600 text-sm">{error}</p>}
          <div className="flex gap-2">
            <button onClick={() => setTab('view')} className="flex-1 py-2 rounded-lg border border-gray-300">Отмена</button>
            <button onClick={save} disabled={saving} className="flex-1 py-2 rounded-lg bg-blue-600 text-white disabled:opacity-60">
              {saving ? 'Сохраняем…' : 'Сохранить'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}