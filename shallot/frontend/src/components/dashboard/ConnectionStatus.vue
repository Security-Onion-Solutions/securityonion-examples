<template>
  <v-card class="mb-4">
    <v-card-title>Connection Status</v-card-title>
    <v-card-text>
      <div class="d-flex align-center mb-2">
        <div class="me-2">Security Onion API:</div>
        <v-icon
          :color="soStatus.connected ? 'success' : 'error'"
          :title="soStatus.error || 'Connected'"
        >
          {{ soStatus.connected ? 'mdi-check-circle' : 'mdi-alert-circle' }}
        </v-icon>
        <v-tooltip v-if="soStatus.error" activator="parent">
          {{ soStatus.error }}
        </v-tooltip>
      </div>
      <div class="d-flex align-center">
        <div class="me-2">{{ activeService }}:</div>
        <v-icon
          :color="anyServiceConnected ? 'success' : 'error'"
          :title="activeServiceError || (anyServiceConnected ? 'Connected' : 'Disconnected')"
        >
          {{ anyServiceConnected ? 'mdi-check-circle' : 'mdi-alert-circle' }}
        </v-icon>
        <v-tooltip v-if="activeServiceError" activator="parent">
          {{ activeServiceError }}
        </v-tooltip>
      </div>
    </v-card-text>
    <v-card-actions>
      <v-btn
        color="primary"
        @click="testConnection"
        :loading="testing"
      >
        Test Connection
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script lang="ts">
import { defineComponent, ref, onUnmounted, computed, watch } from 'vue'
import { useStore } from '@/store'
import type { Ref } from 'vue'

export default defineComponent({
  name: 'ConnectionStatus',
  setup() {

interface ConnectionStatus {
  connected: boolean
  error: string | null
}

interface SlackStatus {
  webClientConnected: boolean
  socketModeConnected: boolean
  error: string | null
}

interface MatrixStatus {
  connected: boolean
  e2eEnabled: boolean
  error: string | null
}

interface Setting {
  key: string
  value: string
  description?: string
}

const store = useStore()
const soStatus = ref<ConnectionStatus>({ connected: false, error: null })
const discordStatus = ref<ConnectionStatus>({ connected: false, error: null })
const slackStatus = ref<SlackStatus>({ 
  webClientConnected: false, 
  socketModeConnected: false, 
  error: null 
})
const teamsStatus = ref<ConnectionStatus>({ connected: false, error: null })
const matrixStatus = ref<MatrixStatus>({
  connected: false,
  e2eEnabled: false,
  error: null
})

// Map store state
const testing = computed(() => store.getters['settings/isLoading'])
const storeError = computed(() => store.getters['settings/error'])

// Get settings from store
const getSettings = computed(() => {
  const allSettings = store.getters['settings/allSettings']
  const settings = allSettings.reduce((acc: any, setting: any) => {
    try {
      if (setting.key === 'DISCORD' || setting.key === 'SLACK' || 
          setting.key === 'TEAMS' || setting.key === 'MATRIX') {
        acc[setting.key] = JSON.parse(setting.value)
      }
    } catch (e) {
      console.error(`Failed to parse ${setting.key} settings:`, e)
    }
    return acc
  }, {})
  return settings
})

// Computed property to determine which service is active
const activeService = computed(() => {
  const settings = getSettings.value
  
  // First check which service is enabled in settings
  if (settings.MATRIX?.enabled) return 'Matrix'
  if (settings.SLACK?.enabled) return 'Slack'
  if (settings.TEAMS?.enabled) return 'Teams'
  if (settings.DISCORD?.enabled) return 'Discord'
  
  return 'No Service Connected'
})

// Computed property to check if any service is connected
const anyServiceConnected = computed(() => {
  const settings = getSettings.value
  const activeServiceName = activeService.value
  
  switch (activeServiceName) {
    case 'Discord':
      return discordStatus.value.connected
    case 'Slack':
      return slackStatus.value.webClientConnected && slackStatus.value.socketModeConnected
    case 'Teams':
      return teamsStatus.value.connected
    case 'Matrix':
      return matrixStatus.value.connected
    default:
      return false
  }
})

// Computed property to get the active service's error message
const activeServiceError = computed(() => {
  const activeServiceName = activeService.value
  
  switch (activeServiceName) {
    case 'Discord':
      return discordStatus.value.error
    case 'Slack':
      return slackStatus.value.error
    case 'Teams':
      return teamsStatus.value.error
    case 'Matrix':
      return matrixStatus.value.error
    default:
      return null
  }
})

const getSoStatus = async () => {
  try {
    const response = await store.dispatch('settings/getSecurityOnionStatus')
    soStatus.value = response
  } catch (error) {
    console.error('Failed to get SO status:', error)
    soStatus.value = { connected: false, error: storeError.value || 'Failed to get status' }
  }
}

const testConnection = async () => {
  try {
    const response = await store.dispatch('settings/testSecurityOnionConnection')
    if (response?.status?.connected !== undefined) {
      soStatus.value = response.status
    } else {
      soStatus.value = { 
        connected: false, 
        error: response?.status?.error || storeError.value || 'Invalid response format' 
      }
    }
  } catch (error) {
    console.error('Failed to test SO connection:', error)
    soStatus.value = { connected: false, error: storeError.value || 'Connection test failed' }
  }
}

const getDiscordStatus = async () => {
  try {
    const response = await store.dispatch('settings/getDiscordStatus')
    discordStatus.value = response
  } catch (error) {
    console.error('Failed to get Discord status:', error)
    discordStatus.value = { connected: false, error: storeError.value || 'Failed to get status' }
  }
}

const getSlackStatus = async () => {
  try {
    const response = await store.dispatch('settings/getSlackStatus')
    slackStatus.value = response
  } catch (error) {
    console.error('Failed to get Slack status:', error)
    slackStatus.value = { webClientConnected: false, socketModeConnected: false, error: storeError.value || 'Failed to get status' }
  }
}

const getTeamsStatus = async () => {
  try {
    const response = await store.dispatch('settings/getTeamsStatus')
    teamsStatus.value = response
  } catch (error) {
    console.error('Failed to get Teams status:', error)
    teamsStatus.value = { connected: false, error: storeError.value || 'Failed to get status' }
  }
}

const getMatrixStatus = async () => {
  try {
    const response = await store.dispatch('settings/getMatrixStatus')
    matrixStatus.value = response
  } catch (error) {
    console.error('Failed to get Matrix status:', error)
    matrixStatus.value = { connected: false, e2eEnabled: false, error: storeError.value || 'Failed to get status' }
  }
}

// Helper to check if a service is configured
const isServiceConfigured = (serviceName: string) => {
  const settings = getSettings.value
  return settings[serviceName]?.enabled === true
}

// Set up polling for status updates
const pollStatus = async () => {
  const settings = store.getters['settings/allSettings']
  if (!settings || settings.length === 0) {
    // Don't poll if no settings exist yet
    return
  }

  const statusChecks = []

  // Only check services that are configured
  statusChecks.push(getSoStatus()) // Always check SO status as it's core functionality

  if (isServiceConfigured('DISCORD')) {
    statusChecks.push(getDiscordStatus())
  }
  if (isServiceConfigured('SLACK')) {
    statusChecks.push(getSlackStatus())
  }
  if (isServiceConfigured('TEAMS')) {
    statusChecks.push(getTeamsStatus())
  }
  if (isServiceConfigured('MATRIX')) {
    statusChecks.push(getMatrixStatus())
  }

  try {
    await Promise.all(statusChecks)
  } catch (error) {
    // Silently handle failed fetches to prevent error messages
    console.debug('Status check failed:', error)
  }
}

let pollingInterval: ReturnType<typeof setInterval> | null = null

// Watch for settings changes
watch(
  () => store.getters['settings/allSettings'],
  (newSettings: Setting[]) => {
    if (newSettings && newSettings.length > 0) {
      // Start polling only when settings exist
      if (!pollingInterval) {
        pollingInterval = setInterval(pollStatus, 5000)
      }
      pollStatus()
    } else if (pollingInterval) {
      // Stop polling if settings are cleared
      clearInterval(pollingInterval)
      pollingInterval = null
    }
  },
  { immediate: true }
)

    // Clean up on unmount
    onUnmounted(() => {
      if (pollingInterval) {
        clearInterval(pollingInterval)
        pollingInterval = null
      }
    })

    return {
      soStatus,
      activeService,
      anyServiceConnected,
      activeServiceError,
      testing,
      testConnection
    }
  }
})
</script>
