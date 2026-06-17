import { Navigate, Route, Routes } from 'react-router-dom'

import { CalcPage } from './pages/CalcPage'
import { FactionBrowserPage } from './pages/FactionBrowserPage'
import { FactionUnitsPage } from './pages/FactionUnitsPage'
import { ListBuilderPage } from './pages/ListBuilderPage'
import { ListsPage } from './pages/ListsPage'

export default function App() {
  return (
    <main className="min-h-screen bg-stone-50 text-stone-950">
      <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <Routes>
          <Route element={<FactionBrowserPage />} path="/" />
          <Route element={<FactionUnitsPage />} path="/factions/:id" />
          <Route element={<ListsPage />} path="/lists" />
          <Route element={<ListBuilderPage />} path="/lists/:id" />
          <Route element={<CalcPage />} path="/calc" />
          <Route element={<Navigate replace to="/" />} path="*" />
        </Routes>
      </div>
    </main>
  )
}
