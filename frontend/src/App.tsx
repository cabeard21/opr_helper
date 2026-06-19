import { Navigate, Route, Routes } from 'react-router-dom'

import { CalcPage } from './pages/CalcPage'
import { AdvisorPage } from './pages/AdvisorPage'
import { FactionBrowserPage } from './pages/FactionBrowserPage'
import { FactionUnitsPage } from './pages/FactionUnitsPage'
import { ListBuilderPage } from './pages/ListBuilderPage'
import { ListsPage } from './pages/ListsPage'
import { AppShell } from './components/AppShell'

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route element={<FactionBrowserPage />} path="/" />
        <Route element={<FactionUnitsPage />} path="/factions/:id" />
        <Route element={<AdvisorPage />} path="/advisor" />
        <Route element={<ListsPage />} path="/lists" />
        <Route element={<ListBuilderPage />} path="/lists/:id" />
        <Route element={<CalcPage />} path="/calc" />
        <Route element={<Navigate replace to="/" />} path="*" />
      </Routes>
    </AppShell>
  )
}
