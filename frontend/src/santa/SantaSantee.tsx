import { useEffect, useState } from 'react'
import { api } from '../api'
import type {
  SantaGiftStatus,
  SantaMessage,
  SantaSanteeCard,
  SantaSuggestions,
} from '../types'

type Props = {
  card: SantaSanteeCard
  currency: string
  onChanged: () => void
  onOpenProfile: () => void
}

const GIFT_OPTIONS: Array<{ value: SantaGiftStatus; label: string }> = [
  { value: 'pending', label: 'Не отправлен' },
  { value: 'chosen', label: 'Выбран' },
  { value: 'shipped', label: 'Отправлен' },
  { value: 'delivered', label: 'Доставлен' },
]

export default function SantaSantee({ card, currency, onChanged, onOpenProfile }: Props) {
  const [sug, setSug] = useState<SantaSuggestions | null>(null)
  const [messages, setMessages] = useState<SantaMessage[]>([])
  const [newMessage, setNewMessage] = useState('')
  const [giftStatus, setGiftStatus] = useState<SantaGiftStatus>(card.gift_status)
  const [loadingSug, setLoadingSug] = useState(true)
  const [regenBusy, setRegenBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    async function load() {
      setLoadingSug(true)
      try {
        const [s, m] = await Promise.all([
          api.santa.getSuggestions(card.assignment_id).catch(() => null),
          api.santa.listMessages(card.assignment_id).catch(() => []),
        ])
        if (!alive) return
        setSug(s)
        setMessages(m)
      } catch (e) {
        if (alive) setError(String(e))
      } finally {
        if (alive) setLoadingSug(false)
      }
    }
    load()
    return () => {
      alive = false
    }
  }, [card.assignment_id])

  async function regenerate() {
    setRegenBusy(true)
    setError('')
    try {
      const r = await api.santa.regenerate(card.assignment_id)
      setSug(r)
    } catch (e) {
      setError(String(e))
    } finally {
      setRegenBusy(false)
    }
  }

  async function updateGiftStatus(status: SantaGiftStatus) {
    setError('')
    try {
      await api.santa.updateGiftStatus(card.assignment_id, status)
      setGiftStatus(status)
      onChanged()
    } catch (e) {
      setError(String(e))
    }
  }

  async function sendMessage() {
    if (!newMessage.trim()) return
    setError('')
    try {
      const m = await api.santa.sendMessage(card.assignment_id, newMessage.trim())
      setMessages((prev) => [...prev, m])
      setNewMessage('')
    } catch (e) {
      setError(String(e))
    }
  }

  const p = card.participant as Record<string, unknown>

  return (
    <div className="space-y-4">
      {error && (
        <div className="p-3 rounded-lg bg-[var(--santa-accent-soft)] text-[var(--santa-accent)] text-sm">
          {error}
        </div>
      )}

      {/* Карточка подопечного */}
      <div className="santa-card">
        <h2 className="text-xl font-bold mb-3">
          Ваш подопечный: {String(p.display_name ?? '—')}
        </h2>
        <div className="space-y-1 text-sm">
          <Field label="Пол" value={String(p.gender ?? '—')} />
          <Field label="Возраст" value={String(p.age ?? '—')} />
          <Field
            label="Интересы"
            value={Array.isArray(p.interests) ? (p.interests as string[]).join(', ') : '—'}
          />
          {p.antipathies && <Field label="Антипатии" value={String(p.antipathies)} />}
          {p.allergies && <Field label="Аллергии" value={String(p.allergies)} />}
          {p.hobbies && <Field label="Хобби" value={String(p.hobbies)} />}
          {p.brands && <Field label="Бренды" value={String(p.brands)} />}
        </div>
        <div className="mt-3 text-sm">
          <span className="santa-muted">Бюджет: </span>
          <span className="font-medium">
            {card.budget_min}–{card.budget_max} {currency}
          </span>
        </div>
        {card.pickup_point && (
          <div className="mt-3 p-3 rounded-lg bg-[var(--santa-festive-soft)] text-sm">
            <div className="font-medium mb-1">📦 Пункт выдачи</div>
            <div>
              {String((card.pickup_point as Record<string, unknown>).market ?? '')}
              {card.pickup_point.city ? `, ${String(card.pickup_point.city)}` : ''}
            </div>
          </div>
        )}
        {card.hints.length > 0 && (
          <div className="mt-3 text-xs santa-muted">
            {card.hints.map((h, i) => (
              <div key={i}>• {h}</div>
            ))}
          </div>
        )}
      </div>

      {/* Подборка */}
      <div className="santa-card">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-bold">💡 Идеи подарков</h2>
          {sug && (
            <span className="santa-muted text-xs">
              {sug.can_regenerate ? `Перегенераций: ${sug.regenerations_left}` : 'Лимит исчерпан'}
            </span>
          )}
        </div>

        {loadingSug ? (
          <p className="santa-muted text-sm">Загрузка…</p>
        ) : !sug || sug.items.length === 0 ? (
          <p className="santa-muted text-sm">
            Подборка не сгенерирована (каталог маленький). Попробуйте позже.
          </p>
        ) : (
          <>
            <div className="space-y-3">
              {sug.items.map((it) => (
                <div
                  key={it.id}
                  className="p-3 rounded-lg border border-[var(--santa-border)]"
                >
                  <div className="font-medium">{it.idea_title}</div>
                  <div className="santa-muted text-xs mt-1">
                    {it.price_min != null && it.price_max != null
                      ? `${it.price_min}–${it.price_max} ${currency}`
                      : 'цена не указана'}
                    {it.category && ` · ${it.category}`}
                  </div>
                  {it.reason && (
                    <div className="text-xs mt-1 text-[var(--santa-primary)]">
                      {it.reason}
                    </div>
                  )}
                </div>
              ))}
            </div>

            <button
              className="santa-btn santa-btn-secondary mt-3"
              onClick={regenerate}
              disabled={!sug.can_regenerate || regenBusy}
            >
              {regenBusy ? 'Генерируем…' : '🔄 Показать другие идеи'}
            </button>
          </>
        )}
      </div>

      {/* Gift status */}
      <div className="santa-card">
        <h2 className="font-bold mb-2">Статус подарка</h2>
        <div className="flex flex-wrap gap-2">
          {GIFT_OPTIONS.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => updateGiftStatus(o.value)}
              className={`px-3 py-1.5 rounded-lg text-sm border ${
                giftStatus === o.value
                  ? 'border-[var(--santa-primary)] bg-[var(--santa-primary-soft)]'
                  : 'border-[var(--santa-border)]'
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {/* Чат */}
      <div className="santa-card">
        <h2 className="font-bold mb-2">Анонимные сообщения</h2>
        <p className="santa-muted text-xs mb-3">
          Подопечный видит «Сообщение от вашего Санты». Вы не раскрываете себя.
        </p>

        {messages.length === 0 ? (
          <p className="santa-muted text-sm mb-3">Пока нет сообщений.</p>
        ) : (
          <div className="space-y-2 mb-3 max-h-64 overflow-auto">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`p-2 rounded-lg text-sm max-w-[80%] ${
                  m.from_role === 'santa'
                    ? 'bg-[var(--santa-primary-soft)] ml-auto'
                    : 'bg-[var(--santa-bg)]'
                }`}
              >
                {m.body}
              </div>
            ))}
          </div>
        )}

        <div className="flex gap-2">
          <input
            className="santa-input flex-1"
            placeholder="Написать подопечному…"
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') sendMessage()
            }}
          />
          <button className="santa-btn santa-btn-primary" onClick={sendMessage}>
            Отправить
          </button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <span className="santa-muted min-w-[100px]">{label}:</span>
      <span>{value}</span>
    </div>
  )
}