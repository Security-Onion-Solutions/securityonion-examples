<!--
  Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
  or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
  https://securityonion.net/license; you may not use this file except in compliance with the
  Elastic License 2.0.
-->

<!-- Matrix settings component -->
<template>
  <base-settings-form>
    <v-switch
      v-model="modelValue.enabled"
      label="Enable Matrix Integration"
      hint="Enable or disable Matrix bot functionality"
      persistent-hint
      @update:model-value="handleEnabledChange"
    />
    <v-text-field
      v-model="modelValue.homeserverUrl"
      label="Homeserver URL"
      hint="Matrix homeserver URL"
      persistent-hint
      :disabled="!modelValue.enabled"
      @update:model-value="$emit('update:modelValue', modelValue)"
    />
    <v-text-field
      v-model="modelValue.userId"
      label="User ID"
      hint="Matrix user ID (@user:domain.tld)"
      persistent-hint
      :disabled="!modelValue.enabled"
      @update:model-value="$emit('update:modelValue', modelValue)"
    />
    <v-text-field
      v-model="modelValue.accessToken"
      label="Access Token"
      hint="Matrix access token"
      persistent-hint
      type="password"
      :disabled="!modelValue.enabled"
      @update:model-value="$emit('update:modelValue', modelValue)"
    />
    <v-text-field
      v-model="modelValue.deviceId"
      label="Device ID"
      hint="Matrix device identifier"
      persistent-hint
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
    <v-alert
      type="info"
      class="mt-4"
      dense
    >
      Note: End-to-end encryption is not supported. Messages will be sent unencrypted.
    </v-alert>
    <v-text-field
      v-model="modelValue.alertRoom"
      label="Alert Room"
      hint="Room ID for alert notifications"
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
      :type="status.connected ? 'success' : 'warning'"
      class="mt-4"
    >
      Status: {{ status.connected ? "Connected" : "Disconnected" }}
    </v-alert>
  </base-settings-form>
</template>

<script setup lang="ts">
import { computed } from "vue"
import BaseSettingsForm from "./BaseSettingsForm.vue"
import type { MatrixSettings, MatrixStatus } from "../../../types/settings"

const props = defineProps<{
  modelValue: MatrixSettings
  status: MatrixStatus
}>()

const emit = defineEmits<{
  (e: "update:modelValue", value: MatrixSettings): void
  (e: "platformToggle", platform: "MATRIX", enabled: boolean): void
}>()

const handleEnabledChange = (value: boolean | null) => {
  const enabled = value ?? false
  emit("platformToggle", "MATRIX", enabled)
  emit("update:modelValue", props.modelValue)
}
</script>
