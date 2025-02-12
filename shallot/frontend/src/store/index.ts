/*
 * Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
 * or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
 * https://securityonion.net/license; you may not use this file except in compliance with the
 * Elastic License 2.0.
 */

import { createStore } from 'vuex'
import { auth } from './modules/auth'
import users from './modules/users'
import theme from './modules/theme'
import settings from './modules/settings'

import { ThemeState } from './modules/theme'
import { SettingsState } from './modules/settings'

export interface RootState {
  version: string
  theme: ThemeState
  settings: SettingsState
}

export const store = createStore<RootState>({
  state: () => ({
    version: '1.0.0',
    theme: {
      isDark: localStorage.getItem('theme') === 'dark'
    },
    settings: {
      settings: [],
      loading: false,
      error: null
    }
  }),
  modules: {
    auth,
    users,
    theme,
    settings
  }
})

export function useStore() {
  return store
}
