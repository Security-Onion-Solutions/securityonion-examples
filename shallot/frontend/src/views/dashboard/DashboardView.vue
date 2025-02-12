<template>
  <v-container>
    <v-row>
      <v-col>
        <h1 class="text-h4 mb-4">Dashboard</h1>
        <v-card class="mb-4">
          <v-card-text>
            <div class="text-h6">Welcome, {{ user?.username }}</div>
            <div class="text-subtitle-1 mt-2">
              {{ user?.is_superuser ? 'Administrator' : 'User' }}
            </div>
          </v-card-text>
        </v-card>
        <p class="mb-4">Welcome to the Security Onion Chat Bot administration dashboard.</p>
        
        <!-- Connection Status -->
        <ConnectionStatus class="mb-4" />

        <!-- Settings Management -->
        <v-card v-if="user?.is_superuser" class="mb-4">
          <SettingsManager />
        </v-card>

        <!-- Users Management -->
        <v-card v-if="user?.is_superuser" class="mb-4">
          <v-card-title>User Management</v-card-title>
          <v-card-subtitle>Manage web administrators and chat users</v-card-subtitle>
          <v-card-text>
            <v-tabs v-model="activeTab">
              <v-tab value="web">Web Administrators</v-tab>
              <v-tab value="chat">Chat Users</v-tab>
            </v-tabs>
            <v-window v-model="activeTab">
              <v-window-item value="web">
                <UsersTable class="mt-4" :user-type="'web'" />
              </v-window-item>
              <v-window-item value="chat">
                <UsersTable class="mt-4" :user-type="'chat'" />
              </v-window-item>
            </v-window>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useStore } from 'vuex'
import UsersTable from '../../components/dashboard/UsersTable.vue'
import SettingsManager from '../../components/dashboard/SettingsManager.vue'
import ConnectionStatus from '../../components/dashboard/ConnectionStatus.vue'

const store = useStore()
const user = computed(() => store.getters['auth/currentUser'])
const activeTab = ref('web')

// Fetch settings on mount if we have a valid token
onMounted(async () => {
  const token = store.getters['auth/token']
  if (!token) {
    console.error('No auth token available')
    return
  }

  // Small delay to ensure navigation is complete
  await new Promise(resolve => setTimeout(resolve, 100))

  try {
    await store.dispatch('settings/fetchSettings')
  } catch (error) {
    console.error('Failed to fetch settings:', error)
    // Only logout if it's a real auth error, not just missing settings
    if (error instanceof Error && !error.message.includes('Failed to load settings')) {
      await store.dispatch('auth/logout')
    }
  }
})
</script>
