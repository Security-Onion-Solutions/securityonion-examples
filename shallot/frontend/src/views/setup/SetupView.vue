<template>
  <v-container class="fill-height">
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="6">
        <v-card class="elevation-12">
          <v-card-title class="text-h5 text-center py-4">
            Initial Setup
          </v-card-title>
          <v-card-text>
            <v-form @submit.prevent="handleSubmit" ref="form">
              <v-text-field
                v-model="username"
                label="Admin Username"
                name="username"
                type="text"
                required
                :rules="[rules.required]"
              />
              <v-text-field
                v-model="password"
                label="Password"
                name="password"
                type="password"
                required
                :rules="[rules.required, rules.min]"
              />
              <v-text-field
                v-model="confirmPassword"
                label="Confirm Password"
                name="confirmPassword"
                type="password"
                required
                :rules="[rules.required, rules.passwordMatch]"
              />
            </v-form>
          </v-card-text>
          <v-card-actions class="px-4 pb-4">
            <v-spacer />
            <v-btn
              color="primary"
              block
              :loading="loading"
              :disabled="loading"
              @click="handleSubmit"
            >
              Create Admin Account
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useStore } from 'vuex'

const router = useRouter()
const store = useStore()

const form = ref()
const loading = ref(false)
const username = ref('')
const password = ref('')
const confirmPassword = ref('')

const rules = {
  required: (v: string) => !!v || 'This field is required',
  min: (v: string) => v.length >= 8 || 'Password must be at least 8 characters',
  passwordMatch: (v: string) => v === password.value || 'Passwords must match'
}

const handleSubmit = async () => {
  const { valid } = await form.value.validate()
  
  if (!valid) return
  
  loading.value = true
  
  try {
    await store.dispatch('auth/setup', {
      username: username.value,
      password: password.value
    })
    
    // Redirect to dashboard after successful setup
    router.push({ name: 'dashboard' })
  } catch (error) {
    console.error('Setup failed:', error)
  } finally {
    loading.value = false
  }
}
</script>
