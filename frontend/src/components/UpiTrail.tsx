"use client";

import { useState } from "react";
import { addUpiHop, removeUpiHop, type UpiHop, type UpiHopInput } from "@/lib/api";

// The form's own draft state is all-strings (an <input> always hands back a
// string, including the number field) — only converted to UpiHopInput's
// real types at submit time. Keeping the draft type honest here is what
// makes the amount field's number conversion visible instead of silently
// wrong.
type HopDraft = Partial<Record<keyof UpiHopInput, string>>;
const EMPTY: HopDraft = {};

/** A hand-entered UPI/bank leg of a money trail, rendered as a card chain —
 * front half of the same visual language the wallet-trace graph uses
 * (rounded cards, directional flow), but plain flex rather than Cytoscape:
 * a case realistically has a handful of hops, not dozens, so a canvas graph
 * engine is more machinery than the job needs.
 *
 * There is no API or dataset that produces this data. UPI and bank ledgers
 * are private, held by banks and NPCI; every hop here exists only because
 * an officer already obtained it — a bank disclosure, an NCRP complaint —
 * and is recording it, not because the tool went and found it. The final
 * connector to the wallet trace is explicitly labelled as asserted by the
 * investigator, not a proven or on-chain link: only the VASP's own KYC
 * disclosure (the BNSS s.94 route this tool already drafts) can confirm
 * that a given UPI payment actually became this wallet's funding.
 */
export function UpiTrail({
  caseId, seedAddress, chain, hops, onChange,
}: {
  caseId: number;
  seedAddress: string;
  chain: string;
  hops: UpiHop[];
  onChange: () => void;
}) {
  const [form, setForm] = useState<HopDraft>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set(key: keyof HopDraft, value: string) {
    setForm((f) => ({ ...f, [key]: value === "" ? undefined : value }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.payer_vpa && !form.payee_vpa && !form.amount) return; // nothing worth saving yet
    setBusy(true);
    setError(null);
    try {
      const { amount, ...rest } = form;
      const hop: UpiHopInput = { ...rest, ...(amount !== undefined ? { amount: Number(amount) } : {}) };
      await addUpiHop(caseId, hop);
      setForm(EMPTY);
      onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save hop");
    } finally {
      setBusy(false);
    }
  }

  async function remove(hopId: number) {
    setBusy(true);
    setError(null);
    try {
      await removeUpiHop(caseId, hopId);
      onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove hop");
    } finally {
      setBusy(false);
    }
  }

  const short = `${seedAddress.slice(0, 6)}…${seedAddress.slice(-4)}`;

  return (
    <div>
      <p className="mb-3 text-xs leading-relaxed text-ink-soft">
        No API produces this — UPI and bank ledgers are private. Record each hop by hand as it comes back
        from a bank disclosure or an NCRP complaint, in order. The last hop connects to this case&apos;s
        wallet as an <em>asserted</em> link, not a proven one: only the exchange&apos;s own KYC disclosure
        confirms a UPI payment actually became this wallet&apos;s funding.
      </p>

      {hops.length > 0 && (
        <div className="mb-4 flex flex-wrap items-stretch gap-1.5 overflow-x-auto pb-1">
          {hops.map((h, i) => (
            <div key={h.id} className="flex items-center gap-1.5">
              <HopCard hop={h} index={i + 1} onRemove={() => remove(h.id)} busy={busy} />
              <Arrow />
            </div>
          ))}
          <div className="flex min-w-[140px] flex-col justify-center rounded-md border border-dashed border-gold/60 bg-gold/5 px-3 py-2">
            <div className="text-[10px] uppercase tracking-wide text-gold">presumed off-ramp</div>
            <div className="font-mono text-xs font-semibold text-ink">{short}</div>
            <div className="text-[10px] text-ink-faint">{chain} · this case&apos;s wallet</div>
          </div>
        </div>
      )}

      {hops.length === 0 && (
        <div className="mb-4 rounded-md border border-dashed border-wire-strong bg-ledger-soft/50 px-3 py-4 text-center text-xs text-ink-soft">
          No UPI/bank hops recorded yet.
        </div>
      )}

      {error && (
        <div className="mb-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800">{error}</div>
      )}

      <form onSubmit={submit} className="rounded-md border border-wire bg-paper-raised p-3">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <MiniField label="Payer VPA">
            <input value={form.payer_vpa ?? ""} onChange={(e) => set("payer_vpa", e.target.value)}
                  placeholder="victim@paytm" className="w-full rounded-md border border-wire bg-paper-raised px-2 py-[0.3rem] font-mono text-xs outline-none focus:border-navy" />
          </MiniField>
          <MiniField label="Payer bank">
            <input value={form.payer_bank ?? ""} onChange={(e) => set("payer_bank", e.target.value)}
                  placeholder="SBI" className="w-full rounded-md border border-wire bg-paper-raised px-2 py-[0.3rem] text-xs outline-none focus:border-navy" />
          </MiniField>
          <MiniField label="Payee VPA">
            <input value={form.payee_vpa ?? ""} onChange={(e) => set("payee_vpa", e.target.value)}
                  placeholder="mule1@ybl" className="w-full rounded-md border border-wire bg-paper-raised px-2 py-[0.3rem] font-mono text-xs outline-none focus:border-navy" />
          </MiniField>
          <MiniField label="Payee bank">
            <input value={form.payee_bank ?? ""} onChange={(e) => set("payee_bank", e.target.value)}
                  placeholder="HDFC" className="w-full rounded-md border border-wire bg-paper-raised px-2 py-[0.3rem] text-xs outline-none focus:border-navy" />
          </MiniField>
          <MiniField label="Amount (₹)">
            <input type="number" min="0" step="0.01" value={form.amount ?? ""}
                  onChange={(e) => set("amount", e.target.value)} placeholder="50000" className="w-full rounded-md border border-wire bg-paper-raised px-2 py-[0.3rem] font-mono text-xs outline-none focus:border-navy" />
          </MiniField>
          <MiniField label="UTR / reference">
            <input value={form.utr ?? ""} onChange={(e) => set("utr", e.target.value)}
                  placeholder="Bank-disclosed" className="w-full rounded-md border border-wire bg-paper-raised px-2 py-[0.3rem] font-mono text-xs outline-none focus:border-navy" />
          </MiniField>
          <MiniField label="Date">
            <input type="date" value={form.transferred_at ?? ""} onChange={(e) => set("transferred_at", e.target.value)}
                  className="w-full rounded-md border border-wire bg-paper-raised px-2 py-[0.3rem] text-xs outline-none focus:border-navy" />
          </MiniField>
          <MiniField label="Source">
            <input value={form.source ?? ""} onChange={(e) => set("source", e.target.value)}
                  placeholder="Bank disclosure, 12/09/2026" className="w-full rounded-md border border-wire bg-paper-raised px-2 py-[0.3rem] text-xs outline-none focus:border-navy" />
          </MiniField>
        </div>
        <div className="mt-2 flex items-end gap-2">
          <div className="flex-1">
            <MiniField label="Note">
              <input value={form.note ?? ""} onChange={(e) => set("note", e.target.value)}
                    placeholder="Optional" className="w-full rounded-md border border-wire bg-paper-raised px-2 py-[0.3rem] text-xs outline-none focus:border-navy" />
            </MiniField>
          </div>
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-navy px-4 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
          >
            {busy ? "Saving…" : "Add hop"}
          </button>
        </div>
      </form>
    </div>
  );
}

function HopCard({ hop, index, onRemove, busy }: { hop: UpiHop; index: number; onRemove: () => void; busy: boolean }) {
  return (
    <div className="relative min-w-[160px] rounded-md border border-wire bg-paper-raised px-3 py-2 text-xs shadow-sm">
      <button
        onClick={onRemove}
        disabled={busy}
        title="Remove this hop"
        className="absolute right-1 top-1 rounded px-1 text-ink-faint hover:bg-ledger-soft hover:text-ink"
      >
        ×
      </button>
      <div className="text-[10px] uppercase tracking-wide text-ink-faint">Hop {index}</div>
      <div className="mt-0.5 font-mono font-semibold text-ink">{hop.payer_vpa ?? "unknown payer"}</div>
      <div className="text-ink-faint">↓</div>
      <div className="font-mono font-semibold text-ink">{hop.payee_vpa ?? "unknown payee"}</div>
      <div className="mt-1 flex flex-wrap gap-x-2 text-[10px] text-ink-soft">
        {hop.amount != null && <span>₹{Number(hop.amount).toLocaleString("en-IN")}</span>}
        {hop.transferred_at && <span>{new Date(hop.transferred_at).toLocaleDateString()}</span>}
      </div>
      {(hop.payer_bank || hop.payee_bank) && (
        <div className="text-[10px] text-ink-faint">
          {hop.payer_bank ?? "?"} → {hop.payee_bank ?? "?"}
        </div>
      )}
      {hop.source && <div className="mt-1 truncate text-[10px] italic text-ink-faint" title={hop.source}>{hop.source}</div>}
    </div>
  );
}

function Arrow() {
  return <span className="shrink-0 text-ink-faint">→</span>;
}

function MiniField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-0.5">
      <span className="text-[10px] text-ink-soft">{label}</span>
      {children}
    </label>
  );
}
