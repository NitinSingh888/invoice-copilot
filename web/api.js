/* ============================================================
   Invoice Copilot — API client
   Exposes window.IC_API with async fetch helpers.
   Base: /api/v1. Sends X-Role header when a role is provided.
   ============================================================ */
window.IC_API = (function () {
  const base = "/api/v1";

  async function j(method, path, body, role) {
    const res = await fetch(base + path, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(role ? { "X-Role": role } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (res.status === 204) return null;
    if (!res.ok) throw new Error(method + " " + path + " → " + res.status);
    return res.json();
  }

  return {
    listInvoices:  ()                   => j("GET",   "/invoices"),
    getInvoice:    (id)                 => j("GET",   "/invoices/" + id),
    action:        (id, body, role)     => j("POST",  "/invoices/" + id + "/action", body, role),
    chat:          (message, history, role) => j("POST", "/chat", { message, history }, role),
    listRules:     ()                   => j("GET",   "/rules"),
    proposeRule:   ()                   => j("POST",  "/rules/propose"),
    activateRule:  (body)               => j("POST",  "/rules/activate", body),
    setRuleStatus: (id, status)         => j("PATCH", "/rules/" + id, { status }),
    trail:         (id)                 => j("GET",   "/audit/" + id),
    reset:         ()                   => j("POST",  "/demo/reset"),
  };
})();
