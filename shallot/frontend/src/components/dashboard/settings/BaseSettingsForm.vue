<!--
  Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
  or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
  https://securityonion.net/license; you may not use this file except in compliance with the
  Elastic License 2.0.
-->

<!-- Base component for settings forms -->
<template>
  <v-container>
    <slot></slot>
    <v-alert
      v-if="error"
      type="error"
      class="mt-4"
    >
      {{ error }}
    </v-alert>
  </v-container>
</template>

<script setup lang="ts">
import { computed } from "vue"
import { useStore } from "../../../store"

const store = useStore()
const error = computed(() => store.getters["settings/error"])

defineExpose({
  error
})
</script>
