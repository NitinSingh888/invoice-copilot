import { useEffect, useRef, useState } from 'react'
import { Plus, Upload, Loader2, FileText } from 'lucide-react'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { getSamples, uploadInvoice, createInvoice } from '@/lib/api'
import { formatMoney } from '@/lib/utils'
import type { SampleInvoice } from '@/lib/types'

interface AddInvoiceDialogProps {
  onAdded: () => void
}

export function AddInvoiceDialog({ onAdded }: AddInvoiceDialogProps) {
  const [open, setOpen] = useState(false)

  function handleOpenChange(v: boolean) {
    setOpen(v)
  }

  return (
    <>
      <Button
        size="sm"
        variant="outline"
        className="h-7 text-xs gap-1.5"
        data-tour="add-invoice"
        onClick={() => setOpen(true)}
      >
        <Plus className="h-3 w-3" />
        Add invoice
      </Button>

      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-base">Add invoice</DialogTitle>
            <DialogDescription>
              Upload a PDF or pick a sample to add an invoice to the queue.
            </DialogDescription>
          </DialogHeader>

          <Tabs defaultValue="upload" className="w-full">
            <TabsList className="w-full">
              <TabsTrigger value="upload" className="flex-1">Upload PDF</TabsTrigger>
              <TabsTrigger value="samples" className="flex-1">Samples</TabsTrigger>
            </TabsList>

            <TabsContent value="upload">
              <UploadTab
                onSuccess={() => {
                  setOpen(false)
                  onAdded()
                }}
              />
            </TabsContent>

            <TabsContent value="samples">
              <SamplesTab
                onSuccess={() => {
                  setOpen(false)
                  onAdded()
                }}
              />
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>
    </>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Upload tab
// ────────────────────────────────────────────────────────────────────────────

function UploadTab({ onSuccess }: { onSuccess: () => void }) {
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFile(file: File) {
    if (!file.name.endsWith('.pdf') && file.type !== 'application/pdf') {
      toast.error('Please select a PDF file')
      return
    }
    setLoading(true)
    try {
      const result = await uploadInvoice(file)
      toast.success(
        `Added ${result.invoice_id} · ${result.status}`,
      )
      onSuccess()
    } catch (e) {
      toast.error(`Upload failed: ${(e as Error).message}`)
    } finally {
      setLoading(false)
    }
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) void handleFile(file)
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file) void handleFile(file)
  }

  return (
    <div className="mt-3 space-y-3">
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        disabled={loading}
        className={[
          'w-full rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors duration-150',
          dragging
            ? 'border-primary bg-primary/5'
            : 'border-border hover:border-primary/50 hover:bg-muted/40',
          loading ? 'pointer-events-none opacity-60' : '',
        ].join(' ')}
      >
        {loading ? (
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="h-8 w-8 text-primary animate-spin" />
            <p className="text-sm text-muted-foreground">Processing…</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <Upload className="h-8 w-8 text-muted-foreground" />
            <p className="text-sm font-medium text-foreground">Drop a PDF here</p>
            <p className="text-xs text-muted-foreground">or click to browse</p>
          </div>
        )}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,application/pdf"
        className="hidden"
        onChange={onInputChange}
      />
      <p className="text-[11px] text-muted-foreground text-center">
        No invoice handy? Try the <strong>Samples</strong> tab, or drop any PDF — Copilot extracts it.
      </p>
    </div>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Samples tab
// ────────────────────────────────────────────────────────────────────────────

const TAG_LABELS: Record<string, string> = {
  'auto-clear': 'Auto-clear',
  'escalate': 'Escalate',
  'block': 'Block',
  'under-100': 'Under $100',
  'over-1000': 'Over $1,000',
  'over-po': 'Over PO',
  'no-po': 'No PO',
  'unknown-vendor': 'Unknown vendor',
  'duplicate': 'Duplicate',
  'low-confidence': 'Low confidence',
}

function SamplesTab({ onSuccess }: { onSuccess: () => void }) {
  const [samples, setSamples] = useState<SampleInvoice[]>([])
  const [loadingSamples, setLoadingSamples] = useState(true)
  const [adding, setAdding] = useState<string | null>(null)
  const [addingAll, setAddingAll] = useState(false)
  const [activeTag, setActiveTag] = useState<string | null>(null)

  useEffect(() => {
    getSamples()
      .then(setSamples)
      .catch(() => setSamples([]))
      .finally(() => setLoadingSamples(false))
  }, [])

  const filtered = activeTag
    ? samples.filter((s) => s.tags?.includes(activeTag))
    : samples

  const allTags = Array.from(
    new Set(samples.flatMap((s) => s.tags ?? [])),
  )

  async function handleAdd(s: SampleInvoice) {
    setAdding(s.invoice_number)
    try {
      await createInvoice({
        vendor: s.vendor,
        amount: s.amount,
        invoice_number: s.invoice_number,
        po_number: s.po_number,
        confidence: s.confidence,
        source_file: s.source_file,
      })
      toast.success(`Added ${s.invoice_number} · received`)
      onSuccess()
    } catch (e) {
      toast.error(`Failed: ${(e as Error).message}`)
    } finally {
      setAdding(null)
    }
  }

  async function handleAddAll() {
    setAddingAll(true)
    let added = 0
    try {
      for (const s of filtered) {
        await createInvoice({
          vendor: s.vendor,
          amount: s.amount,
          invoice_number: s.invoice_number,
          po_number: s.po_number,
          confidence: s.confidence,
          source_file: s.source_file,
        })
        added++
      }
      toast.success(`Added ${added} sample invoice${added === 1 ? '' : 's'}`)
      onSuccess()
    } catch (e) {
      toast.error(`Added ${added}, then failed: ${(e as Error).message}`)
    } finally {
      setAddingAll(false)
    }
  }

  if (loadingSamples) {
    return (
      <div className="mt-4 flex items-center justify-center py-10">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (samples.length === 0) {
    return (
      <p className="mt-4 text-center text-sm text-muted-foreground py-8">
        No samples available from the server.
      </p>
    )
  }

  return (
    <div className="mt-3 space-y-3">
      {/* Tag filters */}
      <div className="flex flex-wrap gap-1.5">
        <button
          onClick={() => setActiveTag(null)}
          className={[
            'rounded-full border px-2.5 py-0.5 text-[11px] font-medium transition-colors',
            activeTag === null
              ? 'border-primary bg-primary/10 text-primary'
              : 'border-border text-muted-foreground hover:border-primary/50',
          ].join(' ')}
        >
          All ({samples.length})
        </button>
        {allTags.map((tag) => (
          <button
            key={tag}
            onClick={() => setActiveTag(activeTag === tag ? null : tag)}
            className={[
              'rounded-full border px-2.5 py-0.5 text-[11px] font-medium transition-colors',
              activeTag === tag
                ? 'border-primary bg-primary/10 text-primary'
                : 'border-border text-muted-foreground hover:border-primary/50',
            ].join(' ')}
          >
            {TAG_LABELS[tag] ?? tag}
          </button>
        ))}
      </div>

      {/* Bulk add button */}
      <Button
        size="sm"
        variant="outline"
        className="w-full h-8 text-xs"
        disabled={addingAll || adding !== null || filtered.length === 0}
        onClick={() => void handleAddAll()}
      >
        {addingAll ? (
          <><Loader2 className="h-3 w-3 animate-spin mr-1.5" /> Adding…</>
        ) : (
          <><Plus className="h-3 w-3 mr-1.5" /> Add all {filtered.length} sample{filtered.length === 1 ? '' : 's'}</>
        )}
      </Button>

      {/* Sample list */}
      <div className="space-y-2 max-h-[300px] overflow-y-auto">
        {filtered.map((s) => (
          <div
            key={s.invoice_number}
            className="flex items-center gap-3 rounded-lg border border-border bg-card px-3 py-2.5 hover:bg-muted/40 transition-colors"
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
              <FileText className="h-4 w-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium text-foreground">{s.label}</span>
              </div>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="text-xs text-muted-foreground">{s.vendor}</span>
                <span className="text-[10px] text-muted-foreground">·</span>
                <span className="text-xs font-mono text-muted-foreground">
                  {formatMoney(s.amount)}
                </span>
              </div>
              <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-1">
                {s.expected}
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs shrink-0"
              disabled={adding !== null || addingAll}
              onClick={() => void handleAdd(s)}
            >
              {adding === s.invoice_number ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                'Add'
              )}
            </Button>
          </div>
        ))}
      </div>
    </div>
  )
}
