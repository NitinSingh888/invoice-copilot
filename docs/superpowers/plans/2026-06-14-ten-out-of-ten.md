# Invoice Copilot 10/10 Upgrades — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix every gap identified in the senior-engineer review to bring the project from 8/10 to 10/10 before client delivery.

**Architecture:** All changes are additive or surgical replacements — no refactoring of existing working code. Frontend gets URL routing via react-router-dom. Backend gets rate limiting via slowapi and a file size guard. Hardcoded demo logic is removed from UI components.

**Tech Stack:** react-router-dom (frontend routing), slowapi (backend rate limiting)

---

### Task 1: URL Routing — Install react-router-dom and wrap app

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Install react-router-dom**

```bash
cd frontend && npm install react-router-dom
```

- [ ] **Step 2: Wrap app with BrowserRouter in main.tsx**

Replace `frontend/src/main.tsx` with:

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { TooltipProvider } from '@/components/ui/tooltip'
import '@fontsource-variable/geist/index.css'
import '@fontsource-variable/geist-mono/index.css'
import './index.css'
import App from './App.tsx'
import { AuthGate } from '@/components/auth/AuthGate'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <TooltipProvider delayDuration={400}>
        <AuthGate>
          {(user) => <App userEmail={user.email} orgName={user.orgName} orgRole={user.orgRole} />}
        </AuthGate>
      </TooltipProvider>
    </BrowserRouter>
  </StrictMode>,
)
```

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/main.tsx
git commit -m "feat: install react-router-dom and wrap app with BrowserRouter"
```

---

### Task 2: URL Routing — Convert App.tsx to use Routes

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Replace view state with useNavigate/useLocation**

In `App.tsx`, replace the view state management with react-router hooks:

1. Add imports: `import { Routes, Route, useNavigate, useLocation, Navigate } from 'react-router-dom'`
2. Remove: `const [view, setView] = useState<View>('inbox')`
3. Add: `const navigate = useNavigate()` and `const location = useLocation()`
4. Derive the current view from location: `const view = (location.pathname.slice(1) || 'inbox') as View`
5. Create: `const setView = (v: View) => navigate(v === 'inbox' ? '/' : \`/\${v}\`)`
6. Replace the conditional rendering block with `<Routes>`:

```tsx
<Routes>
  <Route path="/" element={<Inbox {...inboxProps} />} />
  <Route path="/dashboard" element={<Dashboard {...dashboardProps} />} />
  <Route path="/history" element={<History onInvoiceClick={openDetail} />} />
  <Route path="/rules" element={<Rules orgRole={orgRole} />} />
  <Route path="/audit" element={<AuditLog live={healthLive} />} />
  <Route path="/guide" element={<Guide onStartTour={startTour} />} />
  <Route path="/usage" element={<Usage />} />
  <Route path="*" element={<Navigate to="/" replace />} />
</Routes>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: replace useState view routing with react-router URLs"
```

---

### Task 3: URL Routing — Update Sidebar to use navigation links

**Files:**
- Modify: `frontend/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Update Sidebar to use useLocation for active state**

1. Add import: `import { useLocation, useNavigate } from 'react-router-dom'`
2. Remove `view` and `onViewChange` from `SidebarProps`
3. Inside the component, derive the active view from the URL:
   ```tsx
   const location = useLocation()
   const navigate = useNavigate()
   const view = (location.pathname.slice(1) || 'inbox') as View
   const onViewChange = (v: View) => navigate(v === 'inbox' ? '/' : `/${v}`)
   ```
4. Keep the `View` type export unchanged (it's used elsewhere)

- [ ] **Step 2: Update App.tsx to remove view/onViewChange props from Sidebar**

Remove `view={view} onViewChange={setView}` from the `<Sidebar>` JSX in App.tsx. The Sidebar now reads from the URL directly.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/layout/Sidebar.tsx frontend/src/App.tsx
git commit -m "feat: sidebar navigates via URL instead of callback props"
```

---

### Task 4: URL Routing — Configure Vite and backend SPA fallback

**Files:**
- Modify: `frontend/vite.config.ts`
- Modify: `backend/src/app/main.py`

- [ ] **Step 1: Vite already handles SPA fallback in dev mode — verify**

Vite dev server serves `index.html` for all unknown routes by default. No change needed to `vite.config.ts`.

- [ ] **Step 2: Add SPA fallback in backend for production static serving**

In `backend/src/app/main.py`, add a catch-all route BEFORE the static mount so that non-API routes serve `index.html`:

```python
# Add after `application.include_router(api_router, prefix="/api/v1")`
# and before the static mount block:

static_dir = os.environ.get("IC_STATIC_DIR", "static")
if Path(static_dir).is_dir():
    index_html = Path(static_dir) / "index.html"

    @application.get("/{path:path}")
    async def spa_fallback(path: str) -> FileResponse:
        """Serve index.html for all non-API routes (SPA client-side routing)."""
        requested = Path(static_dir) / path
        if requested.is_file():
            return FileResponse(requested)
        return FileResponse(index_html)
```

Add `from fastapi.responses import FileResponse` to imports.

Remove the old `StaticFiles` mount (it doesn't support SPA fallback).

- [ ] **Step 3: Commit**

```bash
git add backend/src/app/main.py frontend/vite.config.ts
git commit -m "feat: SPA fallback for client-side routing in production"
```

---

### Task 5: Cold-Start Loading Screen

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Add inline loading spinner to index.html**

Replace the `<body>` content in `frontend/index.html` with:

```html
<body>
  <div id="root"></div>
  <!-- Loading screen shown before React hydrates. Removed by React when it mounts. -->
  <div id="loading-screen" style="
    position: fixed; inset: 0; z-index: 9999;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    background: #fafbfc; font-family: 'Inter', system-ui, sans-serif;
    transition: opacity 0.3s ease;
  ">
    <svg width="48" height="48" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="28" height="28" rx="7" fill="#5e6ad2"/>
      <rect x="7" y="6" width="14" height="16" rx="2" fill="white" fill-opacity="0.15"/>
      <rect x="7" y="6" width="14" height="16" rx="2" stroke="white" stroke-opacity="0.6" stroke-width="1.2"/>
      <line x1="10" y1="11" x2="18" y2="11" stroke="white" stroke-opacity="0.7" stroke-width="1.2" stroke-linecap="round"/>
      <line x1="10" y1="14" x2="16" y2="14" stroke="white" stroke-opacity="0.5" stroke-width="1.2" stroke-linecap="round"/>
      <line x1="10" y1="17" x2="14" y2="17" stroke="white" stroke-opacity="0.5" stroke-width="1.2" stroke-linecap="round"/>
      <circle cx="20" cy="20" r="5" fill="#5e6ad2"/>
      <circle cx="20" cy="20" r="5" stroke="#fafbfc" stroke-width="1.5"/>
      <path d="M17.5 20L19.2 21.7L22.5 18.5" stroke="white" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    <p style="margin-top: 16px; font-size: 15px; font-weight: 600; color: #16171a; letter-spacing: -0.01em;">
      Invoice Copilot
    </p>
    <p style="margin-top: 4px; font-size: 12px; color: #6b7280;">
      Loading…
    </p>
    <style>
      @keyframes ic-pulse { 0%,100%{opacity:.4} 50%{opacity:1} }
      #loading-screen p:last-child { animation: ic-pulse 1.5s ease-in-out infinite; }
      @media (prefers-color-scheme: dark) {
        #loading-screen { background: #0b0c0e !important; }
        #loading-screen p:first-of-type { color: #f7f8f8 !important; }
        #loading-screen p:last-child { color: #9ca3af !important; }
      }
    </style>
  </div>
  <script>
    // Remove loading screen once React renders
    const observer = new MutationObserver(() => {
      const root = document.getElementById('root');
      if (root && root.children.length > 0) {
        const screen = document.getElementById('loading-screen');
        if (screen) {
          screen.style.opacity = '0';
          setTimeout(() => screen.remove(), 300);
        }
        observer.disconnect();
      }
    });
    observer.observe(document.getElementById('root'), { childList: true });
  </script>
  <script type="module" src="/src/main.tsx"></script>
</body>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "feat: branded loading screen for cold-start and initial bundle load"
```

---

### Task 6: Remove Hardcoded Demo Logic from Frontend

**Files:**
- Modify: `frontend/src/components/invoice/ApprovalCard.tsx`
- Modify: `frontend/src/components/invoice/InvoiceInspectionCard.tsx`
- Modify: `frontend/src/pages/Inbox.tsx`

- [ ] **Step 1: Remove Acme/Priya logic from ApprovalCard.tsx**

1. Delete lines 34-38 (the `isAcmeOverPO` / `showRouteToPriya` variables)
2. Delete the `handleRouteToPriya` function (lines 58-60)
3. Replace the conditional `{showRouteToPriya ? (...Route to Priya...) : (...Approve...)}` block (lines 141-183) with just the Approve button — always show Approve as the primary action. The user can still route via the Edit button.

- [ ] **Step 2: Remove Acme/Priya logic from InvoiceInspectionCard.tsx**

1. Delete lines 27-30 (the `isAcmeOverPO` / `showRouteToPriya` variables)
2. Replace the conditional `{showRouteToPriya ? (...Route to Priya...) : (...Approve...)}` block (lines 115-157) with just the Approve button.

- [ ] **Step 3: Make chat suggestions generic in Inbox.tsx**

Replace the SUGGESTIONS constant (lines 18-23):

```tsx
const SUGGESTIONS = [
  "Process today's invoices",
  'How many need review?',
  'Show me held invoices',
  'What is the total amount pending?',
]
```

Remove the hardcoded vendor name "Acme" and "Open the rules" (which is a navigation action, not a chat command).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/invoice/ApprovalCard.tsx frontend/src/components/invoice/InvoiceInspectionCard.tsx frontend/src/pages/Inbox.tsx
git commit -m "fix: remove hardcoded Acme/Priya demo logic from UI components"
```

---

### Task 7: Backend — Rate Limiting

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/src/app/main.py`
- Modify: `backend/src/app/api/v1/routes/auth.py`
- Modify: `backend/src/app/api/v1/routes/invoices.py`

- [ ] **Step 1: Install slowapi**

Add `"slowapi>=0.1.9"` to dependencies in `backend/pyproject.toml`.

```bash
cd backend && pip install slowapi
```

- [ ] **Step 2: Set up the limiter in main.py**

Add to `main.py` after the CORS middleware:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
application.state.limiter = limiter
application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

- [ ] **Step 3: Apply rate limits to auth routes**

In `auth.py`, add `@limiter.limit("5/minute")` to signup and login endpoints.

```python
from slowapi import Limiter
from app.main import limiter

@router.post("/signup")
@limiter.limit("5/minute")
async def signup(request: Request, ...):
```

- [ ] **Step 4: Apply rate limit to upload endpoint**

In `invoices.py`, add `@limiter.limit("10/minute")` to `upload_invoice`.

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/src/app/main.py backend/src/app/api/v1/routes/auth.py backend/src/app/api/v1/routes/invoices.py
git commit -m "feat: add rate limiting (5/min auth, 10/min uploads)"
```

---

### Task 8: Backend — File Upload Size Limit

**Files:**
- Modify: `backend/src/app/api/v1/routes/invoices.py`

- [ ] **Step 1: Add size check before reading file**

In `invoices.py`, add a size guard at the top of `upload_invoice` (before `file.file.read()`):

```python
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

@router.post("/upload", status_code=201, response_model=ProcessResultOut)
def upload_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm),
    org_id: str = Depends(get_current_org),
) -> ProcessResultOut:
    file_bytes = file.file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise AppError(f"File too large ({len(file_bytes) // (1024*1024)}MB). Maximum is 10MB.")
    # ... rest of function unchanged
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/app/api/v1/routes/invoices.py
git commit -m "fix: reject uploads over 10MB to prevent OOM"
```

---

### Task 9: Polish — README Fixes, Boilerplate Cleanup, API Docs, Theme Detection

**Files:**
- Modify: `README.md`
- Delete: `frontend/README.md`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Fix React version in README.md**

Change line 189 from `React 18` to `React 19`.

- [ ] **Step 2: Add API docs mention to README.md**

In the Architecture section, after the tech stack, add:

```markdown
## API documentation

FastAPI auto-generates interactive API docs. Once running, open **http://localhost:8123/docs** (Swagger UI) or **http://localhost:8123/redoc** (ReDoc).
```

- [ ] **Step 3: Delete frontend/README.md**

```bash
rm frontend/README.md
```

- [ ] **Step 4: Add system theme detection in App.tsx**

Update the theme initializer to respect `prefers-color-scheme`:

```tsx
const [theme, setTheme] = useState<'light' | 'dark'>(
  () =>
    (localStorage.getItem('ic-theme') as 'light' | 'dark') ||
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'),
)
```

- [ ] **Step 5: Commit**

```bash
git add README.md frontend/src/App.tsx
git rm frontend/README.md
git commit -m "polish: fix README version, add API docs section, system theme detection, remove boilerplate"
```

---

## Summary

| Task | Category | Impact |
|------|----------|--------|
| 1-4 | URL Routing | CRITICAL — back button, bookmarks, shareability |
| 5 | Loading Screen | HIGH — cold-start UX on Render |
| 6 | Remove Demo Logic | HIGH — no hardcoded vendor names in prod code |
| 7 | Rate Limiting | MEDIUM — security gap closed |
| 8 | Upload Size Limit | MEDIUM — prevents OOM |
| 9 | Polish | MEDIUM — README accuracy, theme, cleanup |
