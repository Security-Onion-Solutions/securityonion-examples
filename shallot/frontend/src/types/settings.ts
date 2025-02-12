// Platform Settings Interfaces
export interface SystemSettings {
  debugLogging: boolean
}

export interface SecurityOnionSettings {
  apiUrl: string
  clientId: string
  clientSecret: string
  pollInterval: number
  verifySSL: boolean
}

export interface SlackSettings {
  enabled: boolean
  botToken: string
  appToken: string
  signingSecret: string
  commandPrefix: string
  requireApproval: boolean
  alertNotifications: boolean
  alertChannel: string
}

export interface MatrixSettings {
  enabled: boolean
  homeserverUrl: string
  userId: string
  accessToken: string
  deviceId: string
  commandPrefix: string
  requireApproval: boolean
  alertNotifications: boolean
  alertRoom: string
}

export interface DiscordSettings {
  enabled: boolean
  botToken: string
  commandPrefix: string
  requireApproval: boolean
  alertNotifications: boolean
  alertChannel: string
}

// Platform Status Interfaces
export interface SlackStatus {
  webClientConnected: boolean
  socketModeConnected: boolean
  error: string | null
}

export interface MatrixStatus {
  connected: boolean
  error: string | null
}

export interface Settings {
  system: SystemSettings
  SECURITY_ONION: SecurityOnionSettings
  SLACK: SlackSettings
  MATRIX: MatrixSettings
  DISCORD: DiscordSettings
}

export type SettingCategory = 'system' | 'SECURITY_ONION' | 'SLACK' | 'MATRIX' | 'DISCORD'
