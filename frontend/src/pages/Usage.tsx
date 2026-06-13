import { useEffect, useState } from 'react'
import { Coins, Cpu, Hash, RefreshCw } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Skeleton } from '@/components/ui/skeleton'
import { getUsage, type UsageSummary } from '@/lib/api'

/** Format a USD string: 2 dp for ≥ $1, otherwise up to 4 sig. for small amounts. */
function usd(value: string | number, maxDp = 6): string {
  const n = typeof value === 'number' ? value : parseFloat(value)
  if (isNaN(n)) return '$0.00'
  const dp = n === 0 ? 2 : n >= 1 ? 2 : 4
  return `$${n.toFixed(Math.min(dp, maxDp))}`
}

function num(n: number): string {
  return new Intl.NumberFormat('en-US').format(n)
}

function timeAgo(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

const PURPOSE_LABEL: Record<string, string> = {
  extract_invoice: 'Read invoice',
  converse: 'Conversation',
  parse_command: 'Parse command',
  explain_rule: 'Explain rule',
}

function StatCard({
  icon,
  label,
  value,
  hint,
}: {
  icon: React.ReactNode
  label: string
  value: string
  hint?: string
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-center gap-2 text-muted-foreground mb-1.5">
        {icon}
        <span className="text-xs font-medium">{label}</span>
      </div>
      <div className="text-2xl font-semibold tabular-nums text-foreground">{value}</div>
      {hint && <div className="text-[11px] text-muted-foreground mt-0.5">{hint}</div>}
    </div>
  )
}

export function Usage() {
  const [data, setData] = useState<UsageSummary | null>(null)
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    getUsage()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="flex flex-col h-full overflow-y-auto scrollbar-thin">
      <PageHeader
        title="AI Usage"
        subtitle="Every model call this team has made — what it was for, who ran it, and what it cost"
        actions={
          <button
            onClick={load}
            className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </button>
        }
      />

      <div className="flex-1 p-6 space-y-6 max-w-5xl">
        {loading && !data ? (
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-24 rounded-lg" />
            ))}
          </div>
        ) : data ? (
          <>
            {/* Headline: total team spend */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
              <div className="rounded-lg border border-primary/30 bg-primary/5 p-4 sm:col-span-1">
                <div className="flex items-center gap-2 text-primary mb-1.5">
                  <Coins className="h-4 w-4" />
                  <span className="text-xs font-medium">AI spend · this team</span>
                </div>
                <div className="text-3xl font-bold tabular-nums text-foreground">
                  {usd(data.total_cost_usd)}
                </div>
                <div className="text-[11px] text-muted-foreground mt-0.5">
                  {data.currency} · all time
                </div>
              </div>
              <StatCard
                icon={<Hash className="h-4 w-4" />}
                label="Calls"
                value={num(data.total_calls)}
              />
              <StatCard
                icon={<Cpu className="h-4 w-4" />}
                label="Input tokens"
                value={num(data.total_input_tokens)}
              />
              <StatCard
                icon={<Cpu className="h-4 w-4" />}
                label="Output tokens"
                value={num(data.total_output_tokens)}
              />
            </div>

            {/* Breakdowns */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Breakdown
                title="By purpose"
                rows={data.by_purpose.map((p) => ({
                  label: PURPOSE_LABEL[p.purpose] ?? p.purpose,
                  sub: `${p.calls} call${p.calls !== 1 ? 's' : ''}`,
                  cost: p.cost_usd,
                }))}
              />
              <Breakdown
                title="By model"
                rows={data.by_model.map((m) => ({
                  label: m.model,
                  sub: `${m.calls} call${m.calls !== 1 ? 's' : ''}`,
                  cost: m.cost_usd,
                }))}
              />
              <Breakdown
                title="By person"
                rows={data.by_user.map((u) => ({
                  label: u.user,
                  sub: `${u.calls} call${u.calls !== 1 ? 's' : ''}`,
                  cost: u.cost_usd,
                }))}
              />
            </div>

            {/* Recent calls */}
            <div>
              <h2 className="text-xs font-semibold text-muted-foreground tracking-wider uppercase mb-2">
                Recent calls
              </h2>
              <div className="rounded-lg border border-border overflow-hidden bg-card">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-left text-muted-foreground border-b border-border">
                        <th className="font-medium px-3 py-2">When</th>
                        <th className="font-medium px-3 py-2">For</th>
                        <th className="font-medium px-3 py-2">Entity</th>
                        <th className="font-medium px-3 py-2">Model</th>
                        <th className="font-medium px-3 py-2 text-right">Tokens</th>
                        <th className="font-medium px-3 py-2 text-right">Cost</th>
                        <th className="font-medium px-3 py-2 text-right">Latency</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.recent.length === 0 && (
                        <tr>
                          <td colSpan={7} className="px-3 py-8 text-center text-muted-foreground">
                            No AI calls yet. Process invoices or chat with Copilot to see usage here.
                          </td>
                        </tr>
                      )}
                      {data.recent.map((c) => (
                        <tr key={c.id} className="border-b border-border last:border-b-0">
                          <td className="px-3 py-2 text-muted-foreground whitespace-nowrap">
                            {timeAgo(c.created_at)}
                          </td>
                          <td className="px-3 py-2">
                            <div className="font-medium text-foreground">
                              {PURPOSE_LABEL[c.purpose] ?? c.purpose}
                            </div>
                            <div className="text-[11px] text-muted-foreground">{c.reason}</div>
                          </td>
                          <td className="px-3 py-2 text-muted-foreground whitespace-nowrap font-mono text-[11px]">
                            {c.entity_type ? `${c.entity_type}:${c.entity_id ?? ''}` : '—'}
                          </td>
                          <td className="px-3 py-2 text-muted-foreground whitespace-nowrap">
                            {c.provider === 'mock' ? 'mock' : c.model}
                          </td>
                          <td className="px-3 py-2 text-right tabular-nums text-muted-foreground whitespace-nowrap">
                            {num(c.input_tokens)}/{num(c.output_tokens)}
                          </td>
                          <td className="px-3 py-2 text-right tabular-nums font-medium text-foreground whitespace-nowrap">
                            {usd(c.cost_usd)}
                          </td>
                          <td className="px-3 py-2 text-right tabular-nums text-muted-foreground whitespace-nowrap">
                            {c.latency_ms} ms
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              <p className="text-[11px] text-muted-foreground mt-2">
                Cost is the actual token usage priced per model — the mock provider makes no real
                API call and costs nothing.
              </p>
            </div>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">Couldn't load usage.</p>
        )}
      </div>
    </div>
  )
}

function Breakdown({
  title,
  rows,
}: {
  title: string
  rows: { label: string; sub: string; cost: string }[]
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h3 className="text-xs font-semibold text-muted-foreground tracking-wider uppercase mb-3">
        {title}
      </h3>
      {rows.length === 0 ? (
        <p className="text-xs text-muted-foreground">No data yet.</p>
      ) : (
        <div className="space-y-2">
          {rows.map((r, i) => (
            <div key={i} className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="text-xs font-medium text-foreground truncate">{r.label}</div>
                <div className="text-[11px] text-muted-foreground">{r.sub}</div>
              </div>
              <div className="text-xs font-mono font-medium text-foreground tabular-nums shrink-0">
                {usd(r.cost)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
