import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import type {
  SantaDashboard,
  SantaDraw,
  SantaExclusion,
  SantaParticipantPublic,
  SantaRoom as SantaRoomType,
} from '../types'
import SantaRoomParticipants from './SantaRoomParticipants'
import SantaRoomSettings from './SantaRoomSettings'
import SantaRoomDashboard from './SantaRoomDashboard'
import SantaMyProfile from './SantaMyProfile'

type Props = {
  roomId: string
  onBack: () => void
}

type Tab = 'participants' | 'settings' | 'dashboard'

export default function SantaRoom({ roomId, onBack }: Props) {
  const [room, setRoom] = useState<SantaRoomType | null>(null)
  const [participants, setParticipants] = useState<SantaParticipantPublic[]>([])
  const [exclusions, setExclusions] = useState<SantaExclusion[]>([])
  const [dashboard, setDashboard] = useState<SantaDashboard | null>(null)
  const [draw, setDraw] = useState<SantaDraw | null>(null)
  const [tab, setTab] = useState<Tab>('participants')
  const [showMyProfile, setShowMyProfile] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const reload = useCallback(async () => {
    setError('')
    try {
      const [r, ps, ex, d] = await Promise.all([
        api.santa.getRoom(roomId),
        api.santa.listParticipants(roomId),
        api.santa.listExclusions(roomId).catch(() => []),
        api.santa.getDraw(roomId).catch(() => null),
      ])
      setRoom(r)
      setParticipants(ps)
      setExclusions(ex)
      setDraw(d)
      if (d) {
        const dash = await api.santa.getDashboard(roomId).catch(() => null)
        setDashboard(dash)
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }, [roomId])

  useEffect(() => {
    reload()
  }, [reload])

  if (loading) {
    return <div className="max-w-3xl mx-auto p-8 text-center santa-muted">Загрузка…</div>
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto p-4">
        <button onClick={onBack} className="santa-btn santa-btn-ghost mb-4">← Назад</button>
        <div className="santa-card text-[var(--santa-danger)]">{error}</div>
      </div>
    )
  }

  if (!room) return null

  if (showMyProfile) {
    return (
      <SantaMyProfile
        roomId={roomId}
        room={room}
        onBack={() => setShowMyProfile(false)}
        onSaved={reload}
      />
    )
  }

  const canEdit = room.status === 'draft' || room.status === 'collecting'

  return (
    <div className="max-w-3xl mx-auto p-4">
      <button onClick={onBack} className="santa-btn santa-btn-ghost mb-3">← Назад</button>

      {/* Заголовок комнаты */}
      <div className="santa-card mb-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h1 className="text-2xl font-bold">{room.title}</h1>
              <div className="santa-muted text-sm mt-1">
                Бюджет: {room.budget_min}–{room.budget_max} {room.currency}
                {room.event_date && ` · Обмен: ${room.event_date}`}
              </div>
            </div>
            <StatusBadge status={room.status} />
          </div>
          <button
            className="santa-btn santa-btn-secondary mt-3"
            onClick={() => setShowMyProfile(true)}
          >
            ✏️ Мой профиль в комнате
          </button>
      </div>

      {/* Вкладки */}
      <div className="flex flex-wrap gap-2 mb-4">
        <TabButton active={tab === 'participants'} onClick={() => setTab('participants')}>
          Участники ({participants.length})
        </TabButton>
        <TabButton active={tab === 'settings'} onClick={() => setTab('settings')}>
          Настройки
        </TabButton>
        {draw && (
          <TabButton active={tab === 'dashboard'} onClick={() => setTab('dashboard')}>
            Дашборд
          </TabButton>
        )}
      </div>

      {tab === 'participants' && (
        <SantaRoomParticipants
          roomId={roomId}
          room={room}
          participants={participants}
          draw={draw}
          canEdit={canEdit}
          onChanged={reload}
        />
      )}

      {tab === 'settings' && (
        <SantaRoomSettings
          room={room}
          participants={participants}
          exclusions={exclusions}
          canEdit={canEdit}
          onChanged={reload}
        />
      )}

      {tab === 'dashboard' && dashboard && (
        <SantaRoomDashboard dashboard={dashboard} />
      )}
    </div>
  )
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
        active
          ? 'bg-[var(--santa-primary)] text-white'
          : 'bg-[var(--santa-primary-soft)] text-[var(--santa-primary)] hover:bg-[var(--santa-border)]'
      }`}
    >
      {children}
    </button>
  )
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    draft: { label: 'Черновик', cls: 'santa-badge-primary' },
    collecting: { label: 'Сбор участников', cls: 'santa-badge-primary' },
    drawn: { label: 'Жеребьёвка', cls: 'santa-badge-festive' },
    in_progress: { label: 'Идёт обмен', cls: 'santa-badge-festive' },
    completed: { label: 'Завершено', cls: 'santa-badge-success' },
    archived: { label: 'Архив', cls: 'santa-badge-primary' },
  }
  const cfg = map[status] ?? { label: status, cls: 'santa-badge-primary' }
  return <span className={`santa-badge ${cfg.cls}`}>{cfg.label}</span>
}