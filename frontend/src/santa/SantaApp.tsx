import { useEffect, useState } from 'react'
import SantaLanding from './SantaLanding'
import SantaCreateRoom from './SantaCreateRoom'
import SantaRoom from './SantaRoom'
import SantaParticipantRoom from './SantaParticipantRoom'
import SantaJoin from './SantaJoin'

type Screen = 'landing' | 'create' | 'room'

type CreatedRoom = {
  roomId: string
  inviteToken?: string
  deepLink?: string
  isOwner?: boolean
}

export default function SantaApp() {
  const [joinToken, setJoinToken] = useState<string | null>(() => {
    const params = new URLSearchParams(window.location.search)
    return params.get('join')
  })
  const [screen, setScreen] = useState<Screen>('landing')
  const [createdRoom, setCreatedRoom] = useState<CreatedRoom | null>(null)

  return (
    <div className="santa-scope min-h-screen">
      {joinToken && (
        <SantaJoin
          token={joinToken}
          onJoined={(roomId) => {
            setJoinToken(null)
            setCreatedRoom({ roomId })
            setScreen('room')
            // чистим ?join из URL
            window.history.replaceState({}, '', window.location.pathname)
          }}
          onCancel={() => {
            setJoinToken(null)
            window.history.replaceState({}, '', window.location.pathname)
          }}
        />
      )}

      {!joinToken && screen === 'landing' && (
        <SantaLanding
          onCreate={() => setScreen('create')}
          onJoin={(code) => {
            // TODO: join by token — следующий экран
            console.log('join by code:', code)
          }}
          onOpenRoom={async (roomId) => {
            // Пытаемся как организатор, если 403 — как участник
            try {
              await api.santa.getRoom(roomId)
              setCreatedRoom({ roomId, isOwner: true })
            } catch {
              setCreatedRoom({ roomId, isOwner: false })
            }
            setScreen('room')
          }}
        />
      )}

      {!joinToken && screen === 'create' && (
        <SantaCreateRoom
          onBack={() => setScreen('landing')}
          onCreated={(room) => {
            setCreatedRoom({ ...room, isOwner: true })
            setScreen('room')
          }}
        />
      )}

      {!joinToken && screen === 'room' && createdRoom && (
        createdRoom.isOwner === false ? (
          <SantaParticipantRoom
            roomId={createdRoom.roomId}
            onBack={() => setScreen('landing')}
          />
        ) : (
          <SantaRoom
            roomId={createdRoom.roomId}
            onBack={() => setScreen('landing')}
          />
        )
      )}
    </div>
  )
}