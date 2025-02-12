<template>
  <v-container>
    <v-row>
      <v-col>
        <h1 class="text-h4 mb-4">Commands</h1>
        
        <!-- Available Commands -->
        <v-card class="mb-4">
          <v-card-title>Available Commands</v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item v-for="cmd in commands" :key="cmd.name">
                <template v-slot:prepend>
                  <v-icon>mdi-console</v-icon>
                </template>
                
                <v-list-item-title class="font-weight-bold">
                  !{{ cmd.name }}
                </v-list-item-title>
                
                <v-list-item-subtitle>
                  {{ cmd.description }}
                </v-list-item-subtitle>
                
                <v-list-item-subtitle class="font-monospace">
                  Example: {{ cmd.example }}
                </v-list-item-subtitle>

                <template v-slot:append>
                  <v-chip
                    :color="getPermissionColor(cmd.permission)"
                    size="small"
                    variant="tonal"
                  >
                    {{ formatPermission(cmd.permission) }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>

        <!-- Command Execution -->
        <v-card>
          <v-card-title>Execute Command</v-card-title>
          <v-card-text>
            <v-form @submit.prevent="testCommand">
              <v-text-field
                v-model="command"
                label="Command (e.g. !alerts)"
                placeholder="Enter a command to test"
                :rules="[v => !!v || 'Command is required']"
                required
              />
              <v-btn
                color="primary"
                type="submit"
                :loading="loading"
                :disabled="!command"
              >
                Execute Command
              </v-btn>
            </v-form>

            <v-divider class="my-4" />

            <div v-if="response" class="mt-4">
              <h3 class="text-h6 mb-2">Response:</h3>
              <v-card :color="response.success ? 'grey-lighten-4' : 'error-lighten-5'">
                <v-card-text>
                  <div v-if="response.success">
                    <!-- Format alerts response -->
                    <div v-if="response.response.startsWith('Found')">
                      <div class="text-subtitle-1 font-weight-bold mb-2">
                        {{ response.response.split('\n')[0] }}
                      </div>
                      <v-list class="bg-transparent">
                        <template v-for="(alert, i) in parseAlerts(response.response)" :key="i">
                          <v-list-item>
                            <template v-slot:prepend>
                              <v-icon :color="getSeverityColor(alert.severity)" class="mr-2">
                                mdi-alert-circle
                              </v-icon>
                            </template>
                            <v-list-item-title class="text-subtitle-1 font-weight-bold">
                              {{ alert.name }}
                            </v-list-item-title>
                            <v-list-item-subtitle class="mt-1">
                              <div class="d-flex align-center">
                                <v-chip
                                  :color="getSeverityColor(alert.severity)"
                                  size="small"
                                  class="mr-2"
                                  variant="tonal"
                                >
                                  {{ alert.severity_label }}
                                </v-chip>
                              </div>
                              <div class="mt-2">
                                <div class="text-grey d-flex align-center mb-1">
                                  <span class="font-weight-medium mr-2">Rule ID:</span>
                                  <span>{{ alert.ruleid }}</span>
                                </div>
                                <div class="text-grey d-flex align-center mb-1">
                                  <span class="font-weight-medium mr-2">Event ID:</span>
                                  <span>{{ alert.eventid }}</span>
                                </div>
                                <div class="text-grey d-flex align-center mb-1">
                                  <span class="font-weight-medium mr-2">Source:</span>
                                  <span>{{ alert.source }}</span>
                                </div>
                                <div class="text-grey d-flex align-center mb-1">
                                  <span class="font-weight-medium mr-2">Destination:</span>
                                  <span>{{ alert.destination }}</span>
                                </div>
                                <div class="text-grey d-flex align-center mb-1">
                                  <span class="font-weight-medium mr-2">Observer:</span>
                                  <span>{{ alert.observer_name }}</span>
                                </div>
                                <div class="text-grey d-flex align-center">
                                  <span class="font-weight-medium mr-2">Timestamp:</span>
                                  <span>{{ alert.timestamp }}</span>
                                </div>
                              </div>
                            </v-list-item-subtitle>
                          </v-list-item>
                          <v-divider v-if="i < parseAlerts(response.response).length - 1"></v-divider>
                        </template>
                      </v-list>
                    </div>
                    <!-- Format error response -->
                    <div v-else class="text-body-1">
                      {{ response.response }}
                    </div>
                  </div>
                  <div v-else class="text-error">
                    {{ response.response }}
                  </div>
                </v-card-text>
              </v-card>
            </div>

            <v-alert
              v-if="error"
              type="error"
              class="mt-4"
            >
              {{ error }}
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useStore } from 'vuex'
import { apiRequest } from '../../store/utils/api'
import { CommandPermission } from '../../types'

interface Command {
  name: string
  description: string
  example: string
  permission: CommandPermission
}

interface Alert {
  name: string
  severity: string
  severity_label: string
  ruleid: string
  eventid: string
  source: string
  destination: string
  observer_name: string
  timestamp: string
}

interface CommandResponse {
  command: string
  response: string
  success: boolean
}

const store = useStore()
const command = ref('')
const response = ref<CommandResponse | null>(null)
const error = ref('')
const loading = ref(false)
const commands = ref<Command[]>([])

// Format permission level for display
const formatPermission = (permission: CommandPermission): string => {
  return permission.charAt(0).toUpperCase() + permission.slice(1).toLowerCase()
}

// Get color for permission level
const getPermissionColor = (permission: CommandPermission): string => {
  switch (permission) {
    case 'public':
      return 'success'
    case 'basic':
      return 'warning'
    case 'admin':
      return 'error'
    default:
      return 'info'
  }
}

// Fetch available commands
const fetchCommands = async () => {
  try {
    const data = await apiRequest('/commands/')
    commands.value = data.commands
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load commands'
  }
}

// Load commands on mount
onMounted(() => {
  fetchCommands()
})

const parseAlerts = (responseText: string): Alert[] => {
  console.log('Parsing response:', responseText)
  
  // Split into alert blocks
  const blocks = responseText.split('\n\n').slice(1) // Skip summary line
  console.log('Alert blocks:', blocks)
  
  const alerts: Alert[] = []
  
  for (const block of blocks) {
    if (!block.trim()) continue
    
    console.log('Processing block:', block)
    const lines = block.split('\n').map(line => line.trim())
    
    // First line should be [severity] - name
    const titleMatch = lines[0].match(/\[(.*?)\] - (.*)/)
    if (!titleMatch) {
      console.log('Failed to match title line:', lines[0])
      continue
    }
    
    const alert: Alert = {
      severity: titleMatch[1],
      severity_label: titleMatch[1], // Set severity_label to the same value as severity
      name: titleMatch[2],
      ruleid: '',
      eventid: '',
      source: '',
      destination: '',
      observer_name: '',
      timestamp: ''
    }
    
    // Process remaining lines
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i]
      if (line.startsWith('ruleid:')) {
        alert.ruleid = line.substring(7).trim()
      } else if (line.startsWith('eventid:')) {
        alert.eventid = line.substring(8).trim()
      } else if (line.startsWith('source:')) {
        alert.source = line.substring(7).trim()
      } else if (line.startsWith('destination:')) {
        alert.destination = line.substring(12).trim()
      } else if (line.startsWith('observer.name:')) {
        alert.observer_name = line.substring(13).trim()
      } else if (line.startsWith('timestamp:')) {
        alert.timestamp = line.substring(10).trim()
      }
    }
    
    console.log('Created alert:', alert)
    alerts.push(alert)
  }
  
  console.log('Parsed alerts:', alerts)
  return alerts
}

const getSeverityColor = (severity: string): string => {
  severity = severity.toLowerCase()
  if (severity.includes('high')) return 'error'
  if (severity.includes('medium')) return 'warning'
  if (severity.includes('low')) return 'success'
  return 'info'
}

const testCommand = async () => {
  if (!command.value) return
  
  loading.value = true
  error.value = ''
  response.value = null
  
  try {
    response.value = await apiRequest('/commands/test-command', {
      method: 'POST',
      body: JSON.stringify({ command: command.value })
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'An error occurred'
  } finally {
    loading.value = false
  }
}
</script>
