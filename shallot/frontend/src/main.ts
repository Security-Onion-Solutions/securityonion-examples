// Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
// or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
// https://securityonion.net/license; you may not use this file except in compliance with the
// Elastic License 2.0.

import { createApp } from 'vue'
import { createVuetify } from 'vuetify'
import App from './App.vue'
import { store } from './store'
import router from './router'

// Vuetify
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

// Get initial theme from localStorage
const initialTheme = localStorage.getItem('theme') === 'dark' ? 'dark' : 'light'

// Create Vuetify instance
const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: initialTheme,
    themes: {
      light: {
        colors: {
          primary: '#1867C0',
          secondary: '#5CBBF6',
        },
      },
      dark: {
        colors: {
          primary: '#2196F3',
          secondary: '#64B5F6',
        },
      },
    },
  },
})

// Watch theme changes
store.watch(
  (state) => state.theme.isDark,
  (isDark) => {
    vuetify.theme.global.name.value = isDark ? 'dark' : 'light'
  }
)

// Create and mount app
const app = createApp(App)
app.use(vuetify)
app.use(store)
app.use(router)
app.mount('#app')
