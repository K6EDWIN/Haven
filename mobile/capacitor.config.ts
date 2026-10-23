import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.haven.wellbeing',
  appName: 'Haven',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
  },
}

export default config
