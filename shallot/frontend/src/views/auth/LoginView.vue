<!--
  Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
  or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
  https://securityonion.net/license; you may not use this file except in compliance with the
  Elastic License 2.0.
-->

<template>
  <v-container class="fill-height">
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card>
          <v-img
            src="/shallot.png"
            class="mx-auto mt-4"
            max-width="200"
            alt="Shallot Logo"
          />
          <v-card-title class="text-center">
            Login to Shallot
          </v-card-title>
          <v-card-text>
            <v-form @submit.prevent="handleLogin">
              <v-text-field
                v-model="username"
                label="Username"
                required
                :error-messages="errors.username"
              />
              <v-text-field
                v-model="password"
                label="Password"
                type="password"
                required
                :error-messages="errors.password"
              />
              <v-alert
                v-if="error"
                type="error"
                class="mt-3"
              >
                {{ error }}
              </v-alert>
              <v-card-actions>
                <v-spacer />
                <v-btn
                  color="primary"
                  type="submit"
                  :loading="loading"
                >
                  Login
                </v-btn>
              </v-card-actions>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useStore } from 'vuex'
import { useRouter, useRoute } from 'vue-router'

const store = useStore()
const router = useRouter()
const route = useRoute()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const errors = ref({
  username: '',
  password: ''
})

// Get redirect path from query parameter
const redirectPath = ref('')
onMounted(() => {
  const redirect = route.query.redirect as string
  if (redirect) {
    redirectPath.value = decodeURIComponent(redirect)
  }
})

const handleLogin = async () => {
  // Reset errors
  error.value = ''
  errors.value = {
    username: '',
    password: ''
  }

  // Validate
  if (!username.value) {
    errors.value.username = 'Username is required'
    return
  }
  if (!password.value) {
    errors.value.password = 'Password is required'
    return
  }

  loading.value = true

  try {
    await store.dispatch('auth/login', {
      username: username.value,
      password: password.value
    })
    
    // Wait for token to be properly set in store and localStorage
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // Redirect to saved path or dashboard
    // Let the dashboard handle fetching settings
    if (redirectPath.value) {
      router.push(redirectPath.value)
    } else {
      router.push({ name: 'dashboard' })
    }
  } catch (err) {
    if (err instanceof Error) {
      error.value = err.message
    } else {
      error.value = 'Login failed. Please check your credentials.'
    }
  } finally {
    loading.value = false
  }
}
</script>
