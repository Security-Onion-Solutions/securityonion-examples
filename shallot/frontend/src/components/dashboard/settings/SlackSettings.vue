<!--
  Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
  or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
  https://securityonion.net/license; you may not use this file except in compliance with the
  Elastic License 2.0.
-->

<!-- Slack settings component -->
<template>
  <base-settings-form>
    <v-switch
      v-model="modelValue.enabled"
      label="Enable Slack Integration"
      hint="Enable or disable Slack bot functionality"
      persistent-hint
      @update:model-value="handleEnabledChange"
    />
    <v-text-field
      v-model="modelValue.botToken"
      label="Bot Token"
      hint="Bot User OAuth Token - Used for sending messages and interacting with Slack APIs"
      persistent-hint
      :disabled="!modelValue.enabled"
      @update:model-value="$emit('update:modelValue', modelValue)"
    />
    <v-text-field
      v-model="modelValue.appToken"
      label="App Token"
      hint="App-Level Token - Required for Socket Mode connections"
      persistent-hint
      :disabled="!modelValue.enabled"
      @update:model-value="$emit('update:modelValue', modelValue)"
    />
    <v-text-field
      v-model="modelValue.signingSecret"
      label="Signing Secret"
      hint="Signing Secret from App Credentials - Used to verify requests from Slack"
      persistent-hint
      :disabled="!modelValue.enabled"
      @update:model-value="$emit('update:modelValue', modelValue)"
    />
    <v-text-field
      v-model="modelValue.commandPrefix"
      label="Command Prefix"
      hint="Character prefix for bot commands (e.g., ! or /) - Users will type this before commands"
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
      hint="Slack channel ID or name (e.g., #alerts or C0123ABC) for sending notifications"
      persistent-hint
      :disabled="!modelValue.enabled || !modelValue.alertNotifications"
      @update:model-value="$emit('update:modelValue', modelValue)"
    />
    <v-alert
      v-if="status.error"
      type="error"
      class="mt-4"
    >
      {{ status.error }}
    </v-alert>
    <v-alert
      v-else-if="modelValue.enabled"
      :type="status.webClientConnected && status.socketModeConnected ? 'success' : 'warning'"
      class="mt-4"
    >
      Web Client: {{ status.webClientConnected ? "Connected" : "Disconnected" }}<br>
      Socket Mode: {{ status.socketModeConnected ? "Connected" : "Disconnected" }}
    </v-alert>
  </base-settings-form>
</template>

<script setup lang="ts">
import { computed } from "vue"
import BaseSettingsForm from "./BaseSettingsForm.vue"
import type { SlackSettings, SlackStatus } from "../../../types/settings"

const props = defineProps<{
  modelValue: SlackSettings
  status: SlackStatus
}>()

const emit = defineEmits<{
  (e: "update:modelValue", value: SlackSettings): void
  (e: "platformToggle", platform: "SLACK", enabled: boolean): void
}>()

const handleEnabledChange = (value: boolean | null) => {
  const enabled = value ?? false
  emit("platformToggle", "SLACK", enabled)
  emit("update:modelValue", props.modelValue)
}
</script>
