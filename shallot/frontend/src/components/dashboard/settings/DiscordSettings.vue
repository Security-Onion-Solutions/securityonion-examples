<!--
  Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
  or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
  https://securityonion.net/license; you may not use this file except in compliance with the
  Elastic License 2.0.
-->

<!-- Discord settings component -->
<template>
  <base-settings-form>
    <v-alert
      v-if="modelValue.enabled"
      :type="status?.connected ? 'success' : 'warning'"
      class="mb-4"
      border="start"
      colored-border
      elevation="2"
    >
      {{ connectionStatus }}
    </v-alert>
    <v-switch
      v-model="modelValue.enabled"
      label="Enable Discord Integration"
      hint="Enable or disable Discord bot functionality"
      persistent-hint
      @update:model-value="handleEnabledChange"
    />
    <v-text-field
      v-model="modelValue.botToken"
      label="Bot Token"
      hint="Discord bot token"
      persistent-hint
      type="password"
      :disabled="!modelValue.enabled"
      @update:model-value="$emit('update:modelValue', modelValue)"
    />
    <v-text-field
      v-model="modelValue.commandPrefix"
      label="Command Prefix"
      hint="Prefix for bot commands (e.g., !)"
      persistent-hint
      :disabled="!modelValue.enabled"
      @update:model-value="$emit('update:modelValue', modelValue)"
    />
    <v-switch
      v-model="modelValue.requireApproval"
      label="Require User Approval"
      hint="Require admin approval for new users"
      persistent-hint
      :disabled="!modelValue.enabled"
      @update:model-value="$emit('update:modelValue', modelValue)"
    />
    <v-switch
      v-model="modelValue.alertNotifications"
      label="Alert Notifications"
      hint="Enable alert notifications"
      persistent-hint
      :disabled="!modelValue.enabled"
      @update:model-value="$emit('update:modelValue', modelValue)"
    />
    <v-text-field
      v-model="modelValue.alertChannel"
      label="Alert Channel"
      hint="Channel for alert notifications"
      persistent-hint
      :disabled="!modelValue.enabled || !modelValue.alertNotifications"
      @update:model-value="$emit('update:modelValue', modelValue)"
    />
  </base-settings-form>
</template>

<script setup lang="ts">
import { computed } from "vue"
import BaseSettingsForm from "./BaseSettingsForm.vue"
import type { DiscordSettings } from "../../../types/settings"

const props = defineProps<{
  modelValue: DiscordSettings
  status?: {
    connected: boolean
    error: string | null
  }
}>()

const emit = defineEmits<{
  (e: "update:modelValue", value: DiscordSettings): void
  (e: "platformToggle", platform: "DISCORD", enabled: boolean): void
}>()

const connectionStatus = computed(() => {
  if (!props.modelValue.enabled) return "Disabled"
  if (props.status?.error) return `Error: ${props.status.error}`
  return props.status?.connected ? "Connected" : "Disconnected"
})

const handleEnabledChange = (value: boolean | null) => {
  const enabled = value ?? false
  emit("platformToggle", "DISCORD", enabled)
  emit("update:modelValue", props.modelValue)
}
</script>
