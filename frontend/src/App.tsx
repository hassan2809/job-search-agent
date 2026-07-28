import { Route, Routes } from 'react-router-dom'
import { LeadsPage } from '@/features/leads/components/LeadsPage'
import { LeadDetailPage } from '@/features/leads/components/LeadDetailPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<LeadsPage />} />
      <Route path="/leads/:id" element={<LeadDetailPage />} />
    </Routes>
  )
}

export default App
