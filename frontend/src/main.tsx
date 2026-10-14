import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import './i18n'
import { setupPwa } from './lib/pwa'
import { setupMonitoring } from './lib/monitoring'

setupMonitoring()
setupPwa()

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)