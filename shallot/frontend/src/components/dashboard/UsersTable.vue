<template>
  <div>
    <v-card>
      <v-card-title class="d-flex justify-space-between align-center">
        {{ userType === 'web' ? 'Web Administrators' : 'Chat Users' }}
        <v-btn
          color="primary"
          prepend-icon="mdi-plus"
          @click="showCreateDialog = true"
          v-if="currentUser?.is_superuser"
        >
          Add {{ userType === 'web' ? 'Administrator' : 'Chat User' }}
        </v-btn>
      </v-card-title>

      <v-card-text>
        <v-table>
          <thead>
            <tr>
              <th>Username</th>
              <th v-if="userType === 'chat'">Display Name</th>
              <th v-if="userType === 'chat'">Service</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in filteredUsers" :key="user.id">
              <td>{{ user.username }}</td>
              <td v-if="userType === 'chat'">{{ user.display_name || '-' }}</td>
              <td v-if="userType === 'chat'">
                <v-chip
                  :color="getServiceColor(user.service)"
                  size="small"
                >
                  {{ getServiceDisplay(user.service) }}
                </v-chip>
              </td>
              <td>
                <v-chip
                  :color="getRoleColor(user)"
                  size="small"
                >
                  {{ getRoleText(user) }}
                </v-chip>
              </td>
              <td>
                <v-chip
                  :color="user.is_active ? 'success' : 'warning'"
                  size="small"
                >
                  {{ user.is_active ? 'Active' : 'Inactive' }}
                </v-chip>
              </td>
              <td>
                <div class="d-flex align-center">
                  <v-btn
                    icon="mdi-pencil"
                    variant="text"
                    size="small"
                    @click="editUser(user)"
                    v-if="currentUser?.is_superuser || currentUser?.id === user.id"
                  />
                  <v-btn
                    v-if="userType === 'chat' && currentUser?.is_superuser"
                    icon="mdi-delete"
                    variant="text"
                    size="small"
                    color="error"
                    @click="deleteUser(user)"
                  />
                </div>
              </td>
            </tr>
          </tbody>
        </v-table>
      </v-card-text>
    </v-card>

    <!-- Create User Dialog -->
    <v-dialog v-model="showCreateDialog" max-width="500px">
      <v-card>
        <v-card-title>Create New {{ userType === 'web' ? 'Administrator' : 'Chat User' }}</v-card-title>
        <v-card-text>
          <v-form ref="createForm" @submit.prevent="handleCreate">
            <v-text-field
              v-model="newUser.username"
              label="Username"
              required
              :rules="[(v: string) => !!v || 'Username is required']"
            />
            <v-text-field
              v-model="newUser.password"
              label="Password"
              type="password"
              required
              :rules="[(v: string) => !!v || 'Password is required']"
            />
            <v-switch
              v-if="userType === 'web'"
              v-model="newUser.is_superuser"
              label="Admin Access"
              color="error"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            color="grey-darken-1"
            variant="text"
            @click="showCreateDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            variant="text"
            @click="handleCreate"
            :loading="loading"
          >
            Create
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Edit User Dialog -->
    <v-dialog v-model="showEditDialog" max-width="500px">
      <v-card>
        <v-card-title>Edit {{ userType === 'web' ? 'Administrator' : 'Chat User' }}</v-card-title>
        <v-card-text>
          <v-form ref="editForm" @submit.prevent="handleEdit">
            <v-text-field
              v-model="editedUser.username"
              label="Username"
              required
              :rules="[(v: string) => !!v || 'Username is required']"
            />
            <v-text-field
              v-if="userType === 'chat'"
              v-model="editedUser.display_name"
              label="Display Name"
            />
            <template v-if="userType === 'web'">
              <v-text-field
                v-model="editedUser.password"
                label="New Password (optional)"
                type="password"
              />
              <v-switch
                v-model="editedUser.is_active"
                label="Active"
                color="success"
                v-if="currentUser?.is_superuser"
              />
              <v-switch
                v-if="currentUser?.is_superuser && editedUser.id !== currentUser?.id"
                v-model="editedUser.is_superuser"
                label="Admin Access"
                color="error"
              />
            </template>
            <template v-else>
              <v-select
                v-model="editedUser.role"
                label="Role"
                :items="[
                  { value: 'user', title: 'User' },
                  { value: 'basic', title: 'Basic' },
                  { value: 'admin', title: 'Admin' }
                ]"
                :rules="[(v: string) => !!v || 'Role is required']"
              />
            </template>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            color="grey-darken-1"
            variant="text"
            @click="showEditDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            variant="text"
            @click="handleEdit"
            :loading="loading"
          >
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, defineProps, PropType } from 'vue'
import { useStore } from 'vuex'
import type { User } from '../../store/modules/users'
import { Store } from 'vuex'
import { RootState } from '../../store'

import { ChatService } from '../../types/chat'

// Service display and color mappings
const serviceDisplayMap: Record<ChatService, string> = {
  [ChatService.DISCORD]: 'Discord',
  [ChatService.SLACK]: 'Slack',
  [ChatService.MATRIX]: 'Matrix',
  [ChatService.TEAMS]: 'Teams'
}

const serviceColorMap: Record<ChatService, string> = {
  [ChatService.DISCORD]: 'purple',
  [ChatService.SLACK]: 'blue',
  [ChatService.MATRIX]: 'green',
  [ChatService.TEAMS]: 'orange'
}

function getServiceDisplay(service: string | undefined): string {
  return service ? serviceDisplayMap[service as ChatService] || service : ''
}

function getServiceColor(service: string | undefined): string {
  return service ? serviceColorMap[service as ChatService] || 'primary' : 'primary'
}

interface Props {
  userType: 'web' | 'chat'
}

const props = defineProps<Props>()
const store = useStore<RootState>()
const loading = computed(() => store.getters['users/isLoading'])
const users = computed(() => store.getters['users/getUsers'])
const currentUser = computed(() => store.getters['auth/currentUser'])
const error = computed(() => store.getters['users/getError'])

// Filter users based on type
const filteredUsers = computed(() => {
  return users.value.filter((user: User) => user.user_type === props.userType)
})

const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const createForm = ref()
const editForm = ref()

interface NewUser {
  username: string
  password: string
  is_superuser: boolean
  user_type: 'web' | 'chat'
}

const newUser = ref<NewUser>({
  username: '',
  password: '',
  is_superuser: false,
  user_type: props.userType
})

interface EditedUser {
  id?: number
  username: string
  password: string
  is_active: boolean
  is_superuser: boolean
  user_type: 'web' | 'chat'
  role?: string
  display_name?: string
}

const editedUser = ref<EditedUser>({
  username: '',
  password: '',
  is_active: true,
  is_superuser: false,
  user_type: props.userType
})

onMounted(async () => {
  await store.dispatch('users/fetchUsers', { userType: props.userType })
})

function editUser(user: User) {
  editedUser.value = {
    id: user.id,
    username: user.username,
    password: '',
    is_active: user.is_active,
    is_superuser: user.is_superuser,
    user_type: user.user_type,
    role: user.role || 'user',
    display_name: user.display_name
  }
  showEditDialog.value = true
}

async function handleCreate() {
  const { valid } = await createForm.value.validate()
  if (!valid) return

  try {
    await store.dispatch('users/createUser', {
      ...newUser.value,
      user_type: props.userType
    })
    showCreateDialog.value = false
    newUser.value = {
      username: '',
      password: '',
      is_superuser: false,
      user_type: props.userType
    }
  } catch (err) {
    // Error will be handled by the store
  }
}

function getRoleColor(user: User): string {
  if (props.userType === 'web') {
    return user.is_superuser ? 'error' : 'primary'
  } else {
    // For chat users
    if (user.is_superuser) return 'error' // admin
    return user.role === 'basic' ? 'success' : 'primary' // basic or user
  }
}

function getRoleText(user: User): string {
  if (props.userType === 'web') {
    return user.is_superuser ? 'Admin' : 'User'
  } else {
    // For chat users
    if (user.is_superuser) return 'Admin'
    return user.role || 'User'
  }
}

async function deleteUser(user: User) {
  try {
    await store.dispatch('users/deleteUser', {
      id: user.id,
      userType: props.userType
    })
  } catch (err) {
    // Error will be handled by the store
  }
}

async function handleEdit() {
  const { valid } = await editForm.value.validate()
  if (!valid) return

  try {
    const data: Record<string, any> = {
      username: editedUser.value.username,
      user_type: props.userType
    }

    if (editedUser.value.password) {
      data.password = editedUser.value.password
    }

    if (currentUser.value?.is_superuser) {
      data.is_active = editedUser.value.is_active
      if (editedUser.value.id !== currentUser.value?.id) {
        data.is_superuser = editedUser.value.is_superuser
      }
    }

    if (props.userType === 'chat') {
      data.role = editedUser.value.role
      data.display_name = editedUser.value.display_name
    }

    await store.dispatch('users/updateUser', {
      id: editedUser.value.id,
      data,
      userType: props.userType
    })
    showEditDialog.value = false
  } catch (err) {
    // Error will be handled by the store
  }
}
</script>
