import { useState, useEffect, useCallback } from 'react'
import {
    Activity, Bell, Send, Mail, ChevronLeft,
    CheckCircle2, XCircle, Clock, Loader2
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/Card'
import { Badge } from './components/ui/Badge'
import { format } from 'date-fns'

type Page = 'dashboard' | 'notifications'

interface NotificationHistoryEntry {
    id: number
    timestamp: string
    recipient: string
    subject: string
    message: string
    severity: string
    channel: string
    status: string
    error?: string
}

interface NotificationsProps {
    onNavigate: (page: Page) => void
}

export default function Notifications({ onNavigate }: NotificationsProps) {
    const apiUrl = import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`

    // Form state
    const [recipient, setRecipient] = useState('')
    const [subject, setSubject] = useState('')
    const [message, setMessage] = useState('')
    const [severity, setSeverity] = useState('HIGH')
    const [sending, setSending] = useState(false)
    const [sendResult, setSendResult] = useState<{ type: 'success' | 'error' | 'mock'; message: string } | null>(null)

    // History state
    const [history, setHistory] = useState<NotificationHistoryEntry[]>([])
    const [loadingHistory, setLoadingHistory] = useState(true)

    const fetchHistory = useCallback(async () => {
        try {
            const res = await fetch(`${apiUrl}/notify/history`)
            if (res.ok) {
                const data = await res.json()
                setHistory(data)
            }
        } catch (err) {
            console.error('Fehler beim Laden des Verlaufs:', err)
        } finally {
            setLoadingHistory(false)
        }
    }, [apiUrl])

    useEffect(() => {
        fetchHistory()
    }, [fetchHistory])

    const handleSend = async (e: React.FormEvent) => {
        e.preventDefault()
        setSending(true)
        setSendResult(null)

        try {
            const res = await fetch(`${apiUrl}/notify/send`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ recipient, subject, message, severity }),
            })

            const data = await res.json()

            if (res.ok) {
                setSendResult({
                    type: data.status === 'mock' ? 'mock' : 'success',
                    message: data.message,
                })
                await fetchHistory()
                setRecipient('')
                setSubject('')
                setMessage('')
                setSeverity('HIGH')
            } else {
                setSendResult({ type: 'error', message: data.detail || 'Fehler beim Versand' })
            }
        } catch {
            setSendResult({ type: 'error', message: 'Verbindungsfehler zum Backend' })
        } finally {
            setSending(false)
        }
    }

    const renderStatus = (status: string) => {
        if (status === 'sent') return (
            <span className="flex items-center gap-1 text-emerald-400 text-xs font-medium">
                <CheckCircle2 className="w-3 h-3" /> Versendet
            </span>
        )
        if (status === 'mock') return (
            <span className="flex items-center gap-1 text-blue-400 text-xs font-medium">
                <CheckCircle2 className="w-3 h-3" /> Mock
            </span>
        )
        return (
            <span className="flex items-center gap-1 text-red-400 text-xs font-medium">
                <XCircle className="w-3 h-3" /> Fehler
            </span>
        )
    }

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
                        <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">
                            Notification Management
                        </p>
                    </div>
                </div>

                <button
                    onClick={() => onNavigate('dashboard')}
                    className="flex items-center gap-2 px-4 py-2 bg-slate-900/50 hover:bg-slate-800 rounded-xl border border-slate-800 text-sm text-slate-400 hover:text-white transition-colors"
                >
                    <ChevronLeft className="w-4 h-4" />
                    Zurück zum Dashboard
                </button>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Notification Form */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-white">
                            <Mail className="w-5 h-5 text-blue-400" />
                            Benachrichtigung senden
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSend} className="space-y-4 pt-2">
                            <div className="space-y-1.5">
                                <label className="text-xs font-bold text-slate-500 uppercase">
                                    Empfänger (E-Mail)
                                </label>
                                <input
                                    type="email"
                                    required
                                    value={recipient}
                                    onChange={(e) => setRecipient(e.target.value)}
                                    placeholder="admin@example.com"
                                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all placeholder:text-slate-600"
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-xs font-bold text-slate-500 uppercase">
                                    Schweregrad
                                </label>
                                <select
                                    value={severity}
                                    onChange={(e) => setSeverity(e.target.value)}
                                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white focus:ring-2 focus:ring-blue-500 focus:outline-none appearance-none"
                                >
                                    <option value="INFO">Info</option>
                                    <option value="HIGH">High</option>
                                    <option value="CRITICAL">Critical</option>
                                </select>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-xs font-bold text-slate-500 uppercase">
                                    Betreff
                                </label>
                                <input
                                    type="text"
                                    required
                                    value={subject}
                                    onChange={(e) => setSubject(e.target.value)}
                                    placeholder="z.B. Server DB01 nicht erreichbar"
                                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all placeholder:text-slate-600"
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-xs font-bold text-slate-500 uppercase">
                                    Nachricht
                                </label>
                                <textarea
                                    required
                                    value={message}
                                    onChange={(e) => setMessage(e.target.value)}
                                    placeholder="Beschreibung des Vorfalls..."
                                    rows={5}
                                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all resize-none placeholder:text-slate-600"
                                />
                            </div>

                            {sendResult && (
                                <div
                                    className={`flex items-start gap-3 p-3 rounded-lg border text-sm ${
                                        sendResult.type === 'success'
                                            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                                            : sendResult.type === 'mock'
                                            ? 'bg-blue-500/10 border-blue-500/30 text-blue-400'
                                            : 'bg-red-500/10 border-red-500/30 text-red-400'
                                    }`}
                                >
                                    {sendResult.type === 'error' ? (
                                        <XCircle className="w-4 h-4 mt-0.5 shrink-0" />
                                    ) : (
                                        <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
                                    )}
                                    {sendResult.message}
                                </div>
                            )}

                            <button
                                type="submit"
                                disabled={sending}
                                className="w-full flex items-center justify-center gap-2 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:cursor-not-allowed rounded-lg text-sm font-semibold text-white transition-colors"
                            >
                                {sending ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" /> Wird gesendet...
                                    </>
                                ) : (
                                    <>
                                        <Send className="w-4 h-4" /> Benachrichtigung senden
                                    </>
                                )}
                            </button>
                        </form>
                    </CardContent>
                </Card>

                {/* Konfiguration Übersicht */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-white">
                            <Bell className="w-5 h-5 text-blue-400" />
                            Konfiguration
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-4 space-y-4">
                        <div className="space-y-3">
                            <div className="p-4 bg-slate-900/60 rounded-lg border border-slate-800 space-y-1">
                                <div className="text-xs font-bold text-slate-500 uppercase">
                                    E-Mail (SMTP)
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-emerald-500" />
                                    <span className="text-sm text-slate-300">Konfiguriert via .env</span>
                                </div>
                                <p className="text-xs text-slate-600">
                                    SMTP_SERVER · SMTP_USER · ON_CALL_EMAIL
                                </p>
                            </div>

                            <div className="p-4 bg-slate-900/60 rounded-lg border border-slate-800 space-y-1 opacity-50">
                                <div className="text-xs font-bold text-slate-500 uppercase">
                                    MS Teams
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-slate-600" />
                                    <span className="text-sm text-slate-500">Noch nicht verfügbar</span>
                                </div>
                                <p className="text-xs text-slate-600">Geplant in v0.2.0</p>
                            </div>

                            <div className="p-4 bg-slate-900/60 rounded-lg border border-slate-800 space-y-1 opacity-50">
                                <div className="text-xs font-bold text-slate-500 uppercase">
                                    SMS (Twilio)
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-slate-600" />
                                    <span className="text-sm text-slate-500">Automatisch bei CRITICAL</span>
                                </div>
                                <p className="text-xs text-slate-600">
                                    TWILIO_ACCOUNT_SID · TWILIO_AUTH_TOKEN
                                </p>
                            </div>
                        </div>

                        <div className="p-3 bg-blue-500/5 border border-blue-500/20 rounded-lg text-xs text-slate-400">
                            <span className="text-blue-400 font-semibold">Hinweis: </span>
                            Ohne SMTP-Konfiguration werden Benachrichtigungen im Mock-Modus simuliert und im Verlauf protokolliert.
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Versandverlauf */}
            <Card className="overflow-hidden">
                <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle className="flex items-center gap-2 text-white">
                        <Clock className="w-5 h-5 text-blue-400" />
                        Versandverlauf
                    </CardTitle>
                    <Badge variant="default">{history.length} Einträge</Badge>
                </CardHeader>

                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="text-xs uppercase bg-slate-900/80 text-slate-500 border-b border-slate-700/50">
                            <tr>
                                <th className="px-6 py-4 font-semibold">Zeitpunkt</th>
                                <th className="px-6 py-4 font-semibold">Empfänger</th>
                                <th className="px-6 py-4 font-semibold">Betreff</th>
                                <th className="px-6 py-4 font-semibold">Severity</th>
                                <th className="px-6 py-4 font-semibold">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50">
                            {history.map((entry) => (
                                <tr
                                    key={entry.id}
                                    className="hover:bg-slate-800/40 transition-colors group"
                                >
                                    <td className="px-6 py-4 whitespace-nowrap text-slate-400 group-hover:text-slate-200">
                                        {format(new Date(`${entry.timestamp}Z`), 'HH:mm:ss')}
                                        <span className="block text-[10px] text-slate-600">
                                            {format(new Date(`${entry.timestamp}Z`), 'dd.MM.yyyy')}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 font-mono text-slate-300 text-xs">
                                        {entry.recipient}
                                    </td>
                                    <td
                                        className="px-6 py-4 text-slate-300 max-w-xs truncate"
                                        title={entry.subject}
                                    >
                                        {entry.subject}
                                    </td>
                                    <td className="px-6 py-4">
                                        <Badge
                                            variant={
                                                entry.severity.toLowerCase() === 'critical'
                                                    ? 'critical'
                                                    : entry.severity.toLowerCase() === 'high'
                                                    ? 'high'
                                                    : entry.severity.toLowerCase() === 'info'
                                                    ? 'info'
                                                    : 'default'
                                            }
                                        >
                                            {entry.severity}
                                        </Badge>
                                    </td>
                                    <td className="px-6 py-4">{renderStatus(entry.status)}</td>
                                </tr>
                            ))}
                            {!loadingHistory && history.length === 0 && (
                                <tr>
                                    <td colSpan={5} className="px-6 py-12 text-center">
                                        <div className="flex flex-col items-center gap-2 text-slate-600">
                                            <Bell className="w-8 h-8 opacity-20" />
                                            <p>Noch keine Benachrichtigungen versendet.</p>
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
