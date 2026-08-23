import { Route, Routes } from 'react-router-dom'
import { LeadsPage } from '@/features/leads/components/LeadsPage'
import { LeadDetailPage } from '@/features/leads/components/LeadDetailPage'
import { EfficiencyPage } from '@/features/efficiency/components/EfficiencyPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<LeadsPage />} />
      <Route path="/leads/:id" element={<LeadDetailPage />} />
      <Route path="/efficiency" element={<EfficiencyPage />} />
    </Routes>
  )
}

export default App
