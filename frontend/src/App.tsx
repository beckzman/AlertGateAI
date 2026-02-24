import { useState } from 'react'
import Dashboard from './Dashboard'
import Notifications from './Notifications'
import Alerting from './Alerting'
import './App.css'

export type Page = 'dashboard' | 'notifications' | 'alerting'

function App() {
    const [currentPage, setCurrentPage] = useState<Page>('dashboard')

    return (
        <>
            {currentPage === 'dashboard' && <Dashboard onNavigate={setCurrentPage} />}
            {currentPage === 'notifications' && <Notifications onNavigate={setCurrentPage} />}
            {currentPage === 'alerting' && <Alerting onNavigate={setCurrentPage} />}
        </>
    )
}

export default App
