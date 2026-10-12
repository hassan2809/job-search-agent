import { Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { LeadsPage } from '@/features/leads/components/LeadsPage'
import { LeadDetailPage } from '@/features/leads/components/LeadDetailPage'
import { EfficiencyPage } from '@/features/efficiency/components/EfficiencyPage'

function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<LeadsPage />} />
        <Route path="/leads/:id" element={<LeadDetailPage />} />
        <Route path="/efficiency" element={<EfficiencyPage />} />
      </Route>
    </Routes>
  )
}

export default App
