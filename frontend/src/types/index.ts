export type Direction = 'LONG' | 'SHORT' | 'NEUTRAL'

export type ChartType = 'crypto' | 'forex' | 'stocks' | 'indices' | 'commodities' | 'other'

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
  signal_json?: string | null
}

export interface Chart {
  id: number
  name: string
  url: string
  symbol: string
  type: ChartType
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
  threshold: number
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
  DISPLAY_TIMEZONE?: string
}

export type StrategyType = 'prompt' | 'cpp'

export interface StrategyParamSchema {
  type: 'int' | 'float' | 'bool' | 'str'
  default: number | boolean | string
  min?: number
  max?: number
  step?: number
  options?: string[]
  hint?: string
}

export interface CppStrategyDefinition {
  key: string
  label: string
  description: string
  params: Record<string, StrategyParamSchema>
}

export interface AiStrategy {
  id: number
  name: string
  content: string
  created_at: string
  updated_at: string
}

export interface CppStrategy {
  id: number
  name: string
  engine_type: string
  params: Record<string, any>
  created_at: string
  updated_at: string
}

export interface ActiveStrategy {
  id: number
  name: string
  mode: 'hybrid' | 'ai_only' | 'cpp_only'
  enabled: boolean
  chart_id: number
  cpp_strategy_id: number | null
  ai_strategy_id: number | null
  min_score: number
  cooldown_minutes: number
  created_at: string
  updated_at: string
  
  // joined fields (optional depending on API output)
  chart_name?: string
  ai_strategy_name?: string
  cpp_strategy_name?: string
}

