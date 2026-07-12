export type Direction = 'LONG' | 'SHORT' | 'NEUTRAL'

export interface Analysis {
  id: number
  chart_name: string
  timestamp: string
  score: number
  direction: Direction
  reason: string
  entry: string | null
  stop_loss: string | null
  take_profit: string | null
  sent: boolean
  screenshot_url?: string
  notification_id?: number | null
}

export interface Chart {
  id: number
  name: string
  url: string
  enabled: boolean
  last_score: number | null
  last_scanned: string | null
  status: string
}

export interface Notification {
  id: number
  analysis_id: number
  chart_name: string
  timestamp: string
  score: number
  direction: Direction
  status: string
  caption: string | null
}

export interface DashboardStatus {
  running: boolean
  next_scan_seconds: number
  charts_count: number
  analyses_today: number
  signals_sent: number
  avg_score: number
  recent_analyses: Analysis[]
  signals: Analysis[]
}

export interface CppEngineStatus {
  running: boolean
  pid: number | null
  uptime_seconds: number | null
  last_signal: {
    chart_name: string
    timestamp: string
    score: number
    direction: string
    entry: string | null
  } | null
}

export interface Settings {
  [key: string]: any
  CHECK_INTERVAL_SECONDS?: number
  NOTIFICATION_THRESHOLD?: number
  PLAYWRIGHT_WAIT_TIME?: number
  HEADLESS?: boolean
  BROWSER_VIEWPORT_WIDTH?: number
  BROWSER_VIEWPORT_HEIGHT?: number
  NVIDIA_API_KEY?: string
  NVIDIA_MODEL?: string
  AI_CALL_DELAY?: number
  BROWSER_USER_DATA_DIR?: string
  BROWSER_RETRY_COUNT?: number
  BROWSER_RETRY_DELAY?: number
  TELEGRAM_TOKEN?: string
  TELEGRAM_CHAT_ID?: string | number
  TELEGRAM_SEND_SCREENSHOT?: boolean
  TELEGRAM_QUIET_START?: string
  TELEGRAM_QUIET_END?: string
  NOTIFY_LONG?: boolean
  NOTIFY_SHORT?: boolean
  NOTIFY_NEUTRAL?: boolean
  URLS_FILE?: string
}
