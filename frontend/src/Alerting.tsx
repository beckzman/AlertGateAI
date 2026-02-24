import { useState, useEffect, useCallback } from 'react'
import {
    ChevronLeft, Save, Mail, Phone, Webhook,
    CheckCircle2, AlertCircle, AlertTriangle, Info, Loader2
} from 'lucide-react'
import type { Page } from './App'
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/Card'
import { Badge } from './components/ui/Badge'

interface EscalationRule {
    severity: string
    email_enabled: boolean
    email_recipients: string
    sms_enabled: boolean
    sms_recipients: string
    webhook_enabled: boolean
    webhook_url: string
}

interface AlertingProps {
    onNavigate: (page: Page) => void
}

const SEVERITIES = ['INFO', 'HIGH', 'CRITICAL'] as const

const SEVERITY_META: Record<string, { label: string; icon: React.ReactNode; border: string; badge: 'info' | 'high' | 'critical' }> = {
    INFO:     { label: 'Info',     icon: <Info className="w-4 h-4 text-blue-400" />,   border: 'border-l-blue-500/50',  badge: 'info' },
    HIGH:     { label: 'High',     icon: <AlertTriangle className="w-4 h-4 text-amber-400" />, border: 'border-l-amber-500/50', badge: 'high' },
    CRITICAL: { label: 'Critical', icon: <AlertCircle className="w-4 h-4 text-red-400" />,   border: 'border-l-red-500/50',   badge: 'critical' },
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
    return (
        <button
            type="button"
            onClick={() => onChange(!checked)}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${checked ? 'bg-blue-500' : 'bg-slate-700'}`}
        >
            <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${checked ? 'translate-x-4' : 'translate-x-1'}`} />
        </button>
    )
}

export default function Alerting({ onNavigate }: AlertingProps) {
    const apiUrl = import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`
    const [rules, setRules] = useState<Record<string, EscalationRule>>({})
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [savedSev, setSavedSev] = useState<string | null>(null)

    const fetchRules = useCallback(async () => {
        try {
            const res = await fetch(`${apiUrl}/escalation`)
            if (res.ok) {
                const data: EscalationRule[] = await res.json()
                const map: Record<string, EscalationRule> = {}
                data.forEach(r => { map[r.severity] = { ...r } })
                setRules(map)
            }
        } catch (e) {
            console.error('Fehler beim Laden der Eskalationsregeln:', e)
        } finally {
            setLoading(false)
        }
    }, [apiUrl])

    useEffect(() => { fetchRules() }, [fetchRules])

    const updateRule = (severity: string, field: keyof EscalationRule, value: boolean | string) => {
        setRules(prev => ({
            ...prev,
            [severity]: { ...prev[severity], [field]: value }
        }))
    }

    const saveRule = async (severity: string) => {
        setSaving(true)
        try {
            const rule = rules[severity]
            const res = await fetch(`${apiUrl}/escalation/${severity}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(rule),
            })
            if (res.ok) {
                setSavedSev(severity)
                setTimeout(() => setSavedSev(null), 2000)
            }
        } catch (e) {
            console.error('Fehler beim Speichern:', e)
        } finally {
            setSaving(false)
        }
    }

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8 w-full max-w-5xl mx-auto space-y-8">
            {/* Header */}
            <header className="flex items-center gap-4 pb-6 border-b border-slate-800/60">
                <button
                    onClick={() => onNavigate('dashboard')}
                    className="p-2 hover:bg-slate-800 rounded-lg transition-colors border border-slate-800"
                >
                    <ChevronLeft className="w-5 h-5 text-slate-400" />
                </button>
                <div>
                    <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
                        Alarmierung & Eskalation
                    </h1>
                    <p className="text-xs text-slate-500 font-medium uppercase tracking-wider mt-0.5">
                        Konfiguriere welche Severity-Stufen wie alarmiert werden
                    </p>
                </div>
            </header>

            {loading ? (
                <div className="flex items-center justify-center py-24 text-slate-500">
                    <Loader2 className="w-6 h-6 animate-spin mr-2" /> Lade Konfiguration...
                </div>
            ) : (
                <div className="space-y-4">
                    {SEVERITIES.map(sev => {
                        const rule = rules[sev]
                        const meta = SEVERITY_META[sev]
                        if (!rule) return null
                        return (
                            <Card key={sev} className={`border-l-4 ${meta.border}`}>
                                <CardHeader className="flex flex-row items-center justify-between pb-2">
                                    <CardTitle className="flex items-center gap-2 text-base">
                                        {meta.icon}
                                        <Badge variant={meta.badge}>{meta.label}</Badge>
                                        <span className="text-slate-400 text-sm font-normal ml-1">Eskalationsstufe</span>
                                    </CardTitle>
                                    <button
                                        onClick={() => saveRule(sev)}
                                        disabled={saving}
                                        className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg text-xs font-semibold text-white transition-colors"
                                    >
                                        {savedSev === sev
                                            ? <><CheckCircle2 className="w-3.5 h-3.5" /> Gespeichert</>
                                            : <><Save className="w-3.5 h-3.5" /> Speichern</>
                                        }
                                    </button>
                                </CardHeader>
                                <CardContent className="space-y-4 pt-2">
                                    {/* E-Mail */}
                                    <div className="flex items-start gap-4 p-3 rounded-lg bg-slate-900/50 border border-slate-800/50">
                                        <div className="flex items-center gap-2 w-32 shrink-0 pt-0.5">
                                            <Mail className="w-4 h-4 text-slate-400" />
                                            <span className="text-sm font-medium text-slate-300">E-Mail</span>
                                        </div>
                                        <div className="flex items-start gap-3 flex-1">
                                            <Toggle
                                                checked={rule.email_enabled}
                                                onChange={v => updateRule(sev, 'email_enabled', v)}
                                            />
                                            {rule.email_enabled ? (
                                                <div className="flex-1">
                                                    <input
                                                        type="text"
                                                        value={rule.email_recipients}
                                                        onChange={e => updateRule(sev, 'email_recipients', e.target.value)}
                                                        placeholder="oncall@firma.de, team@firma.de"
                                                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none text-slate-200 placeholder:text-slate-600"
                                                    />
                                                    <p className="text-[11px] text-slate-600 mt-1">Mehrere Adressen kommagetrennt</p>
                                                </div>
                                            ) : (
                                                <span className="text-sm text-slate-600 pt-0.5">Deaktiviert</span>
                                            )}
                                        </div>
                                    </div>

                                    {/* SMS */}
                                    <div className="flex items-start gap-4 p-3 rounded-lg bg-slate-900/50 border border-slate-800/50">
                                        <div className="flex items-center gap-2 w-32 shrink-0 pt-0.5">
                                            <Phone className="w-4 h-4 text-slate-400" />
                                            <span className="text-sm font-medium text-slate-300">SMS</span>
                                        </div>
                                        <div className="flex items-start gap-3 flex-1">
                                            <Toggle
                                                checked={rule.sms_enabled}
                                                onChange={v => updateRule(sev, 'sms_enabled', v)}
                                            />
                                            {rule.sms_enabled ? (
                                                <div className="flex-1">
                                                    <input
                                                        type="text"
                                                        value={rule.sms_recipients}
                                                        onChange={e => updateRule(sev, 'sms_recipients', e.target.value)}
                                                        placeholder="+49123456789, +49987654321"
                                                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none text-slate-200 placeholder:text-slate-600"
                                                    />
                                                    <p className="text-[11px] text-slate-600 mt-1">Mehrere Nummern kommagetrennt (via Twilio)</p>
                                                </div>
                                            ) : (
                                                <span className="text-sm text-slate-600 pt-0.5">Deaktiviert</span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Webhook */}
                                    <div className="flex items-start gap-4 p-3 rounded-lg bg-slate-900/50 border border-slate-800/50">
                                        <div className="flex items-center gap-2 w-32 shrink-0 pt-0.5">
                                            <Webhook className="w-4 h-4 text-slate-400" />
                                            <span className="text-sm font-medium text-slate-300">Webhook</span>
                                        </div>
                                        <div className="flex items-start gap-3 flex-1">
                                            <Toggle
                                                checked={rule.webhook_enabled}
                                                onChange={v => updateRule(sev, 'webhook_enabled', v)}
                                            />
                                            {rule.webhook_enabled ? (
                                                <div className="flex-1">
                                                    <input
                                                        type="url"
                                                        value={rule.webhook_url}
                                                        onChange={e => updateRule(sev, 'webhook_url', e.target.value)}
                                                        placeholder="https://hooks.slack.com/services/..."
                                                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none text-slate-200 placeholder:text-slate-600"
                                                    />
                                                    <p className="text-[11px] text-slate-600 mt-1">Teams / Slack / Custom Webhook URL</p>
                                                </div>
                                            ) : (
                                                <span className="text-sm text-slate-600 pt-0.5">Deaktiviert</span>
                                            )}
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        )
                    })}

                    {/* Hinweis */}
                    <p className="text-[11px] text-slate-600 text-center pt-2">
                        Änderungen werden pro Stufe mit „Speichern" bestätigt. SMTP- und Twilio-Credentials werden in der <code className="font-mono">.env</code> konfiguriert.
                    </p>
                </div>
            )}
        </div>
    )
}
