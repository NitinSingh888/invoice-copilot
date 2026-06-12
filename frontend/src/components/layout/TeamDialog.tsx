import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { getOrgMembers, getPendingMembers, verifyMember } from '@/lib/api'
import type { OrgMember } from '@/lib/types'

interface TeamDialogProps {
  open: boolean
  onOpenChange: (v: boolean) => void
}

export function TeamDialog({ open, onOpenChange }: TeamDialogProps) {
  const [members, setMembers] = useState<OrgMember[]>([])
  const [pending, setPending] = useState<OrgMember[]>([])
  const [loading, setLoading] = useState(false)
  const [verifying, setVerifying] = useState<string | null>(null)

  async function loadData() {
    setLoading(true)
    try {
      const [m, p] = await Promise.all([getOrgMembers(), getPendingMembers()])
      setMembers(m)
      setPending(p)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load team members')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open) void loadData()
  }, [open])

  async function handleVerify(userId: string, email: string) {
    setVerifying(userId)
    try {
      await verifyMember(userId)
      toast.success(`Approved ${email}`)
      await loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to approve member')
    } finally {
      setVerifying(null)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle className="text-sm font-semibold">Team</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 mt-1">
          {/* Pending approvals */}
          {(loading || pending.length > 0) && (
            <div>
              <p className="text-[10px] font-semibold text-muted-foreground tracking-wider uppercase mb-2">
                Pending approval
              </p>
              {loading ? (
                <div className="space-y-2">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                </div>
              ) : (
                <div className="space-y-1.5">
                  {pending.map((m) => (
                    <div
                      key={m.id}
                      className="flex items-center gap-3 px-3 py-2 rounded-md border border-border bg-muted/30"
                    >
                      <span className="flex-1 text-xs font-mono truncate text-foreground">{m.email}</span>
                      <Badge variant="warning" className="text-[10px] shrink-0">pending</Badge>
                      <Button
                        size="sm"
                        className="h-6 text-xs px-2 shrink-0"
                        disabled={verifying !== null}
                        onClick={() => void handleVerify(m.id, m.email)}
                      >
                        {verifying === m.id ? 'Approving…' : 'Verify'}
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Active members */}
          <div>
            <p className="text-[10px] font-semibold text-muted-foreground tracking-wider uppercase mb-2">
              Members
            </p>
            {loading ? (
              <div className="space-y-2">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            ) : members.length === 0 ? (
              <p className="text-xs text-muted-foreground">No members yet.</p>
            ) : (
              <div className="space-y-1.5">
                {members.map((m) => (
                  <div
                    key={m.id}
                    className="flex items-center gap-3 px-3 py-2 rounded-md border border-border bg-card"
                  >
                    <span className="flex-1 text-xs font-mono truncate text-foreground">{m.email}</span>
                    <Badge
                      variant={m.role === 'admin' ? 'default' : 'muted'}
                      className="text-[10px] shrink-0 capitalize"
                    >
                      {m.role}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
