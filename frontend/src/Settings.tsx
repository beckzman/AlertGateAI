import { useState, useEffect, useCallback } from 'react'
import {
    Activity, ChevronLeft, Settings as SettingsIcon,
    Eye, EyeOff, Save, Loader2, CheckCircle2,
    XCircle, Zap, RefreshCw,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/Card'

type Page = 'dashboard' | 'notifications' | 'alerting' | 'settings'

interface FieldMeta {
    key: string
    label: string
    type: 'text' | 'number' | 'password' | 'select'
    options?: string[]
    is_secret: boolean
    value: string
}

interface SettingsGroup {
    group: string
    label: string
    restart_required: boolean
    fields: FieldMeta[]
}

interface SettingsProps {
    onNavigate: (page: Page) => void
}

export default function Settings({ onNavigate }: SettingsProps) {
    const apiUrl = import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`

    const [groups, setGroups] = useState<SettingsGroup[]>([])
    const [loading, setLoading] = useState(true)
    // Local edits: key → new value (empty string = unchanged for secrets)
    const [edits, setEdits] = useState<Record<string, string>>({})
    // Password visibility per field
    const [visible, setVisible] = useState<Record<string, boolean>>({})
    const [saving, setSaving] = useState(false)
    const [result, setResult] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

    const fetchSettings = useCallback(async () => {
        setLoading(true)
        try {
            const res = await fetch(`${apiUrl}/settings`)
            if (res.ok) {
                const data: SettingsGroup[] = await res.json()
                setGroups(data)
                // Initialise edits: non-secrets get current value, secrets start empty
                const initial: Record<string, string> = {}
                for (const g of data) {
                    for (const f of g.fields) {
                        initial[f.key] = f.is_secret ? '' : f.value
                    }
                }
                setEdits(initial)
            }
        } catch {
            setResult({ type: 'error', message: 'Verbindungsfehler zum Backend' })
        } finally {
            setLoading(false)
        }
    }, [apiUrl])

    useEffect(() => { fetchSettings() }, [fetchSettings])

    const handleChange = (key: string, value: string) => {
        setEdits(prev => ({ ...prev, [key]: value }))
        setResult(null)
    }

    const toggleVisible = (key: string) =>
        setVisible(prev => ({ ...prev, [key]: !prev[key] }))

    const handleSave = async () => {
        setSaving(true)
        setResult(null)
        try {
            const res = await fetch(`${apiUrl}/settings`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(edits),
            })
            const data = await res.json()
            if (res.ok) {
                setResult({
                    type: 'success',
                    message: `${data.updated.length} Parameter gespeichert und live aktiviert.`,
                })
                // Re-fetch to reflect server state (masks new secrets, etc.)
                await fetchSettings()
            } else {
                setResult({ type: 'error', message: data.detail || 'Fehler beim Speichern' })
            }
        } catch {
            setResult({ type: 'error', message: 'Verbindungsfehler zum Backend' })
        } finally {
            setSaving(false)
        }
    }

    const renderField = (f: FieldMeta) => {
        const val = edits[f.key] ?? ''
        const base = 'w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all placeholder:text-slate-600'

        if (f.type === 'select' && f.options) {
            return (
                <select
                    value={val}
                    onChange={e => handleChange(f.key, e.target.value)}
                    className={base + ' appearance-none'}
                >
                    {f.options.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
            )
        }

        if (f.type === 'password') {
            const isSet = f.value === '***'
            const show = visible[f.key]
            return (
                <div className="relative">
                    <input
                        type={show ? 'text' : 'password'}
                        value={val}
                        onChange={e => handleChange(f.key, e.target.value)}
                        placeholder={isSet ? '(unverändert lassen)' : 'Nicht konfiguriert'}
                        className={base + ' pr-10'}
                        autoComplete="new-password"
                    />
                    <button
                        type="button"
                        onClick={() => toggleVisible(f.key)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                        tabIndex={-1}
                    >
                        {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                </div>
            )
        }

        return (
            <input
                type={f.type === 'number' ? 'number' : 'text'}
                value={val}
                onChange={e => handleChange(f.key, e.target.value)}
                className={base}
            />
        )
    }

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8 w-full max-w-5xl mx-auto space-y-8">
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
                            Systemkonfiguration
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <button
                        onClick={fetchSettings}
                        className="flex items-center gap-2 px-3 py-2 bg-slate-900/50 hover:bg-slate-800 rounded-xl border border-slate-800 text-sm text-slate-400 hover:text-white transition-colors"
                        title="Neu laden"
                    >
                        <RefreshCw className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => onNavigate('dashboard')}
                        className="flex items-center gap-2 px-4 py-2 bg-slate-900/50 hover:bg-slate-800 rounded-xl border border-slate-800 text-sm text-slate-400 hover:text-white transition-colors"
                    >
                        <ChevronLeft className="w-4 h-4" />
                        Zurück zum Dashboard
                    </button>
                </div>
            </header>

            {/* Hinweis-Banner */}
            <div className="p-3 bg-blue-500/5 border border-blue-500/20 rounded-xl text-xs text-slate-400 flex items-start gap-2">
                <SettingsIcon className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                <span>
                    Passwörter und Tokens werden <span className="text-white font-medium">sicher gespeichert</span> und
                    niemals im Klartext zurückgegeben. Leere Passwortfelder lassen den bestehenden Wert unverändert.
                    Alle Änderungen werden sofort live aktiviert — kein Neustart erforderlich.
                </span>
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-24 text-slate-500">
                    <Loader2 className="w-6 h-6 animate-spin mr-3" /> Lade Konfiguration…
                </div>
            ) : (
                <div className="space-y-6">
                    {groups.map(group => (
                        <Card key={group.group}>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-3 text-white">
                                    {group.label}
                                    <span className="text-xs font-normal px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center gap-1">
                                        <Zap className="w-3 h-3" />
                                        Live-Reload
                                    </span>
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                                    {group.fields.map(f => (
                                        <div key={f.key} className="space-y-1.5">
                                            <div className="flex items-center gap-2">
                                                <label className="text-xs font-bold text-slate-500 uppercase">
                                                    {f.label}
                                                </label>
                                                {f.is_secret && (
                                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-500 border border-slate-700">
                                                        secret
                                                    </span>
                                                )}
                                                {f.is_secret && f.value === '***' && (
                                                    <span className="text-[10px] text-emerald-500 flex items-center gap-0.5">
                                                        <CheckCircle2 className="w-3 h-3" /> gesetzt
                                                    </span>
                                                )}
                                            </div>
                                            {renderField(f)}
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

            {/* Feedback */}
            {result && (
                <div className={`flex items-start gap-3 p-4 rounded-xl border text-sm ${
                    result.type === 'success'
                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                        : 'bg-red-500/10 border-red-500/30 text-red-400'
                }`}>
                    {result.type === 'success'
                        ? <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
                        : <XCircle className="w-4 h-4 mt-0.5 shrink-0" />}
                    <p>{result.message}</p>
                </div>
            )}

            {/* Save Button */}
            {!loading && (
                <div className="flex justify-end pb-4">
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:cursor-not-allowed rounded-xl text-sm font-semibold text-white transition-colors"
                    >
                        {saving
                            ? <><Loader2 className="w-4 h-4 animate-spin" /> Wird gespeichert…</>
                            : <><Save className="w-4 h-4" /> Konfiguration speichern</>}
                    </button>
                </div>
            )}
        </div>
    )
}
