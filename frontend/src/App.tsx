import { useState } from 'react'
import Dashboard from './Dashboard'
import Notifications from './Notifications'
import './App.css'

export type Page = 'dashboard' | 'notifications'

function App() {
    const [currentPage, setCurrentPage] = useState<Page>('dashboard')

    return (
        <>
            {currentPage === 'dashboard' && <Dashboard onNavigate={setCurrentPage} />}
            {currentPage === 'notifications' && <Notifications onNavigate={setCurrentPage} />}
        </>
    )
}

export default App
