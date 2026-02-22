import { useState, useEffect } from 'react'
import { Server, Activity, AlertTriangle, CheckCircle2, AlertCircle } from 'lucide-react'
import { Card, CardContent } from './components/ui/Card'
import { Badge } from './components/ui/Badge'
import { format } from 'date-fns'

interface LogEntry {
    id: number;
    source_ip: string;
    severity: string;
    message: string;
    diagnosis: string;
    recommendation?: string;
    timestamp: string;
}

export default function Dashboard() {
    const [logs, setLogs] = useState<LogEntry[]>([])
    const [backendOnline, setBackendOnline] = useState(false)

    const fetchLogs = async () => {
        try {
            const response = await fetch('http://localhost:8000/logs')
            if (response.ok) {
                const data = await response.json()
                setLogs(data)
                setBackendOnline(true)
            } else {
                setBackendOnline(false)
            }
        } catch (err) {
            console.error("Fehler beim Abrufen der Logs:", err)
            setBackendOnline(false)
        }
    }

    // Polling für Echtzeit-Updates
    useEffect(() => {
        fetchLogs()
        const interval = setInterval(fetchLogs, 5000)
        return () => clearInterval(interval)
    }, [])

    // Statistiken berechnen
    const criticalCount = logs.filter(l => l.severity === 'CRITICAL').length
    const highCount = logs.filter(l => l.severity === 'HIGH').length
    const infoCount = logs.filter(l => l.severity === 'INFO').length

    return (
        <div className="min-h-screen bg-slate-900 text-slate-100 p-8 w-full max-w-7xl mx-auto">
            {/* Header */}
            <header className="flex items-center justify-between mb-8 pb-4 border-b border-slate-800">
                <div className="flex items-center gap-3">
                    <Activity className="text-blue-500 w-8 h-8" />
                    <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
                        AlertGateAI
                    </h1>
                </div>
                <div className="flex items-center gap-4 text-sm font-medium">
                    <span className="flex items-center gap-2 bg-slate-800 px-3 py-1.5 rounded-full border border-slate-700">
                        <Server className={`w-4 h-4 ${backendOnline ? 'text-emerald-400' : 'text-slate-400'}`} />
                        <span>Backend: <span className={backendOnline ? 'text-emerald-400' : 'text-red-400'}>
                            {backendOnline ? 'Online' : 'Offline'}
                        </span></span>
                    </span>
                </div>
            </header>

            {/* Stats Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <Card>
                    <CardContent className="p-6">
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-red-500/10 rounded-lg">
                                <AlertCircle className="w-6 h-6 text-red-500" />
                            </div>
                            <div>
                                <p className="text-slate-400 text-sm font-medium">Kritische Alarme</p>
                                <p className="text-2xl font-bold text-white">{criticalCount}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardContent className="p-6">
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-amber-500/10 rounded-lg">
                                <AlertTriangle className="w-6 h-6 text-amber-500" />
                            </div>
                            <div>
                                <p className="text-slate-400 text-sm font-medium">Warnungen (High)</p>
                                <p className="text-2xl font-bold text-white">{highCount}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardContent className="p-6">
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-emerald-500/10 rounded-lg">
                                <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                            </div>
                            <div>
                                <p className="text-slate-400 text-sm font-medium">Info Events (24h)</p>
                                <p className="text-2xl font-bold text-white">{infoCount}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Main Content: Log Table */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden backdrop-blur-sm">
                <div className="p-6 border-b border-slate-700/50">
                    <h2 className="text-lg font-semibold text-white">Letzte Infrastruktur Events</h2>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="text-xs uppercase bg-slate-800/80 text-slate-400 border-b border-slate-700">
                            <tr>
                                <th className="px-6 py-4 font-medium">Zeitpunkt</th>
                                <th className="px-6 py-4 font-medium">Source IP</th>
                                <th className="px-6 py-4 font-medium">Severity</th>
                                <th className="px-6 py-4 font-medium">Ursprungs-Log</th>
                                <th className="px-6 py-4 font-medium">KI-Diagnose</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700/50">
                            {logs.map((log) => (
                                <tr key={log.id} className="hover:bg-slate-700/20 transition-colors">
                                    <td className="px-6 py-4 whitespace-nowrap text-slate-300">
                                        {format(new Date(`${log.timestamp}Z`), 'HH:mm:ss')}
                                    </td>
                                    <td className="px-6 py-4 font-mono text-slate-300">
                                        {log.source_ip}
                                    </td>
                                    <td className="px-6 py-4">
                                        <Badge variant={
                                            log.severity.toLowerCase() === 'critical' ? 'critical' :
                                                log.severity.toLowerCase() === 'high' ? 'high' :
                                                    log.severity.toLowerCase() === 'info' ? 'info' : 'default'
                                        }>
                                            {log.severity}
                                        </Badge>
                                    </td>
                                    <td className="px-6 py-4 font-mono text-xs text-slate-400 max-w-xs truncate" title={log.message}>
                                        {log.message}
                                    </td>
                                    <td className="px-6 py-4 text-slate-300" title={log.recommendation}>
                                        {log.diagnosis}
                                    </td>
                                </tr>
                            ))}
                            {logs.length === 0 && (
                                <tr>
                                    <td colSpan={5} className="px-6 py-8 text-center text-slate-500">
                                        Keine Events gefunden. Warte auf eingehende Logs...
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}
