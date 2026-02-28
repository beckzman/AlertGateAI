import { useState, useEffect, useCallback } from 'react'
import { Server, Activity, AlertTriangle, CheckCircle2, AlertCircle, Search, RefreshCw, Bell, Settings, SlidersHorizontal, ThumbsUp, ThumbsDown, Link2, X } from 'lucide-react'
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
    confidence?: number | null;
    status?: string;
    timestamp: string;
    count?: number; // Neu für Gruppierung
    service_name?: string;
    cluster_id?: string | null;
    correlation_id?: string | null;
    feedback?: string | null;
}

interface CorrelatedEvent {
    id: number;
    timestamp: string;
    source_ip: string;
    severity: string;
    message: string;
    diagnosis: string;
    recommendation?: string;
    confidence?: number | null;
    service_name?: string;
    rca_hypothesis?: string | null;
}

interface TriageModalProps {
    correlationId: string;
    apiUrl: string;
    onClose: () => void;
}

function TriageModal({ correlationId, apiUrl, onClose }: TriageModalProps) {
    const [events, setEvents] = useState<CorrelatedEvent[]>([])
    const [rca, setRca] = useState<{ hypothesis: string; confidence: number; recommendation?: string } | null>(null)
    const [loadingEvents, setLoadingEvents] = useState(true)
    const [loadingRca, setLoadingRca] = useState(false)

    useEffect(() => {
        fetch(`${apiUrl}/logs/correlation/${correlationId}`)
            .then(r => r.json())
            .then(data => { setEvents(data); setLoadingEvents(false) })
            .catch(() => setLoadingEvents(false))
    }, [correlationId, apiUrl])

    const triggerRca = async () => {
        setLoadingRca(true)
        try {
            const res = await fetch(`${apiUrl}/logs/correlation/${correlationId}/rca`, { method: 'POST' })
            const data = await res.json()
            setRca({ hypothesis: data.hypothesis, confidence: data.confidence, recommendation: data.recommendation })
        } catch { /* silent */ } finally {
            setLoadingRca(false)
        }
    }

    const SEV_COLOR: Record<string, string> = {
        CRITICAL: 'border-l-red-500 bg-red-500/5',
        HIGH: 'border-l-amber-500 bg-amber-500/5',
        INFO: 'border-l-blue-500 bg-blue-500/5',
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
            <div className="w-full max-w-3xl max-h-[85vh] overflow-y-auto bg-slate-900 rounded-2xl border border-slate-700/50 shadow-2xl" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="sticky top-0 bg-slate-900 px-6 py-4 border-b border-slate-700/50 flex items-center justify-between z-10">
                    <div>
                        <h2 className="text-base font-semibold text-white">Alert-Story</h2>
                        <p className="text-xs text-slate-500 font-mono mt-0.5">{correlationId}</p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-slate-800 rounded-lg transition-colors text-slate-400 hover:text-white">
                        <X className="w-4 h-4" />
                    </button>
                </div>

                <div className="p-6 space-y-6">
                    {/* RCA */}
                    {rca ? (
                        <div className="p-4 bg-violet-500/10 border border-violet-500/30 rounded-xl">
                            <p className="text-xs font-bold text-violet-400 uppercase mb-2">Root Cause Hypothese</p>
                            <p className="text-slate-200 text-sm leading-relaxed">{rca.hypothesis}</p>
                            {rca.recommendation && (
                                <p className="text-xs text-emerald-400/80 mt-2 whitespace-pre-line">{rca.recommendation}</p>
                            )}
                            <div className="mt-2 flex items-center gap-2">
                                <div className="h-1 w-24 rounded-full bg-slate-700 overflow-hidden">
                                    <div className="h-full bg-violet-500 rounded-full" style={{ width: `${Math.round((rca.confidence ?? 0) * 100)}%` }} />
                                </div>
                                <span className="text-[10px] text-violet-400 font-semibold tabular-nums">
                                    {Math.round((rca.confidence ?? 0) * 100)}%
                                </span>
                            </div>
                        </div>
                    ) : (
                        <button
                            onClick={triggerRca}
                            disabled={loadingRca || loadingEvents}
                            className="w-full py-2.5 bg-violet-600 hover:bg-violet-500 disabled:bg-slate-700 disabled:cursor-not-allowed rounded-xl text-sm font-semibold text-white transition-colors"
                        >
                            {loadingRca ? 'Analysiere...' : 'Root Cause analysieren (KI)'}
                        </button>
                    )}

                    {/* Timeline */}
                    <div>
                        <p className="text-xs font-bold text-slate-500 uppercase mb-3">
                            Event-Timeline ({events.length} Events)
                        </p>
                        {loadingEvents ? (
                            <div className="text-center text-slate-600 py-8">Lade Events...</div>
                        ) : (
                            <div className="space-y-2">
                                {events.map(event => (
                                    <div key={event.id} className={`border-l-2 rounded-r-lg p-3 pl-4 ${SEV_COLOR[event.severity] ?? 'border-l-slate-600 bg-slate-800/30'}`}>
                                        <div className="flex items-center gap-2 flex-wrap mb-1">
                                            <span className="text-[10px] font-mono text-slate-500">
                                                {new Date(`${event.timestamp}Z`).toLocaleTimeString('de-DE')}
                                            </span>
                                            <span className="font-mono text-xs text-slate-300">{event.source_ip}</span>
                                            {event.service_name && (
                                                <span className="px-1.5 py-0.5 bg-slate-700 rounded text-[10px] text-slate-400">{event.service_name}</span>
                                            )}
                                        </div>
                                        <p className="text-[11px] text-slate-500 font-mono break-words">{event.message}</p>
                                        {event.diagnosis && (
                                            <p className="text-xs text-slate-300 mt-1">{event.diagnosis}</p>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}

interface Stats {
    severity: Record<string, number>;
    timeline: { hour: string; CRITICAL: number; HIGH: number; INFO: number }[];
    top_sources?: { source: string; count: number }[];
}

interface DashboardProps {
    onNavigate: (page: Page) => void
}

export default function Dashboard({ onNavigate }: DashboardProps) {
    const [logs, setLogs] = useState<LogEntry[]>([])
    const [stats, setStats] = useState<Stats | null>(null)
    const [backendOnline, setBackendOnline] = useState(false)
    const [loading, setLoading] = useState(true)

    const apiUrl = import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`

    const fetchData = useCallback(async () => {
        try {
            const [logsRes, statsRes] = await Promise.all([
                fetch(`${apiUrl}/logs`),
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
    }, [apiUrl])

    useEffect(() => {
        fetchData()
        const interval = setInterval(fetchData, 10000) // Alle 10s aktualisieren
        return () => clearInterval(interval)
    }, [fetchData])


    const [triagedCorrelationId, setTriagedCorrelationId] = useState<string | null>(null)

    // Tabellen-Filter (client-seitig)
    const [colDatum, setColDatum] = useState('')
    const [colSource, setColSource] = useState('')
    const [colSeverity, setColSeverity] = useState('')
    const [colStatus, setColStatus] = useState('')
    const [colMessage, setColMessage] = useState('')
    const [colDiagnosis, setColDiagnosis] = useState('')
    const [colCluster, setColCluster] = useState('')

    const STATUS_CYCLE: Record<string, string> = { new: 'acknowledged', acknowledged: 'resolved', resolved: 'new' }
    const STATUS_LABEL: Record<string, string> = { new: 'NEU', acknowledged: 'ACK', resolved: 'GELÖST' }
    const STATUS_CLASS: Record<string, string> = {
        new: 'bg-slate-700/60 text-slate-300 hover:bg-slate-600',
        acknowledged: 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30',
        resolved: 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30',
    }

    const updateStatus = async (logId: number, current: string) => {
        const next = STATUS_CYCLE[current] ?? 'new'
        await fetch(`${apiUrl}/logs/${logId}/status?status=${next}`, { method: 'PATCH' })
        setLogs(prev => prev.map(l => l.id === logId ? { ...l, status: next } : l))
    }

    const submitFeedback = async (logId: number, feedback: 'valid' | 'false_positive') => {
        await fetch(`${apiUrl}/logs/${logId}/feedback`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ feedback }),
        })
        setLogs(prev => prev.map(l => l.id === logId ? { ...l, feedback } : l))
    }

    const displayedLogs = logs.filter(log => {
        const datum = format(new Date(`${log.timestamp}Z`), 'dd.MM.yyyy')
        if (colDatum && !datum.includes(colDatum)) return false
        if (colSource && !log.source_ip.toLowerCase().includes(colSource.toLowerCase())) return false
        if (colSeverity && log.severity !== colSeverity) return false
        if (colStatus && (log.status ?? 'new') !== colStatus) return false
        if (colMessage && !log.message.toLowerCase().includes(colMessage.toLowerCase())) return false
        if (colDiagnosis && !(log.diagnosis ?? '').toLowerCase().includes(colDiagnosis.toLowerCase())) return false
        if (colCluster && log.cluster_id !== colCluster) return false
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
                        onClick={() => onNavigate('settings')}
                        className="flex items-center gap-2 px-3 py-2 bg-slate-900/50 hover:bg-slate-800 rounded-xl border border-slate-800 text-sm text-slate-400 hover:text-white transition-colors"
                    >
                        <SlidersHorizontal className="w-4 h-4" />
                        <span>Einstellungen</span>
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
                                {(() => {
                                    const total = (stats?.severity?.CRITICAL || 0) + (stats?.severity?.HIGH || 0) + (stats?.severity?.INFO || 0)
                                    const pct = total > 0 ? Math.round((stats?.severity?.CRITICAL || 0) / total * 100) : 0
                                    return <p className="text-[11px] text-red-400/60 mt-1">{pct}% der Events (24h)</p>
                                })()}
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

                <Card className="lg:col-span-1">
                    <CardHeader>
                        <CardTitle className="text-sm font-medium text-slate-400 flex items-center gap-2">
                            <Server className="w-4 h-4" /> Top Sources (24h)
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="h-72 mt-4">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={stats?.top_sources || []} layout="vertical" margin={{ top: 0, right: 10, bottom: 0, left: 10 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                                <XAxis type="number" stroke="#64748b" fontSize={10} allowDecimals={false} />
                                <YAxis dataKey="source" type="category" stroke="#64748b" fontSize={10} width={80} tickFormatter={(val) => val.length > 12 ? val.substring(0, 12) + '...' : val} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }}
                                    labelStyle={{ color: '#94a3b8', marginBottom: 4 }}
                                    cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                                />
                                <Bar dataKey="count" name="Alerts" fill="#8b5cf6" radius={[0, 4, 4, 0]} barSize={20} />
                            </BarChart>
                        </ResponsiveContainer>
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
                                <th className="px-4 pt-4 pb-1 font-semibold">Status</th>
                                <th className="px-4 pt-4 pb-1 font-semibold">Log Message</th>
                                <th className="px-4 pt-4 pb-1 font-semibold text-blue-400">KI-Diagnose</th>
                                <th className="px-4 pt-4 pb-1 font-semibold text-violet-400">Cluster</th>
                                <th className="px-4 pt-4 pb-1 font-semibold">Feedback</th>
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
                                    <select
                                        value={colStatus}
                                        onChange={e => setColStatus(e.target.value)}
                                        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500 font-normal normal-case appearance-none"
                                    >
                                        <option value="">Alle</option>
                                        <option value="new">Neu</option>
                                        <option value="acknowledged">ACK</option>
                                        <option value="resolved">Gelöst</option>
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
                                <th className="px-4 pb-3 pt-1">
                                    <input
                                        value={colCluster}
                                        onChange={e => setColCluster(e.target.value)}
                                        placeholder="Cluster-ID..."
                                        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-300 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-violet-500 font-normal normal-case font-mono"
                                    />
                                </th>
                                <th className="px-4 pb-3 pt-1" />
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
                                        <div className="flex items-center gap-1.5">
                                            <span>{log.source_ip}</span>
                                            {(log.count || 0) > 1 && (
                                                <span className="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 text-[10px] font-bold">
                                                    x{log.count}
                                                </span>
                                            )}
                                            {log.correlation_id && (
                                                <button
                                                    onClick={() => setTriagedCorrelationId(log.correlation_id!)}
                                                    className="p-0.5 hover:bg-slate-700 rounded text-slate-600 hover:text-cyan-400 transition-colors"
                                                    title="Alert-Story öffnen"
                                                >
                                                    <Link2 className="w-3 h-3" />
                                                </button>
                                            )}
                                        </div>
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
                                    <td className="px-4 py-4">
                                        <button
                                            onClick={() => updateStatus(log.id, log.status ?? 'new')}
                                            className={`px-2 py-0.5 rounded text-[10px] font-bold transition-colors ${STATUS_CLASS[log.status ?? 'new'] ?? STATUS_CLASS.new}`}
                                            title="Klicken zum Wechseln"
                                        >
                                            {STATUS_LABEL[log.status ?? 'new'] ?? 'NEU'}
                                        </button>
                                    </td>
                                    <td className="px-4 py-4 font-mono text-[10px] text-slate-500 break-words min-w-[200px] max-w-sm whitespace-pre-wrap">
                                        {log.message}
                                    </td>
                                    <td className="px-4 py-4">
                                        <div className="text-slate-200 font-medium leading-relaxed">
                                            {log.diagnosis}
                                        </div>
                                        {log.confidence != null && (
                                            <div className="mt-1.5 flex items-center gap-2">
                                                <div className="h-1 w-20 rounded-full bg-slate-700 overflow-hidden">
                                                    <div
                                                        className={`h-full rounded-full transition-all ${log.confidence >= 0.8 ? 'bg-emerald-500' :
                                                            log.confidence >= 0.5 ? 'bg-amber-500' : 'bg-red-500'
                                                            }`}
                                                        style={{ width: `${Math.round(log.confidence * 100)}%` }}
                                                    />
                                                </div>
                                                <span className={`text-[10px] font-semibold tabular-nums ${log.confidence >= 0.8 ? 'text-emerald-500' :
                                                    log.confidence >= 0.5 ? 'text-amber-500' : 'text-red-400'
                                                    }`}>
                                                    {Math.round(log.confidence * 100)}%
                                                </span>
                                            </div>
                                        )}
                                        {log.recommendation && (
                                            <div className="text-[11px] text-emerald-500/80 mt-1 flex items-center gap-1">
                                                <CheckCircle2 className="w-3 h-3" />
                                                Empfehlung: {log.recommendation}
                                            </div>
                                        )}
                                    </td>
                                    {/* Cluster */}
                                    <td className="px-4 py-4">
                                        {log.cluster_id && (
                                            <button
                                                onClick={() => setColCluster(colCluster === log.cluster_id ? '' : log.cluster_id!)}
                                                className={`px-1.5 py-0.5 rounded text-[10px] font-mono transition-colors ${colCluster === log.cluster_id ? 'bg-violet-500/30 text-violet-300' : 'bg-slate-700/60 text-slate-400 hover:bg-violet-500/20 hover:text-violet-400'}`}
                                                title="Nach diesem Cluster filtern"
                                            >
                                                {log.cluster_id.slice(0, 8)}
                                            </button>
                                        )}
                                    </td>
                                    {/* Feedback */}
                                    <td className="px-4 py-4">
                                        <div className="flex items-center gap-1">
                                            <button
                                                onClick={() => submitFeedback(log.id, 'valid')}
                                                className={`p-1 rounded transition-colors ${log.feedback === 'valid' ? 'text-emerald-400 bg-emerald-500/10' : 'text-slate-600 hover:text-emerald-400'}`}
                                                title="Korrekte Diagnose"
                                            >
                                                <ThumbsUp className="w-3.5 h-3.5" />
                                            </button>
                                            <button
                                                onClick={() => submitFeedback(log.id, 'false_positive')}
                                                className={`p-1 rounded transition-colors ${log.feedback === 'false_positive' ? 'text-red-400 bg-red-500/10' : 'text-slate-600 hover:text-red-400'}`}
                                                title="False Positive"
                                            >
                                                <ThumbsDown className="w-3.5 h-3.5" />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            {displayedLogs.length === 0 && (
                                <tr>
                                    <td colSpan={9} className="px-6 py-12 text-center">
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

            {/* Alert-Story Modal */}
            {triagedCorrelationId && (
                <TriageModal
                    correlationId={triagedCorrelationId}
                    apiUrl={apiUrl}
                    onClose={() => setTriagedCorrelationId(null)}
                />
            )}
        </div>
    )
}
