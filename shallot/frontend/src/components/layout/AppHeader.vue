<!--
  Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
  or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
  https://securityonion.net/license; you may not use this file except in compliance with the
  Elastic License 2.0.
-->

<template>
  <v-app-bar color="primary">
    <v-app-bar-title>Security Onion Chat Bot</v-app-bar-title>
    <v-spacer />
    <template v-if="isAuthenticated">
      <v-btn variant="text" to="/dashboard">
        Dashboard
      </v-btn>
      <v-btn variant="text" to="/dashboard/api-test">
        Commands
      </v-btn>
      <v-btn variant="text" to="/docs/setup">
        Documentation
      </v-btn>
      <v-btn variant="text" icon @click="toggleTheme">
        <v-icon>{{ isDark ? 'mdi-weather-sunny' : 'mdi-weather-night' }}</v-icon>
      </v-btn>
      <v-btn variant="text" @click="handleLogout">
        Logout
      </v-btn>
    </template>
  </v-app-bar>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useStore } from 'vuex'
import { computed } from 'vue'

const router = useRouter()
const store = useStore()

const isAuthenticated = computed(() => store.getters['auth/isAuthenticated'])
const isDark = computed(() => store.getters['theme/isDark'])

const toggleTheme = () => {
  store.dispatch('theme/toggleTheme')
}

const handleLogout = () => {
  store.dispatch('auth/logout')
  router.push({ name: 'login' })
}
</script>
