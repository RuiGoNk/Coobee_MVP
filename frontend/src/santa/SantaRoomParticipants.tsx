import { useState } from 'react'
import { api } from '../api'
import type {
  SantaDraw,
  SantaParticipantPublic,
  SantaParticipantStatus,
  SantaRoom,
} from '../types'

type Props = {
  roomId: string
  room: SantaRoom
  participants: SantaParticipantPublic[]
  draw: SantaDraw | null
  canEdit: boolean
  onChanged: () => void
}

const STATUS_LABEL: Record<SantaParticipantStatus, string> = {
  invited: 'Приглашён',
  joined: 'Не заполнил',
  profile_min: 'Минимум',
  profile_full: 'Полная анкета',
}

const STATUS_CLS: Record<SantaParticipantStatus, string> = {
  invited: 'santa-badge-primary',
  joined: 'santa-badge-accent',
  profile_min: 'santa-badge-festive',
  profile_full: 'santa-badge-success',
}

export default function SantaRoomParticipants({
  roomId,
  room,
  participants,
  draw,
  canEdit,
  onChanged,
}: Props) {
  const [drawing, setDrawing] = useState(false)
  const [error, setError] = useState('')
  const [showConfirm, setShowConfirm] = useState(false)
  const [mode, setMode] = useState<'random' | 'chain'>('random')

  const active = participants.filter((p) => !p.is_deleted)
  const allReady = active.every((p) => p.status === 'profile_min' || p.status === 'profile_full')
  const canDraw = !draw && canEdit && active.length >= 3 && allReady

  async function startDraw() {
    setError('')
    setDrawing(true)
    try {
      await api.santa.startDraw(roomId, mode)
      setShowConfirm(false)
      onChanged()
    } catch (e) {
      setError(String(e))
    } finally {
      setDrawing(false)
    }
  }

  return (
    <div>
      {/* Прогресс */}
      <div className="santa-card mb-4">
        <div className="flex justify-between text-sm mb-2">
          <span className="santa-muted">Заполнили анкету</span>
          <span className="font-medium">
            {active.filter((p) => p.status === 'profile_min' || p.status === 'profile_full').length} / {active.length}
          </span>
        </div>
        <div className="h-2 rounded-full bg-[var(--santa-border)] overflow-hidden">
          <div
            className="h-full bg-[var(--santa-primary)] transition-all"
            style={{
              width: `${
                active.length
                  ? (active.filter((p) => p.status === 'profile_min' || p.status === 'profile_full').length /
                      active.length) *
                    100
                  : 0
              }%`,
            }}
          />
        </div>
      </div>

      {/* Список */}
      <div className="santa-card mb-4">
        <h2 className="font-bold mb-3">Участники</h2>
        {active.length === 0 ? (
          <p className="santa-muted text-sm">Пока никто не вступил. Отправьте ссылку-приглашение.</p>
        ) : (
          <div className="divide-y divide-[var(--santa-border)]">
            {active.map((p) => (
              <div key={p.id} className="flex items-center justify-between py-2.5">
                <div className="font-medium">{p.display_name}</div>
                <span className={`santa-badge ${STATUS_CLS[p.status]}`}>
                  {STATUS_LABEL[p.status]}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Кнопка draw */}
      {canDraw && !showConfirm && (
        <div className="santa-card">
          <p className="text-sm mb-3">
            Все участники заполнили анкеты. Можно проводить жеребьёвку.
          </p>
          <button className="santa-btn santa-btn-primary" onClick={() => setShowConfirm(true)}>
            🎲 Провести жеребьёвку
          </button>
        </div>
      )}

      {showConfirm && (
        <div className="santa-card">
          <h3 className="font-bold mb-3">Провести жеребьёвку?</h3>
          <p className="text-sm santa-muted mb-3">
            После жеребьёвки участники получат своих подопечных. Изменить пары можно
            только до первого просмотра.
          </p>

          <div className="mb-4">
            <div className="text-sm font-medium mb-2">Режим</div>
            <div className="grid gap-2">
              <button
                type="button"
                onClick={() => setMode('random')}
                className={`text-left p-3 rounded-lg border ${
                  mode === 'random'
                    ? 'border-[var(--santa-primary)] bg-[var(--santa-primary-soft)]'
                    : 'border-[var(--santa-border)]'
                }`}
              >
                <div className="font-medium">Случайная</div>
                <div className="santa-muted text-xs">Классический Тайный Санта</div>
              </button>
              <button
                type="button"
                onClick={() => setMode('chain')}
                className={`text-left p-3 rounded-lg border ${
                  mode === 'chain'
                    ? 'border-[var(--santa-primary)] bg-[var(--santa-primary-soft)]'
                    : 'border-[var(--santa-border)]'
                }`}
              >
                <div className="font-medium">Цепочка</div>
                <div className="santa-muted text-xs">A → B → C → A</div>
              </button>
            </div>
          </div>

          {error && (
            <div className="mb-3 p-3 rounded-lg bg-[var(--santa-accent-soft)] text-[var(--santa-accent)] text-sm">
              {error}
            </div>
          )}

          <div className="flex gap-2">
            <button
              className="santa-btn santa-btn-primary"
              onClick={startDraw}
              disabled={drawing}
            >
              {drawing ? 'Проводим…' : 'Провести'}
            </button>
            <button
              className="santa-btn santa-btn-ghost"
              onClick={() => setShowConfirm(false)}
              disabled={drawing}
            >
              Отмена
            </button>
          </div>
        </div>
      )}

      {draw && (
        <div className="santa-card mt-4">
          <p className="text-sm">
            <span className="santa-badge santa-badge-festive">Жеребьёвка проведена</span>
          </p>
          <p className="santa-muted text-xs mt-2">
            Статус: {draw.status === 'ready' ? 'готово' : 'генерация подборок…'}
          </p>
        </div>
      )}
    </div>
  )
}
