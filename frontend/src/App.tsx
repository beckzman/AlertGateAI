import { useState, useEffect } from 'react'
import Dashboard from './Dashboard'
import Notifications from './Notifications'
import Alerting from './Alerting'
import Settings from './Settings'
import './App.css'

export type Page = 'dashboard' | 'notifications' | 'alerting' | 'settings'

function App() {
    const [currentPage, setCurrentPage] = useState<Page>('dashboard')
    const [theme, setTheme] = useState<'dark' | 'light' | 'fallout'>(() => {
        return (localStorage.getItem('app-theme') as 'dark' | 'light' | 'fallout') || 'dark';
    });

    useEffect(() => {
        document.body.className = theme === 'dark' ? '' : `theme-${theme}`;
        localStorage.setItem('app-theme', theme);
    }, [theme]);

    return (
        <>
            {currentPage === 'dashboard' && <Dashboard onNavigate={setCurrentPage} />}
            {currentPage === 'notifications' && <Notifications onNavigate={setCurrentPage} />}
            {currentPage === 'alerting' && <Alerting onNavigate={setCurrentPage} />}
            {currentPage === 'settings' && <Settings onNavigate={setCurrentPage} />}

            {/* Floating Theme Toggle */}
            <div className="fixed bottom-4 right-4 z-50 flex gap-2 bg-slate-900/50 backdrop-blur-md p-2 rounded-full border border-slate-700/50 shadow-xl items-center">
                <span className="text-[10px] text-slate-400 font-mono px-2 uppercase mix-blend-difference">Theme</span>
                <button
                    onClick={() => setTheme('light')}
                    className={`w-6 h-6 rounded-full border-2 transition-transform hover:scale-110 ${theme === 'light' ? 'border-blue-500 scale-110' : 'border-slate-500'} bg-slate-200`}
                    title="Light Theme"
                />
                <button
                    onClick={() => setTheme('dark')}
                    className={`w-6 h-6 rounded-full border-2 transition-transform hover:scale-110 ${theme === 'dark' ? 'border-blue-500 scale-110' : 'border-slate-500'} bg-slate-800`}
                    title="Dark Theme"
                />
                <button
                    onClick={() => setTheme('fallout')}
                    className={`w-6 h-6 rounded-full border-2 transition-transform hover:scale-110 ${theme === 'fallout' ? 'border-emerald-500 scale-110' : 'border-slate-500'} bg-[#112211] flex items-center justify-center`}
                    title="Terminal Theme"
                >
                    <span className="text-[10px] text-emerald-500 font-mono font-bold leading-none mb-1">_</span>
                </button>
            </div>
        </>
    )
}

export default App
