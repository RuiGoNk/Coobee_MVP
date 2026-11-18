import { useState } from 'react'
import { api } from '../api'
import type { SantaRoom } from '../types'

type Props = {
  onBack: () => void
  onCreated: (room: { roomId: string; deepLink?: string }) => void
}

type Step = 1 | 2 | 3

const ANONYMITY_OPTIONS = [
  { value: 'full', label: 'Полностью анонимно', hint: 'Санта не раскрывает себя' },
  { value: 'reveal_after', label: 'Раскрытие после обмена', hint: 'Санта может открыться в конце' },
  { value: 'signed', label: 'С подписью', hint: 'Санта известен получателю' },
] as const

const VISIBILITY_OPTIONS = [
  { value: 'open', label: 'Открыто', hint: 'Все поля видны Санте по умолчанию' },
  { value: 'balanced', label: 'Сбалансированно', hint: 'Пол/возраст видны, остальное — по выбору' },
  { value: 'minimal', label: 'Минимум', hint: 'Только обобщённая информация' },
] as const

export default function SantaCreateRoom({ onBack, onCreated }: Props) {
  const [step, setStep] = useState<Step>(1)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  // Step 1: параметры
  const [title, setTitle] = useState('')
  const [eventDate, setEventDate] = useState('')
  const [budgetMin, setBudgetMin] = useState('1000')
  const [budgetMax, setBudgetMax] = useState('2000')

  // Step 2: правила
  const [anonymityMode, setAnonymityMode] = useState<string>('full')
  const [visibilityPolicy, setVisibilityPolicy] = useState<string>('balanced')
  const [maxParticipants, setMaxParticipants] = useState('30')

  function validateStep1(): string | null {
    if (!title.trim()) return 'Укажите название комнаты'
    const min = Number(budgetMin)
    const max = Number(budgetMax)
    if (!Number.isFinite(min) || min < 0) return 'Минимальный бюджет — число ≥ 0'
    if (!Number.isFinite(max) || max < min) return 'Максимальный бюджет должен быть ≥ минимального'
    return null
  }

  function next() {
    setError('')
    if (step === 1) {
      const err = validateStep1()
      if (err) {
        setError(err)
        return
      }
    }
    setStep((s) => (s < 3 ? ((s + 1) as Step) : s))
  }

  function back() {
    setError('')
    if (step === 1) {
      onBack()
    } else {
      setStep((s) => (s > 1 ? ((s - 1) as Step) : s))
    }
  }

  async function submit() {
    setError('')
    setSaving(true)
    try {
      const room: SantaRoom = await api.santa.createRoom({
        title: title.trim(),
        event_date: eventDate || null,
        budget_min: Number(budgetMin),
        budget_max: Number(budgetMax),
        currency: 'RUB',
        anonymity_mode: anonymityMode,
        visibility_policy: visibilityPolicy,
        max_participants: Number(maxParticipants),
      })

      let deepLink: string | undefined
      try {
        const invite = await api.santa.createInvite(room.id)
        deepLink = invite.deep_link ?? undefined
      } catch {
        // не критично: комнату создали, ссылку можно получить позже
      }

      onCreated({ roomId: room.id, deepLink })
    } catch (e) {
      setError(String(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto p-4">
      <button
        onClick={back}
        className="santa-btn santa-btn-ghost mb-4"
        disabled={saving}
      >
        ← Назад
      </button>

      <div className="santa-card">
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

        {/* Step 1 */}
        {step === 1 && (
          <div>
            <h2 className="text-xl font-bold mb-4">Параметры обмена</h2>
            <label className="block mb-4">
              <span className="block text-sm font-medium mb-1">Название комнаты</span>
              <input
                className="santa-input"
                placeholder="Например: Новый год в офисе"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                autoFocus
              />
            </label>
            <label className="block mb-4">
              <span className="block text-sm font-medium mb-1">Дата обмена (опционально)</span>
              <input
                type="date"
                className="santa-input"
                value={eventDate}
                onChange={(e) => setEventDate(e.target.value)}
              />
            </label>
            <div className="grid grid-cols-2 gap-3 mb-2">
              <label className="block">
                <span className="block text-sm font-medium mb-1">Бюджет от, ₽</span>
                <input
                  type="number"
                  className="santa-input"
                  value={budgetMin}
                  onChange={(e) => setBudgetMin(e.target.value)}
                />
              </label>
              <label className="block">
                <span className="block text-sm font-medium mb-1">Бюджет до, ₽</span>
                <input
                  type="number"
                  className="santa-input"
                  value={budgetMax}
                  onChange={(e) => setBudgetMax(e.target.value)}
                />
              </label>
            </div>
          </div>
        )}

        {/* Step 2 */}
        {step === 2 && (
          <div>
            <h2 className="text-xl font-bold mb-4">Правила и приватность</h2>

            <div className="mb-5">
              <div className="text-sm font-medium mb-2">Анонимность</div>
              <div className="grid gap-2">
                {ANONYMITY_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setAnonymityMode(opt.value)}
                    className={`text-left p-3 rounded-lg border transition ${
                      anonymityMode === opt.value
                        ? 'border-[var(--santa-primary)] bg-[var(--santa-primary-soft)]'
                        : 'border-[var(--santa-border)] hover:border-[var(--santa-primary)]'
                    }`}
                  >
                    <div className="font-medium">{opt.label}</div>
                    <div className="santa-muted text-xs">{opt.hint}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-5">
              <div className="text-sm font-medium mb-2">Видимость анкет по умолчанию</div>
              <div className="grid gap-2">
                {VISIBILITY_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setVisibilityPolicy(opt.value)}
                    className={`text-left p-3 rounded-lg border transition ${
                      visibilityPolicy === opt.value
                        ? 'border-[var(--santa-primary)] bg-[var(--santa-primary-soft)]'
                        : 'border-[var(--santa-border)] hover:border-[var(--santa-primary)]'
                    }`}
                  >
                    <div className="font-medium">{opt.label}</div>
                    <div className="santa-muted text-xs">{opt.hint}</div>
                  </button>
                ))}
              </div>
            </div>

            <label className="block">
              <span className="block text-sm font-medium mb-1">
                Максимум участников (3–30)
              </span>
              <input
                type="number"
                min={3}
                max={30}
                className="santa-input"
                value={maxParticipants}
                onChange={(e) => setMaxParticipants(e.target.value)}
              />
            </label>
          </div>
        )}

        {/* Step 3 */}
        {step === 3 && (
          <div>
            <h2 className="text-xl font-bold mb-4">Проверьте и создайте</h2>
            <div className="space-y-2 text-sm">
              <Row label="Название" value={title} />
              <Row label="Дата обмена" value={eventDate || '—'} />
              <Row label="Бюджет" value={`${budgetMin}–${budgetMax} ₽`} />
              <Row
                label="Анонимность"
                value={ANONYMITY_OPTIONS.find((o) => o.value === anonymityMode)?.label ?? anonymityMode}
              />
              <Row
                label="Видимость"
                value={VISIBILITY_OPTIONS.find((o) => o.value === visibilityPolicy)?.label ?? visibilityPolicy}
              />
              <Row label="Макс. участников" value={maxParticipants} />
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-[var(--santa-accent-soft)] text-[var(--santa-accent)] text-sm">
            {error}
          </div>
        )}

        {/* Кнопки */}
        <div className="flex justify-end gap-2 mt-6">
          {step < 3 ? (
            <button className="santa-btn santa-btn-primary" onClick={next} disabled={saving}>
              Далее →
            </button>
          ) : (
            <button className="santa-btn santa-btn-primary" onClick={submit} disabled={saving}>
              {saving ? 'Создаём…' : 'Создать комнату'}
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