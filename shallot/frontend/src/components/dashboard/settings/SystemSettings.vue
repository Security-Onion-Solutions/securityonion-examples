<!--
  Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
  or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
  https://securityonion.net/license; you may not use this file except in compliance with the
  Elastic License 2.0.
-->

<!-- System settings component -->
<template>
  <base-settings-form>
    <v-switch
      v-model="modelValue.debugLogging"
      label="Debug Logging"
      hint="Enable detailed debug logging"
      persistent-hint
      @update:model-value="$emit('update:modelValue', modelValue)"
    />
  </base-settings-form>
</template>

<script setup lang="ts">
import { computed } from "vue"
import BaseSettingsForm from "./BaseSettingsForm.vue"
import type { SystemSettings } from "../../../types/settings"

const props = defineProps<{
  modelValue: SystemSettings
}>()

const emit = defineEmits<{
  (e: "update:modelValue", value: SystemSettings): void
}>()
</script>
