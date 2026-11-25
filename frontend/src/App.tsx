import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import ErrorBoundary from './components/ErrorBoundary'
import NavBar from './components/NavBar'
import { useAuth } from './auth/AuthContext'
import ProblemsPage from './pages/ProblemsPage'
import ProblemPage from './pages/ProblemPage'
import { LoginPage, RegisterPage } from './pages/AuthPages'
import ProfilePage from './pages/ProfilePage'
import type { ReactNode } from 'react'
import { PlanPage, PlansPage } from './pages/PlansPage'
import LearnPage from './pages/LearnPage'
import SourcesPage from './pages/SourcesPage'
import { BookPage, ChapterPage } from './pages/DocsPages'
import { InterviewSession, InterviewStart } from './pages/InterviewPage'
import { ContestPage, LeaderboardPage, UserPage } from './pages/CommunityPages'

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="empty"><span className="spinner" /></div>
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  const location = useLocation()
  return (
    <div className="app">
      <NavBar />
      <main>
        <ErrorBoundary resetKey={location.pathname}>
        <Routes>
          <Route path="/" element={<Navigate to="/problems" replace />} />
          <Route path="/problems" element={<ProblemsPage />} />
          <Route path="/problems/:slug" element={<ProblemPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/profile" element={<RequireAuth><ProfilePage /></RequireAuth>} />
          <Route path="/plans" element={<PlansPage />} />
          <Route path="/plans/:id" element={<PlanPage />} />
          <Route path="/learn" element={<LearnPage />} />
          <Route path="/learn/docs/:book" element={<BookPage />} />
          <Route path="/learn/docs/:book/:chapter" element={<ChapterPage />} />
          <Route path="/sources" element={<SourcesPage />} />
          <Route path="/interview" element={<RequireAuth><InterviewStart /></RequireAuth>} />
          <Route path="/interview/:id" element={<RequireAuth><InterviewSession /></RequireAuth>} />
          <Route path="/leaderboard" element={<LeaderboardPage />} />
          <Route path="/contest" element={<ContestPage />} />
          <Route path="/contest/:number" element={<ContestPage />} />
          <Route path="/u/:username" element={<UserPage />} />
          <Route path="*" element={<div className="empty">Page not found.</div>} />
        </Routes>
        </ErrorBoundary>
      </main>
    </div>
  )
}
