import { useEffect, useState } from 'react'
import { api } from '../api'
import type { SantaPrefill, SantaPreview, SantaVisibilityMode } from '../types'

type Props = {
  token: string
  onJoined: (roomId: string) => void
  onCancel: () => void
}

const GENDER_OPTIONS = [
  { value: 'male', label: 'Мужской' },
  { value: 'female', label: 'Женский' },
  { value: 'other', label: 'Другой' },
  { value: 'prefer_not_to_say', label: 'Не указывать' },
]

const INTERESTS_OPTIONS = [
  'tech', 'gaming', 'books_fiction', 'books_nonfiction', 'coffee', 'cooking',
  'travel', 'sport', 'art', 'music', 'cinema', 'fashion', 'beauty', 'home',
  'gardening', 'pets', 'photography', 'science',
]

const VISIBILITY_FIELDS: Array<{ key: string; label: string }> = [
  { key: 'gender', label: 'Пол' },
  { key: 'age', label: 'Возраст' },
  { key: 'interests', label: 'Интересы' },
  { key: 'antipathies', label: 'Антипатии' },
  { key: 'allergies', label: 'Аллергии' },
  { key: 'hobbies', label: 'Хобби' },
]

export default function SantaJoin({ token, onJoined, onCancel }: Props) {
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [prefill, setPrefill] = useState<SantaPrefill | null>(null)
  const [preview, setPreview] = useState<SantaPreview | null>(null)

  // Анкета
  const [displayName, setDisplayName] = useState('')
  const [gender, setGender] = useState('prefer_not_to_say')
  const [ageMode, setAgeMode] = useState<'date' | 'age'>('age')
  const [birthDate, setBirthDate] = useState('')
  const [age, setAge] = useState('')
  const [interests, setInterests] = useState<string[]>([])
  const [visibility, setVisibility] = useState<Record<string, SantaVisibilityMode>>({})

  useEffect(() => {
    let alive = true
    async function load() {
      setLoading(true)
      try {
        // Пытаемся получить prefill: room_id неизвестен из токена,
        // поэтому идём «наугад» — сначала get room by token нет,
        // но join вернёт room. Значит, prefill только после join.
        // Для MVP: prefill не делаем на этом шаге, показываем форму.
        // (Позже можно добавить GET /join/{token}/prefill.)
        setPrefill(null)
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
  }, [token])

  function toggleInterest(i: string) {
    setInterests((prev) => (prev.includes(i) ? prev.filter((x) => x !== i) : [...prev, i]))
  }

  async function submit() {
    setError('')
    setSaving(true)
    try {
      const payload: Record<string, unknown> = {
        display_name: displayName.trim() || undefined,
        gender,
        interests,
        visibility,
      }
      if (ageMode === 'date' && birthDate) {
        payload.birth_date = birthDate
      } else if (ageMode === 'age' && age) {
        payload.age = Number(age)
      } else {
        throw new Error('Укажите дату рождения или возраст')
      }
      if (interests.length === 0) {
        throw new Error('Выберите хотя бы один интерес')
      }

      const participant = await api.santa.join(token, payload)
      onJoined(participant.room_id)
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
      <button onClick={onCancel} className="santa-btn santa-btn-ghost mb-3">
        ← Отмена
      </button>

      <div className="santa-card">
        <h1 className="text-2xl font-bold mb-1">Вступление в Тайного Санту</h1>
        <p className="santa-muted text-sm mb-4">
          Заполните мини-анкету. Ваш Санта увидит только то, что вы разрешите.
        </p>

        {/* Прогресс */}
        <div className="flex items-center gap-2 mb-6">
          {[1, 2, 3].map((n) => (
            <div key={n} className="flex-1 flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                  step >= n
                    ? 'bg-[var(--santa-primary)] text-white'
                    : 'bg-[var(--santa-primary-soft)] text-[var(--santa-primary)]'
                }`}
              >
                {n}
              </div>
              {n < 3 && (
                <div
                  className={`flex-1 h-1 rounded ${
                    step > n ? 'bg-[var(--santa-primary)]' : 'bg-[var(--santa-border)]'
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Step 1 — мини-анкета */}
        {step === 1 && (
          <div>
            <h2 className="font-bold mb-3">Мини-анкета</h2>
            <label className="block mb-3">
              <span className="block text-sm font-medium mb-1">Как к вам обращаться</span>
              <input
                className="santa-input"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Имя"
              />
            </label>
            <div className="mb-3">
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
            <div className="mb-3">
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
            <div>
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
          </div>
        )}

        {/* Step 2 — privacy */}
        {step === 2 && (
          <div>
            <h2 className="font-bold mb-3">Приватность</h2>
            <p className="santa-muted text-sm mb-3">
              Настройте, какие поля увидит ваш Санта.
            </p>
            <div className="space-y-2">
              {VISIBILITY_FIELDS.map((f) => (
                <div
                  key={f.key}
                  className="flex items-center justify-between gap-3 py-2 border-b border-[var(--santa-border)] last:border-0"
                >
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
        )}

        {/* Step 3 — подтверждение */}
        {step === 3 && (
          <div>
            <h2 className="font-bold mb-3">Проверьте и вступите</h2>
            <div className="space-y-2 text-sm">
              <Row label="Имя" value={displayName || '—'} />
              <Row label="Пол" value={GENDER_OPTIONS.find((o) => o.value === gender)?.label ?? gender} />
              <Row label="Возраст" value={ageMode === 'date' ? birthDate : age} />
              <Row label="Интересы" value={interests.join(', ') || '—'} />
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-[var(--santa-accent-soft)] text-[var(--santa-accent)] text-sm">
            {error}
          </div>
        )}

        <div className="flex justify-between gap-2 mt-6">
          <button
            className="santa-btn santa-btn-ghost"
            onClick={() => (step === 1 ? onCancel() : setStep((s) => (s - 1) as 1 | 2 | 3))}
            disabled={saving}
          >
            ← Назад
          </button>
          {step < 3 ? (
            <button
              className="santa-btn santa-btn-primary"
              onClick={() => {
                setError('')
                if (step === 1) {
                  if (!interests.length) {
                    setError('Выберите хотя бы один интерес')
                    return
                  }
                  if (!age && !birthDate) {
                    setError('Укажите возраст или дату рождения')
                    return
                  }
                }
                setStep((s) => (s + 1) as 1 | 2 | 3)
              }}
              disabled={saving}
            >
              Далее →
            </button>
          ) : (
            <button className="santa-btn santa-btn-primary" onClick={submit} disabled={saving}>
              {saving ? 'Вступаем…' : 'Вступить'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-[var(--santa-border)] pb-2">
      <span className="santa-muted">{label}</span>
      <span className="font-medium text-right break-words">{value}</span>
    </div>
  )
}