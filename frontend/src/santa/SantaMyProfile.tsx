import { useEffect, useState } from 'react'
import { api } from '../api'
import type {
  SantaParticipant,
  SantaPrefill,
  SantaPreview,
  SantaRoom,
  SantaVisibilityMode,
} from '../types'

type Props = {
  roomId: string
  room: SantaRoom
  onSaved: () => void
  onBack: () => void
}

const INTERESTS_OPTIONS = [
  'tech', 'gaming', 'books_fiction', 'books_nonfiction', 'coffee', 'cooking',
  'travel', 'sport', 'art', 'music', 'cinema', 'fashion', 'beauty', 'home',
  'gardening', 'pets', 'photography', 'science',
]

const GENDER_OPTIONS = [
  { value: 'male', label: 'Мужской' },
  { value: 'female', label: 'Женский' },
  { value: 'other', label: 'Другой' },
  { value: 'prefer_not_to_say', label: 'Не указывать' },
]

const VISIBILITY_FIELDS: Array<{ key: string; label: string }> = [
  { key: 'gender', label: 'Пол' },
  { key: 'age', label: 'Возраст' },
  { key: 'interests', label: 'Интересы' },
  { key: 'antipathies', label: 'Антипатии' },
  { key: 'allergies', label: 'Аллергии' },
  { key: 'constraints', label: 'Ограничения' },
  { key: 'hobbies', label: 'Хобби' },
  { key: 'brands', label: 'Бренды' },
  { key: 'sizes', label: 'Размеры' },
]

export default function SantaMyProfile({ roomId, room, onSaved, onBack }: Props) {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [preview, setPreview] = useState<SantaPreview | null>(null)

  // Анкета
  const [displayName, setDisplayName] = useState('')
  const [gender, setGender] = useState('prefer_not_to_say')
  const [ageMode, setAgeMode] = useState<'date' | 'age'>('age')
  const [birthDate, setBirthDate] = useState('')
  const [age, setAge] = useState('')
  const [interests, setInterests] = useState<string[]>([])
  const [antipathies, setAntipathies] = useState('')
  const [allergies, setAllergies] = useState('')
  const [constraints, setConstraints] = useState('')
  const [hobbies, setHobbies] = useState('')
  const [brands, setBrands] = useState('')

  // Visibility
  const [visibility, setVisibility] = useState<Record<string, SantaVisibilityMode>>({})

  useEffect(() => {
    let alive = true
    async function load() {
      setLoading(true)
      try {
        const prefill: SantaPrefill = await api.santa.prefill(roomId)
        const fromProfile = (prefill.from_profile ?? {}) as Record<string, unknown>

        if (!alive) return
        setGender(String(fromProfile.gender ?? 'prefer_not_to_say'))
        const bd = fromProfile.birth_date
        if (typeof bd === 'string' && bd) {
          setAgeMode('date')
          setBirthDate(bd)
        } else {
          setAgeMode('age')
          setAge(fromProfile.age ? String(fromProfile.age) : '')
        }
        const ints = (fromProfile.interests as string[]) ?? []
        setInterests(ints)
        setDisplayName(String(fromProfile.display_name ?? ''))

        // visibility — из suggested (по политике комнаты)
        setVisibility(prefill.suggested_visibility ?? {})

        const prev = await api.santa.preview(roomId).catch(() => null)
        if (alive) setPreview(prev)
      } catch (e) {
        if (alive) setError(String(e))
      } finally {
        if (alive) setLoading(false)
      }
    }
    load()
    return () => {
      alive = false
    }
  }, [roomId])

  function toggleInterest(i: string) {
    setInterests((prev) => (prev.includes(i) ? prev.filter((x) => x !== i) : [...prev, i]))
  }

  async function save() {
    setError('')
    setSaving(true)
    try {
      const payload: Record<string, unknown> = {
        display_name: displayName.trim() || undefined,
        gender,
        interests,
        antipathies: antipathies || null,
        allergies: allergies || null,
        constraints: constraints || null,
        hobbies: hobbies || null,
        brands: brands || null,
        visibility,
      }
      if (ageMode === 'date' && birthDate) {
        payload.birth_date = birthDate
      } else if (ageMode === 'age' && age) {
        payload.age = Number(age)
      } else {
        throw new Error('Укажите дату рождения или возраст')
      }

      await api.santa.updateMyProfile(roomId, payload)
      const prev = await api.santa.preview(roomId).catch(() => null)
      setPreview(prev)
      onSaved()
    } catch (e) {
      setError(String(e))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="max-w-2xl mx-auto p-8 text-center santa-muted">Загрузка…</div>
  }

  return (
    <div className="max-w-2xl mx-auto p-4">
      <button onClick={onBack} className="santa-btn santa-btn-ghost mb-3">
        ← Назад в комнату
      </button>

      <div className="santa-card">
        <h1 className="text-2xl font-bold mb-1">Мой профиль в комнате</h1>
        <p className="santa-muted text-sm mb-4">
          Заполните анкету — так Санта точнее подберёт подарок. Видимость каждого поля
          можно настроить ниже.
        </p>

        {/* Имя */}
        <label className="block mb-4">
          <span className="block text-sm font-medium mb-1">Как к вам обращаться</span>
          <input
            className="santa-input"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Имя"
          />
        </label>

        {/* Пол */}
        <div className="mb-4">
          <div className="text-sm font-medium mb-1">Пол</div>
          <div className="flex flex-wrap gap-2">
            {GENDER_OPTIONS.map((o) => (
              <button
                key={o.value}
                type="button"
                onClick={() => setGender(o.value)}
                className={`px-3 py-1.5 rounded-lg text-sm border ${
                  gender === o.value
                    ? 'border-[var(--santa-primary)] bg-[var(--santa-primary-soft)]'
                    : 'border-[var(--santa-border)]'
                }`}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>

        {/* Возраст */}
        <div className="mb-4">
          <div className="text-sm font-medium mb-2">Возраст (14–120)</div>
          <div className="flex gap-2 mb-2">
            <button
              type="button"
              onClick={() => setAgeMode('date')}
              className={`px-3 py-1.5 rounded-lg text-sm border ${
                ageMode === 'date'
                  ? 'border-[var(--santa-primary)] bg-[var(--santa-primary-soft)]'
                  : 'border-[var(--santa-border)]'
              }`}
            >
              Дата рождения
            </button>
            <button
              type="button"
              onClick={() => setAgeMode('age')}
              className={`px-3 py-1.5 rounded-lg text-sm border ${
                ageMode === 'age'
                  ? 'border-[var(--santa-primary)] bg-[var(--santa-primary-soft)]'
                  : 'border-[var(--santa-border)]'
              }`}
            >
              Только возраст
            </button>
          </div>
          {ageMode === 'date' ? (
            <input
              type="date"
              className="santa-input"
              value={birthDate}
              onChange={(e) => setBirthDate(e.target.value)}
            />
          ) : (
            <input
              type="number"
              min={14}
              max={120}
              className="santa-input"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              placeholder="Например, 30"
            />
          )}
        </div>

        {/* Интересы */}
        <div className="mb-4">
          <div className="text-sm font-medium mb-2">Интересы (мин. 1)</div>
          <div className="flex flex-wrap gap-2">
            {INTERESTS_OPTIONS.map((i) => (
              <button
                key={i}
                type="button"
                onClick={() => toggleInterest(i)}
                className={`px-3 py-1.5 rounded-full text-sm border ${
                  interests.includes(i)
                    ? 'border-[var(--santa-primary)] bg-[var(--santa-primary)] text-white'
                    : 'border-[var(--santa-border)]'
                }`}
              >
                {i}
              </button>
            ))}
          </div>
        </div>

        {/* Текстовые поля */}
        <div className="grid gap-3 mb-4">
          <label className="block">
            <span className="block text-sm font-medium mb-1">Антипатии (что не любите)</span>
            <input
              className="santa-input"
              value={antipathies}
              onChange={(e) => setAntipathies(e.target.value)}
              placeholder="Например: сладкое, парфюм"
            />
          </label>
          <label className="block">
            <span className="block text-sm font-medium mb-1">Аллергии / диета</span>
            <input
              className="santa-input"
              value={allergies}
              onChange={(e) => setAllergies(e.target.value)}
            />
          </label>
          <label className="block">
            <span className="block text-sm font-medium mb-1">Религиозные / культурные ограничения</span>
            <input
              className="santa-input"
              value={constraints}
              onChange={(e) => setConstraints(e.target.value)}
            />
          </label>
          <label className="block">
            <span className="block text-sm font-medium mb-1">Хобби</span>
            <input
              className="santa-input"
              value={hobbies}
              onChange={(e) => setHobbies(e.target.value)}
            />
          </label>
          <label className="block">
            <span className="block text-sm font-medium mb-1">Любимые бренды</span>
            <input
              className="santa-input"
              value={brands}
              onChange={(e) => setBrands(e.target.value)}
            />
          </label>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-[var(--santa-accent-soft)] text-[var(--santa-accent)] text-sm">
            {error}
          </div>
        )}

        <button className="santa-btn santa-btn-primary" onClick={save} disabled={saving}>
          {saving ? 'Сохраняем…' : 'Сохранить'}
        </button>
      </div>

      {/* Visibility */}
      <div className="santa-card mt-4">
        <h2 className="font-bold mb-2">Что видит ваш Санта</h2>
        <p className="santa-muted text-sm mb-3">
          Чем больше откроете — тем точнее подборка. Скрытые поля не участвуют в
          генерации идей.
        </p>
        <div className="space-y-2">
          {VISIBILITY_FIELDS.map((f) => (
            <div key={f.key} className="flex items-center justify-between gap-3 py-2 border-b border-[var(--santa-border)] last:border-0">
              <span className="text-sm">{f.label}</span>
              <select
                className="santa-input w-auto"
                value={visibility[f.key] ?? 'full'}
                onChange={(e) =>
                  setVisibility((v) => ({ ...v, [f.key]: e.target.value as SantaVisibilityMode }))
                }
              >
                <option value="full">Видно</option>
                <option value="general">Обобщённо</option>
                <option value="hidden">Скрыто</option>
              </select>
            </div>
          ))}
        </div>
      </div>

      {/* Preview */}
      {preview && (
        <div className="santa-card mt-4">
          <h2 className="font-bold mb-2">Так вас увидит Санта</h2>
          {preview.warnings.length > 0 && (
            <div className="mb-3 p-3 rounded-lg bg-[var(--santa-festive-soft)] text-[#a87400] text-sm">
              {preview.warnings.map((w, i) => (
                <div key={i}>• {w}</div>
              ))}
            </div>
          )}
          <pre className="text-xs bg-[var(--santa-bg)] p-3 rounded-lg overflow-auto max-h-64">
            {JSON.stringify(preview.fields, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}