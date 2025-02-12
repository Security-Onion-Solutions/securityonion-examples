<!--
  Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
  or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
  https://securityonion.net/license; you may not use this file except in compliance with the
  Elastic License 2.0.
-->

<template>
  <v-card-title>Settings</v-card-title>
  <v-card-subtitle>Configure system and platform settings</v-card-subtitle>
  <v-card-text>
    <v-form ref="form">
      <v-tabs v-model="activeTab">
        <v-tab value="system">System</v-tab>
        <v-tab value="SECURITY_ONION">Security Onion</v-tab>
        <v-tab value="SLACK">Slack</v-tab>
        <v-tab value="MATRIX">Matrix</v-tab>
        <v-tab value="DISCORD">Discord</v-tab>
      </v-tabs>

      <v-window v-model="activeTab">
        <!-- System Settings -->
        <v-window-item value="system">
          <system-settings
            v-model="settings.system"
          />
        </v-window-item>

        <!-- Security Onion Settings -->
        <v-window-item value="SECURITY_ONION">
          <security-onion-settings
            v-model="settings.SECURITY_ONION"
          />
        </v-window-item>

        <!-- Slack Settings -->
        <v-window-item value="SLACK">
          <slack-settings
            v-model="settings.SLACK"
            :status="slackStatus"
            @platform-toggle="handlePlatformToggle"
          />
        </v-window-item>

        <!-- Matrix Settings -->
        <v-window-item value="MATRIX">
          <matrix-settings
            v-model="settings.MATRIX"
            :status="matrixStatus"
            @platform-toggle="handlePlatformToggle"
          />
        </v-window-item>

        <!-- Discord Settings -->
        <v-window-item value="DISCORD">
          <discord-settings
            v-model="settings.DISCORD"
            :status="discordStatus"
            @platform-toggle="handlePlatformToggle"
          />
        </v-window-item>
      </v-window>

      <v-divider class="my-4" />

      <v-row justify="end">
        <v-col cols="auto">
          <v-btn
            color="primary"
            :loading="loading"
            :disabled="loading"
            @click="saveSettings"
          >
            Save Settings
          </v-btn>
        </v-col>
      </v-row>

      <v-alert
        v-if="error"
        type="error"
        class="mt-4"
      >
        {{ error }}
      </v-alert>
    </v-form>
  </v-card-text>
</template>

<script lang="ts">
import { defineComponent } from "vue"

export default defineComponent({
  name: 'SettingsManager'
})
</script>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue"
import { useStore } from "../../store"
import type { Setting } from "../../store/modules/settings"
import type { Settings, SettingCategory } from "../../types/settings"
import type { VForm } from 'vuetify/components'

// Import components
import SystemSettings from "./settings/SystemSettings.vue"
import SecurityOnionSettings from "./settings/SecurityOnionSettings.vue"
import SlackSettings from "./settings/SlackSettings.vue"
import MatrixSettings from "./settings/MatrixSettings.vue"
import DiscordSettings from "./settings/DiscordSettings.vue"

const store = useStore()
const form = ref<VForm | null>(null)
const activeTab = ref<string>("system")

// Settings state with default values
const settings = ref<Settings>({
  system: {
    debugLogging: false
  },
  SECURITY_ONION: {
    apiUrl: "",
    clientId: "",
    clientSecret: "",
    pollInterval: 60,
    verifySSL: true
  },
  SLACK: {
    enabled: false,
    botToken: "",
    appToken: "",
    signingSecret: "",
    commandPrefix: "!",
    requireApproval: true,
    alertNotifications: false,
    alertChannel: ""
  },
  MATRIX: {
    enabled: false,
    homeserverUrl: "",
    userId: "",
    accessToken: "",
    deviceId: "",
    commandPrefix: "!",
    requireApproval: true,
    alertNotifications: false,
    alertRoom: ""
  },
  DISCORD: {
    enabled: false,
    botToken: "",
    commandPrefix: "!",
    requireApproval: true,
    alertNotifications: false,
    alertChannel: ""
  }
})

// Store state
const loading = computed(() => store.getters["settings/isLoading"])
const error = computed(() => store.getters["settings/error"])

// Track if settings have been saved
const settingsSaved = ref(false)
let statusInterval: ReturnType<typeof setInterval> | null = null

// Status states
const discordStatus = ref<{
  connected: boolean
  error: string | null
}>({
  connected: false,
  error: null
})

const slackStatus = ref<{
  webClientConnected: boolean
  socketModeConnected: boolean
  error: string | null
}>({
  webClientConnected: false,
  socketModeConnected: false,
  error: null
})

const matrixStatus = ref<{
  connected: boolean
  error: string | null
}>({
  connected: false,
  error: null
})

// Methods
const loadSettings = async () => {
  try {
    const allSettings = await store.dispatch("settings/fetchSettings")
    console.log("Fetched all settings:", allSettings)
    
    if (!Array.isArray(allSettings)) {
      console.log("No settings returned, using defaults")
      return
    }
    
    const categories: SettingCategory[] = ["system", "SECURITY_ONION", "SLACK", "MATRIX", "DISCORD"]
    for (const category of categories) {
      const setting = allSettings.find((s: Setting) => s.key === category)
      if (setting && setting.value) {
        console.log(`Loading ${category} settings`)
        try {
          settings.value[category] = JSON.parse(setting.value)
          console.log(`Loaded ${category} settings successfully`)
        } catch (parseError) {
          console.error(`Failed to parse ${category} settings:`, parseError)
        }
      } else {
        console.log(`Using default values for ${category}`)
      }
    }
  } catch (error) {
    console.error("Failed to load settings:", error)
  }
}

const updateSlackStatus = async () => {
  if (settings.value.SLACK.enabled) {
    try {
      const status = await store.dispatch("settings/getSlackStatus")
      slackStatus.value = status
    } catch (error) {
      console.error("Failed to get Slack status:", error)
      slackStatus.value.error = error instanceof Error ? error.message : "Failed to get Slack status"
    }
  } else {
    slackStatus.value = {
      webClientConnected: false,
      socketModeConnected: false,
      error: null
    }
  }
}

const updateMatrixStatus = async () => {
  if (settings.value.MATRIX.enabled) {
    try {
      const status = await store.dispatch("settings/getMatrixStatus")
      matrixStatus.value = status
    } catch (error) {
      console.error("Failed to get Matrix status:", error)
      matrixStatus.value.error = error instanceof Error ? error.message : "Failed to get Matrix status"
    }
  } else {
    matrixStatus.value = {
      connected: false,
      error: null
    }
  }
}

const handlePlatformToggle = (platform: "SLACK" | "MATRIX" | "DISCORD", enabled: boolean) => {
  if (enabled) {
    // Disable other platforms
    const platforms = ["SLACK", "MATRIX", "DISCORD"] as const
    platforms.forEach(p => {
      if (p !== platform && p in settings.value) {
        const settingValue = settings.value[p]
        if ("enabled" in settingValue) {
          settingValue.enabled = false
        }
      }
    })
  } else {
    // When disabling a platform, immediately stop status checks
    if (statusInterval) {
      clearInterval(statusInterval)
      statusInterval = null
    }
    settingsSaved.value = false

    // Clear status for the disabled platform
    if (platform === "SLACK") {
      slackStatus.value = {
        webClientConnected: false,
        socketModeConnected: false,
        error: null
      }
    } else if (platform === "MATRIX") {
      matrixStatus.value = {
        connected: false,
        error: null
      }
    }
  }
}

const updateDiscordStatus = async () => {
  if (settings.value.DISCORD.enabled) {
    try {
      const status = await store.dispatch("settings/getDiscordStatus")
      discordStatus.value = status
    } catch (error) {
      console.error("Failed to get Discord status:", error)
      discordStatus.value.error = error instanceof Error ? error.message : "Failed to get Discord status"
    }
  } else {
    discordStatus.value = {
      connected: false,
      error: null
    }
  }
}

const startStatusInterval = () => {
  // Clear any existing interval
  if (statusInterval) {
    clearInterval(statusInterval)
  }
  
  // Only start interval if settings have been saved and at least one platform is enabled
  if (settingsSaved.value && (settings.value.SLACK.enabled || settings.value.MATRIX.enabled || settings.value.DISCORD.enabled)) {
    statusInterval = setInterval(() => {
      Promise.all([
        updateSlackStatus(),
        updateMatrixStatus(),
        updateDiscordStatus()
      ])
    }, 30000)
  }
}

const saveSettings = async () => {
  if (!form.value?.validate()) return

  try {
    const categories: SettingCategory[] = ["system", "SECURITY_ONION", "SLACK", "MATRIX", "DISCORD"]
    for (const category of categories) {
      await store.dispatch("settings/updateSetting", {
        key: category,
        value: JSON.stringify(settings.value[category]),
        description: `${category} configuration`
      })
    }

    if (categories.includes("SECURITY_ONION")) {
      console.log("Testing Security Onion connection...")
      await store.dispatch("settings/testSecurityOnionConnection")
    }

    // Update status after saving
    await Promise.all([
      updateSlackStatus(),
      updateMatrixStatus(),
      updateDiscordStatus()
    ])

    // Mark settings as saved and start interval
    settingsSaved.value = true
    startStatusInterval()
  } catch (error) {
    console.error("Failed to save settings:", error)
  }
}

// Watch for settings changes to reset saved state
watch(settings, () => {
  settingsSaved.value = false
  if (statusInterval) {
    clearInterval(statusInterval)
    statusInterval = null
  }
}, { deep: true })

// Lifecycle
onMounted(async () => {
  await loadSettings()
  
  // Initial status update only if settings were loaded
  if (settings.value.SLACK.enabled || settings.value.MATRIX.enabled || settings.value.DISCORD.enabled) {
    settingsSaved.value = true
    await Promise.all([
      updateSlackStatus(),
      updateMatrixStatus(),
      updateDiscordStatus()
    ])
    startStatusInterval()
  }
})

onUnmounted(() => {
  if (statusInterval) {
    clearInterval(statusInterval)
  }
})
</script>
