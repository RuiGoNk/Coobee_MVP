import { useEffect, useRef } from 'react'

type TelegramUser = {
  id: number
  first_name?: string
  last_name?: string
  username?: string
  photo_url?: string
  auth_date: number
  hash: string
}

type Props = {
  botUsername: string
  onAuth: (user: TelegramUser) => void
}

declare global {
  interface Window {
    onTelegramAuth?: (user: TelegramUser) => void
  }
}

export default function TelegramLogin({ botUsername, onAuth }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    window.onTelegramAuth = (user: TelegramUser) => onAuth(user)
    const script = document.createElement('script')
    script.src = 'https://telegram.org/js/telegram-widget.js?22'
    script.async = true
    script.setAttribute('data-telegram-login', botUsername)
    script.setAttribute('data-size', 'large')
    script.setAttribute('data-onauth', 'onTelegramAuth(user)')
    script.setAttribute('data-request-access', 'write')
    ref.current?.appendChild(script)

    return () => {
      if (ref.current) ref.current.innerHTML = ''
      delete window.onTelegramAuth
    }
  }, [botUsername, onAuth])

  return <div ref={ref} />
}