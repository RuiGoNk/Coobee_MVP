import { useEffect, useState } from 'react'
import { api } from '../api'
import type { SantaRoom as SantaRoomType, SantaSanteeCard } from '../types'
import SantaMyProfile from './SantaMyProfile'
import SantaSantee from './SantaSantee'

type Props = {
  roomId: string
  onBack: () => void
}

type Tab = 'santee' | 'profile'

export default function SantaParticipantRoom({ roomId, onBack }: Props) {
  const [room, setRoom] = useState<SantaRoomType | null>(null)
  const [santee, setSantee] = useState<SantaSanteeCard | null>(null)
  const [tab, setTab] = useState<Tab>('profile')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function reload() {
    setError('')
    try {
      const r = await api.santa.getRoomForParticipant(roomId)
      setRoom(r)
      // Пытаемся получить подопечного — может быть 409 (draw не прошёл)
      try {
        const s = await api.santa.getMyAssignment(roomId)
        setSantee(s)
        setTab((cur) => (cur === 'profile' ? 'santee' : cur))
      } catch {
        setSantee(null)
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    reload()
  }, [roomId])

  if (loading) {
    return <div className="max-w-2xl mx-auto p-8 text-center santa-muted">Загрузка…</div>
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto p-4">
        <button onClick={onBack} className="santa-btn santa-btn-ghost mb-3">← Назад</button>
        <div className="santa-card text-[var(--santa-danger)]">{error}</div>
      </div>
    )
  }

  if (!room) return null

  return (
    <div className="max-w-2xl mx-auto p-4">
      <button onClick={onBack} className="santa-btn santa-btn-ghost mb-3">← Назад</button>

      <div className="santa-card mb-4">
        <h1 className="text-2xl font-bold">{room.title}</h1>
        <div className="santa-muted text-sm mt-1">
          Бюджет: {room.budget_min}–{room.budget_max} {room.currency}
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {santee && (
          <TabButton active={tab === 'santee'} onClick={() => setTab('santee')}>
            🎁 Мой подопечный
          </TabButton>
        )}
        <TabButton active={tab === 'profile'} onClick={() => setTab('profile')}>
          ✏️ Мой профиль
        </TabButton>
      </div>

      {tab === 'profile' && (
        <SantaMyProfile
          roomId={roomId}
          room={room}
          onSaved={reload}
          onBack={() => setTab(santee ? 'santee' : 'profile')}
        />
      )}

      {tab === 'santee' && santee && (
        <SantaSantee
          card={santee}
          currency={room.currency}
          onChanged={reload}
          onOpenProfile={() => setTab('profile')}
        />
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