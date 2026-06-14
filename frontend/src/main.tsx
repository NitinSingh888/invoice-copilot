import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { TooltipProvider } from '@/components/ui/tooltip'
import '@fontsource-variable/geist/index.css'
import '@fontsource-variable/geist-mono/index.css'
import './index.css'
import App from './App.tsx'
import { AuthGate } from '@/components/auth/AuthGate'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <TooltipProvider delayDuration={400}>
        <AuthGate>
          {(user) => <App userEmail={user.email} orgName={user.orgName} orgRole={user.orgRole} />}
        </AuthGate>
      </TooltipProvider>
    </BrowserRouter>
  </StrictMode>,
)
