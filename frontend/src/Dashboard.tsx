import { useState, useEffect, useCallback } from 'react'
import { Server, Activity, AlertTriangle, CheckCircle2, AlertCircle, Search, Filter, RefreshCw, Bell, Settings } from 'lucide-react'
import type { Page } from './App'
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/Card'
import { Badge } from './components/ui/Badge'
import { format } from 'date-fns'
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from 'recharts'

interface LogEntry {
    id: number;
    source_ip: string;
    severity: string;
    message: string;
    diagnosis: string;
    recommendation?: string;
    timestamp: string;
    count?: number; // Neu für Gruppierung
}

interface Stats {
    severity: Record<string, number>;
    timeline: { hour: string; CRITICAL: number; HIGH: number; INFO: number }[];
}

interface DashboardProps {
    onNavigate: (page: Page) => void
}

export default function Dashboard({ onNavigate }: DashboardProps) {
    const [logs, setLogs] = useState<LogEntry[]>([])
    const [stats, setStats] = useState<Stats | null>(null)
    const [backendOnline, setBackendOnline] = useState(false)
    const [loading, setLoading] = useState(true)

    // Filter States
    const [severityFilter, setSeverityFilter] = useState<string>('')
    const [searchFilter, setSearchFilter] = useState<string>('')

    const apiUrl = import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`

    const fetchData = useCallback(async () => {
        try {
            // Logs mit Filtern abrufen
            const params = new URLSearchParams()
            if (severityFilter) params.append('severity', severityFilter)
            if (searchFilter) params.append('source_ip', searchFilter)

            const [logsRes, statsRes] = await Promise.all([
                fetch(`${apiUrl}/logs?${params.toString()}`),
                fetch(`${apiUrl}/stats`)
            ])

            if (logsRes.ok && statsRes.ok) {
                const logsData = await logsRes.json()
                const statsData = await statsRes.json()
                setLogs(logsData)
                setStats(statsData)
                setBackendOnline(true)
            } else {
                setBackendOnline(false)
            }
        } catch (err) {
            console.error("Fehler beim Abrufen der Daten:", err)
            setBackendOnline(false)
        } finally {
            setLoading(false)
        }
    }, [severityFilter, searchFilter, apiUrl])

    useEffect(() => {
        fetchData()
        const interval = setInterval(fetchData, 10000) // Alle 10s aktualisieren
        return () => clearInterval(interval)
    }, [fetchData])


    const [groupBySource, setGroupBySource] = useState(false)

    // Tabellen-Filter (client-seitig)
    const [colDatum, setColDatum] = useState('')
    const [colSource, setColSource] = useState('')
    const [colSeverity, setColSeverity] = useState('')
    const [colMessage, setColMessage] = useState('')
    const [colDiagnosis, setColDiagnosis] = useState('')

    const groupedLogs = groupBySource ? logs.reduce((acc: (LogEntry & { count?: number })[], log) => {
        const key = `${log.source_ip}-${log.diagnosis}`
        const existing = acc.find(l => `${l.source_ip}-${l.diagnosis}` === key)
        if (existing) {
            existing.count = (existing.count || 1) + 1
            if (new Date(log.timestamp) > new Date(existing.timestamp)) {
                existing.timestamp = log.timestamp
            }
        } else {
            acc.push({ ...log, count: 1 })
        }
        return acc
    }, []) : logs

    const displayedLogs = groupedLogs.filter(log => {
        const datum = format(new Date(`${log.timestamp}Z`), 'dd.MM.yyyy')
        if (colDatum && !datum.includes(colDatum)) return false
        if (colSource && !log.source_ip.toLowerCase().includes(colSource.toLowerCase())) return false
        if (colSeverity && log.severity !== colSeverity) return false
        if (colMessage && !log.message.toLowerCase().includes(colMessage.toLowerCase())) return false
        if (colDiagnosis && !(log.diagnosis ?? '').toLowerCase().includes(colDiagnosis.toLowerCase())) return false
        return true
    })

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8 w-full max-w-7xl mx-auto space-y-8">
            {/* Header */}
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800/60">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-500/10 rounded-xl border border-blue-500/20">
                        <Activity className="text-blue-500 w-8 h-8" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
                            AlertGateAI
                        </h1>
                        <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Infrastructure Monitoring</p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <button
                        onClick={() => onNavigate('alerting')}
                        className="flex items-center gap-2 px-3 py-2 bg-slate-900/50 hover:bg-slate-800 rounded-xl border border-slate-800 text-sm text-slate-400 hover:text-white transition-colors"
                    >
                        <Settings className="w-4 h-4" />
                        <span>Alarmierung</span>
                    </button>
                    <button
                        onClick={() => onNavigate('notifications')}
                        className="flex items-center gap-2 px-3 py-2 bg-slate-900/50 hover:bg-slate-800 rounded-xl border border-slate-800 text-sm text-slate-400 hover:text-white transition-colors"
                    >
                        <Bell className="w-4 h-4" />
                        <span>Benachrichtigungen</span>
                    </button>
                    <div className="flex items-center gap-2 bg-slate-900/50 backdrop-blur-md px-4 py-2 rounded-xl border border-slate-800">
                        <div className={`w-2 h-2 rounded-full animate-pulse ${backendOnline ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-red-500'}`} />
                        <span className="text-sm font-semibold">
                            Backend: <span className={backendOnline ? 'text-emerald-400' : 'text-red-400'}>
                                {backendOnline ? 'Online' : 'Offline'}
                            </span>
                        </span>
                    </div>
                    <button
                        onClick={() => fetchData()}
                        className="p-2 hover:bg-slate-800 rounded-lg transition-colors border border-slate-800"
                    >
                        <RefreshCw className={`w-4 h-4 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                </div>
            </header>

            {/* Stats Row */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <Card className="bg-gradient-to-br from-slate-900 to-slate-900/50">
                    <CardContent className="p-6">
                        <div className="flex justify-between items-start">
                            <div>
                                <p className="text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">Total Events</p>
                                <p className="text-3xl font-bold text-white">{logs.length}</p>
                            </div>
                            <div className="p-2 bg-slate-800 rounded-lg">
                                <Server className="w-5 h-5 text-slate-400" />
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card className="bg-gradient-to-br from-slate-900 to-slate-900/50 border-l-4 border-l-red-500/50">
                    <CardContent className="p-6">
                        <div className="flex justify-between items-start">
                            <div>
                                <p className="text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">Critical</p>
                                <p className="text-3xl font-bold text-red-400">{stats?.severity?.CRITICAL || 0}</p>
                            </div>
                            <div className="p-2 bg-red-500/10 rounded-lg">
                                <AlertCircle className="w-5 h-5 text-red-500" />
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card className="bg-gradient-to-br from-slate-900 to-slate-900/50 border-l-4 border-l-amber-500/50">
                    <CardContent className="p-6">
                        <div className="flex justify-between items-start">
                            <div>
                                <p className="text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">High Priority</p>
                                <p className="text-3xl font-bold text-amber-400">{stats?.severity?.HIGH || 0}</p>
                            </div>
                            <div className="p-2 bg-amber-500/10 rounded-lg">
                                <AlertTriangle className="w-5 h-5 text-amber-500" />
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card className="bg-gradient-to-br from-slate-900 to-slate-900/50 border-l-4 border-l-blue-500/50">
                    <CardContent className="p-6">
                        <div className="flex justify-between items-start">
                            <div>
                                <p className="text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">Info / Regular</p>
                                <p className="text-3xl font-bold text-blue-400">{stats?.severity?.INFO || 0}</p>
                            </div>
                            <div className="p-2 bg-blue-500/10 rounded-lg">
                                <CheckCircle2 className="w-5 h-5 text-blue-500" />
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Charts & Visualization */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <Card className="lg:col-span-2">
                    <CardHeader>
                        <CardTitle className="text-sm font-medium text-slate-400 flex items-center gap-2">
                            <Activity className="w-4 h-4" /> Alert Frequenz (letzte 24h)
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="h-72 mt-4">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={stats?.timeline || []} barCategoryGap="20%">
                                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                                <XAxis
                                    dataKey="hour"
                                    stroke="#64748b"
                                    fontSize={10}
                                    interval={2}
                                    tickFormatter={(val) => format(new Date(val), 'HH:mm')}
                                />
                                <YAxis stroke="#64748b" fontSize={10} allowDecimals={false} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }}
                                    labelStyle={{ color: '#94a3b8', marginBottom: 4 }}
                                    labelFormatter={(val) => format(new Date(val), 'dd.MM.yyyy HH:mm')}
                                    cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                                />
                                <Legend
                                    wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                                    formatter={(value) => <span style={{ color: '#94a3b8' }}>{value}</span>}
                                />
                                <Bar dataKey="CRITICAL" stackId="a" fill="#ef4444" fillOpacity={0.85} />
                                <Bar dataKey="HIGH" stackId="a" fill="#f59e0b" fillOpacity={0.85} />
                                <Bar dataKey="INFO" stackId="a" fill="#3b82f6" fillOpacity={0.85} />
                            </BarChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="text-sm font-medium text-slate-400 flex items-center gap-2">
                            <Filter className="w-4 h-4" /> Filter & Suche
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4 pt-4">
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-500 uppercase">Schlagwort / IP</label>
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                <input
                                    type="text"
                                    placeholder="Suche..."
                                    className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all"
                                    value={searchFilter}
                                    onChange={(e) => setSearchFilter(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-500 uppercase">Severity</label>
                            <select
                                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none appearance-none"
                                value={severityFilter}
                                onChange={(e) => setSeverityFilter(e.target.value)}
                            >
                                <option value="">Alle Severities</option>
                                <option value="CRITICAL">Critical</option>
                                <option value="HIGH">High</option>
                                <option value="INFO">Info</option>
                            </select>
                        </div>

                        <div className="flex items-center gap-2 pt-2">
                            <input
                                type="checkbox"
                                id="group-toggle"
                                className="w-4 h-4 rounded border-slate-700 bg-slate-900 text-blue-500 focus:ring-blue-500"
                                checked={groupBySource}
                                onChange={(e) => setGroupBySource(e.target.checked)}
                            />
                            <label htmlFor="group-toggle" className="text-xs text-slate-400 cursor-pointer select-none">
                                Ähnliche Events gruppieren
                            </label>
                        </div>

                        <button
                            onClick={() => { setSeverityFilter(''); setSearchFilter(''); setGroupBySource(false); }}
                            className="w-full py-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
                        >
                            Filter zurücksetzen
                        </button>
                    </CardContent>
                </Card>
            </div>

            {/* Main Content: Log Table */}
            <Card className="overflow-hidden">
                <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle className="text-white">Infrastruktur Events</CardTitle>
                    <Badge variant="default">{displayedLogs.length} Ergebnisse</Badge>
                </CardHeader>

                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="text-xs bg-slate-900/80 text-slate-500 border-b border-slate-700/50">
                            {/* Spaltenbezeichnungen */}
                            <tr className="uppercase">
                                <th className="px-4 pt-4 pb-1 font-semibold">Datum</th>
                                <th className="px-4 pt-4 pb-1 font-semibold">Uhrzeit</th>
                                <th className="px-4 pt-4 pb-1 font-semibold">Source</th>
                                <th className="px-4 pt-4 pb-1 font-semibold">Severity</th>
                                <th className="px-4 pt-4 pb-1 font-semibold">Log Message</th>
                                <th className="px-4 pt-4 pb-1 font-semibold text-blue-400">KI-Diagnose</th>
                            </tr>
                            {/* Filter-Zeile */}
                            <tr>
                                <th className="px-4 pb-3 pt-1">
                                    <input
                                        value={colDatum}
                                        onChange={e => setColDatum(e.target.value)}
                                        placeholder="TT.MM.JJJJ"
                                        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-300 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500 font-normal normal-case"
                                    />
                                </th>
                                <th className="px-4 pb-3 pt-1">
                                    {/* Uhrzeit-Spalte hat keinen Filter */}
                                </th>
                                <th className="px-4 pb-3 pt-1">
                                    <input
                                        value={colSource}
                                        onChange={e => setColSource(e.target.value)}
                                        placeholder="IP / Host..."
                                        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-300 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500 font-normal normal-case"
                                    />
                                </th>
                                <th className="px-4 pb-3 pt-1">
                                    <select
                                        value={colSeverity}
                                        onChange={e => setColSeverity(e.target.value)}
                                        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500 font-normal normal-case appearance-none"
                                    >
                                        <option value="">Alle</option>
                                        <option value="CRITICAL">Critical</option>
                                        <option value="HIGH">High</option>
                                        <option value="INFO">Info</option>
                                    </select>
                                </th>
                                <th className="px-4 pb-3 pt-1">
                                    <input
                                        value={colMessage}
                                        onChange={e => setColMessage(e.target.value)}
                                        placeholder="Suche..."
                                        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-300 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500 font-normal normal-case"
                                    />
                                </th>
                                <th className="px-4 pb-3 pt-1">
                                    <input
                                        value={colDiagnosis}
                                        onChange={e => setColDiagnosis(e.target.value)}
                                        placeholder="Suche..."
                                        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-300 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500 font-normal normal-case"
                                    />
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50">
                            {displayedLogs.map((log) => (
                                <tr key={log.id} className="hover:bg-slate-800/40 transition-colors group">
                                    <td className="px-4 py-4 whitespace-nowrap text-slate-400 group-hover:text-slate-200">
                                        {format(new Date(`${log.timestamp}Z`), 'dd.MM.yyyy')}
                                    </td>
                                    <td className="px-4 py-4 whitespace-nowrap text-slate-500">
                                        {format(new Date(`${log.timestamp}Z`), 'HH:mm:ss')}
                                    </td>
                                    <td className="px-4 py-4 font-mono text-slate-300">
                                        {log.source_ip}
                                        {(log.count || 0) > 1 && (
                                            <span className="ml-2 px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 text-[10px] font-bold">
                                                x{log.count}
                                            </span>
                                        )}
                                    </td>
                                    <td className="px-4 py-4">
                                        <Badge variant={
                                            log.severity.toLowerCase() === 'critical' ? 'critical' :
                                                log.severity.toLowerCase() === 'high' ? 'high' :
                                                    log.severity.toLowerCase() === 'info' ? 'info' : 'default'
                                        }>
                                            {log.severity}
                                        </Badge>
                                    </td>
                                    <td className="px-4 py-4 font-mono text-[10px] text-slate-500 break-words min-w-[200px] max-w-sm whitespace-pre-wrap">
                                        {log.message}
                                    </td>
                                    <td className="px-4 py-4">
                                        <div className="text-slate-200 font-medium leading-relaxed">
                                            {log.diagnosis}
                                        </div>
                                        {log.recommendation && (
                                            <div className="text-[11px] text-emerald-500/80 mt-1 flex items-center gap-1">
                                                <CheckCircle2 className="w-3 h-3" />
                                                Empfehlung: {log.recommendation}
                                            </div>
                                        )}
                                    </td>
                                </tr>
                            ))}
                            {displayedLogs.length === 0 && (
                                <tr>
                                    <td colSpan={6} className="px-6 py-12 text-center">
                                        <div className="flex flex-col items-center gap-2 text-slate-600">
                                            <Search className="w-8 h-8 opacity-20" />
                                            <p>Keine Events mit diesen Filtern gefunden.</p>
                                        </div>
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </Card>
        </div>
    )
}
