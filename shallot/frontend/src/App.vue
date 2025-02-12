<!--
  Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
  or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
  https://securityonion.net/license; you may not use this file except in compliance with the
  Elastic License 2.0.
-->

<template>
  <v-app>
    <app-header />

    <v-main :class="{ 'bg-grey-lighten-3': !isDark, 'bg-grey-darken-4': isDark }">
      <router-view />
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useStore } from 'vuex'
import AppHeader from './components/layout/AppHeader.vue'

const store = useStore()
const isDark = computed(() => store.getters['theme/isDark'])
</script>

<style>
/* Global styles will go here */
</style>
