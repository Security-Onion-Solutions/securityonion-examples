<!--
  Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
  or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
  https://securityonion.net/license; you may not use this file except in compliance with the
  Elastic License 2.0.
-->

<!-- Security Onion settings component -->
<template>
  <base-settings-form>
    <v-text-field
      v-model="modelValue.apiUrl"
      label="API URL"
      hint="Security Onion API endpoint URL"
      persistent-hint
      required
      @update:model-value="$emit('update:modelValue', modelValue)"
    />
    <v-text-field
      v-model="modelValue.clientId"
      label="Client ID"
      hint="API client identifier"
      persistent-hint
      required
      @update:model-value="$emit('update:modelValue', modelValue)"
    />
    <v-text-field
      v-model="modelValue.clientSecret"
      label="Client Secret"
      hint="API client secret"
      persistent-hint
      type="password"
      required
      @update:model-value="$emit('update:modelValue', modelValue)"
    />
    <v-text-field
      v-model.number="modelValue.pollInterval"
      label="Poll Interval"
      hint="Alert polling interval in seconds"
      persistent-hint
      type="number"
      required
      @update:model-value="$emit('update:modelValue', modelValue)"
    />
    <v-switch
      v-model="modelValue.verifySSL"
      label="Verify SSL"
      hint="Verify SSL certificates for API requests"
      persistent-hint
      @update:model-value="$emit('update:modelValue', modelValue)"
    />
  </base-settings-form>
</template>

<script setup lang="ts">
import { computed } from "vue"
import BaseSettingsForm from "./BaseSettingsForm.vue"
import type { SecurityOnionSettings } from "../../../types/settings"

const props = defineProps<{
  modelValue: SecurityOnionSettings
}>()

const emit = defineEmits<{
  (e: "update:modelValue", value: SecurityOnionSettings): void
}>()
</script>
