<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>Documentation</v-card-title>
          <v-card-text>
            <div v-html="renderedContent" class="markdown-body"></div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const renderedContent = ref('')

onMounted(async () => {
  try {
    // Get the doc path from the route params
    const docPath = route.params.path as string
    const response = await axios.get(`/api/docs/${docPath}`, {
      transformResponse: [(data) => data], // Prevent axios from parsing as JSON
      responseType: 'text'
    })
    renderedContent.value = response.data
    
    // Handle anchor links after content is loaded
    if (window.location.hash) {
      const id = window.location.hash.replace('#', '')
      setTimeout(() => {
        const element = document.getElementById(id)
        if (element) {
          element.scrollIntoView({ behavior: 'smooth' })
        }
      }, 100)
    }
  } catch (error) {
    console.error('Failed to load documentation:', error)
    renderedContent.value = '<h1>Error</h1><p>Failed to load documentation.</p>'
  }
})
</script>

<style>
.markdown-body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 16px;
  line-height: 1.5;
  word-wrap: break-word;
}

.markdown-body h1 {
  font-size: 2em;
  margin-bottom: 16px;
  font-weight: 600;
  padding-bottom: 0.3em;
  border-bottom: 1px solid #eaecef;
}

.markdown-body h2 {
  font-size: 1.5em;
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  padding-bottom: 0.3em;
  border-bottom: 1px solid #eaecef;
}

.markdown-body ul {
  padding-left: 2em;
  margin-bottom: 16px;
}

.markdown-body li {
  margin: 0.25em 0;
}

.markdown-body code {
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 85%;
  background-color: rgba(27,31,35,0.05);
  border-radius: 3px;
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
}

.markdown-body a {
  color: #0366d6;
  text-decoration: none;
}

.markdown-body a:hover {
  text-decoration: underline;
}
</style>
