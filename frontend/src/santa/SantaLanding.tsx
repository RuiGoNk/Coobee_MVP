import { useEffect, useState } from 'react'
import { api } from '../api'
import type { SantaRoom } from '../types'

type Props = {
  onCreate: () => void
  onJoin: (code: string) => void
  onOpenRoom: (roomId: string) => void
}

export default function SantaLanding({ onCreate, onJoin, onOpenRoom }: Props) {
  const [code, setCode] = useState('')
  const [showJoin, setShowJoin] = useState(false)
  const [rooms, setRooms] = useState<SantaRoom[]>([])
  const [roomsLoading, setRoomsLoading] = useState(true)

  useEffect(() => {
    let alive = true
    api.santa
      .listMyRooms()
      .then((rs) => {
        if (alive) setRooms(rs)
      })
      .catch(() => {})
      .finally(() => {
        if (alive) setRoomsLoading(false)
      })
    return () => {
      alive = false
    }
  }, [])

  return (
    <div className="max-w-2xl mx-auto p-4">
      {/* Hero */}
      <div className="santa-hero p-8 md:p-12 text-center mt-6">
        <h1 className="text-4xl md:text-5xl font-bold mb-3">
          Тайный Санта
        </h1>
        <p className="text-lg md:text-xl opacity-90 mb-8">
          Обменяйтесь подарками с друзьями, семьёй или коллегами.
          <br />
          Анкеты, жеребьёвка и идеи подарков — автоматически.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            className="santa-btn santa-btn-primary text-lg px-8 py-4"
            onClick={onCreate}
          >
            Создать комнату
          </button>
          <button
            className="santa-btn text-lg px-8 py-4 bg-white/15 text-white hover:bg-white/25"
            onClick={() => setShowJoin((v) => !v)}
          >
            Войти по коду
          </button>
        </div>

        {showJoin && (
          <div className="mt-6 flex flex-col sm:flex-row gap-2 max-w-md mx-auto">
            <input
              className="santa-input flex-1"
              placeholder="Код или ссылка-приглашение"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && code.trim()) onJoin(code.trim())
              }}
            />
            <button
              className="santa-btn santa-btn-primary"
              disabled={!code.trim()}
              onClick={() => code.trim() && onJoin(code.trim())}
            >
              Войти
            </button>
          </div>
        )}
      </div>
      {/* Мои комнаты */}
      {!roomsLoading && rooms.length > 0 && (
        <div className="mt-8">
          <h2 className="text-lg font-bold mb-3">Мои комнаты</h2>
          <div className="grid gap-3">
            {rooms.map((r) => (
              <button
                key={r.id}
                onClick={() => onOpenRoom(r.id, r.owner_id === (r as unknown as { owner_me?: boolean }).owner_me)}
                className="santa-card santa-card-hover text-left active:scale-[0.99] transition"
              >
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <div className="font-semibold">{r.title}</div>
                    <div className="santa-muted text-xs mt-1">
                      {r.budget_min}–{r.budget_max} {r.currency}
                      {r.event_date && ` · ${r.event_date}`}
                    </div>
                  </div>
                  <span className="santa-badge santa-badge-primary">
                    {r.status === 'collecting' && 'Сбор'}
                    {r.status === 'drawn' && 'Жеребьёвка'}
                    {r.status === 'in_progress' && 'Идёт'}
                    {r.status === 'completed' && 'Завершено'}
                    {r.status === 'archived' && 'Архив'}
                    {r.status === 'draft' && 'Черновик'}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Преимущества */}
      <div className="grid gap-4 sm:grid-cols-3 mt-8">

        <div className="santa-card">
          <div className="text-2xl mb-2">🎁</div>
          <h3 className="font-semibold mb-1">Автоматическая жеребьёвка</h3>
          <p className="santa-muted text-sm">
            Учитываем исключения — супруги не дарят друг другу.
          </p>
        </div>
        <div className="santa-card">
          <div className="text-2xl mb-2">💡</div>
          <h3 className="font-semibold mb-1">Идеи подарков</h3>
          <p className="santa-muted text-sm">
            Подборка на основе интересов и бюджета. Видна только Санте.
          </p>
        </div>
        <div className="santa-card">
          <div className="text-2xl mb-2">🔒</div>
          <h3 className="font-semibold mb-1">Приватность</h3>
          <p className="santa-muted text-sm">
            Вы решаете, какие поля анкеты увидит ваш Санта.
          </p>
        </div>
      </div>
    </div>
  )
}
