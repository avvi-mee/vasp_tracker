"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  type CaseDetail,
  generateSahyogDraft,
  getCase,
  updateCase,
  updateSahyogStatus,
} from "@/lib/api";
import type { Officer } from "@/lib/auth";
import { entityColor, entityPlainLabel } from "@/lib/entityColors";
import { AuthGuard } from "@/components/AuthGuard";
import { AppShell } from "@/components/AppShell";

const SAHYOG_PIPELINE = ["draft", "ready_for_submission", "submitted", "acknowledged", "fulfilled"] as const;

export default function CaseDetailPage() {
  return <AuthGuard>{(officer) => <CaseDetailContent officer={officer} />}</AuthGuard>;
}

function CaseDetailContent({ officer }: { officer: Officer }) {
  const params = useParams<{ id: string }>();
  const caseId = Number(params.id);

  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [ncrp, setNcrp] = useState("");
  const [cctns, setCctns] = useState("");

  const reload = useCallback(() => {
    getCase(caseId)
      .then((c) => {
        setCaseData(c);
        setNcrp(c.ncrp_ack_number ?? "");
        setCctns(c.cctns_fir_number ?? "");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load case"));
  }, [caseId]);

  useEffect(() => {
    if (Number.isFinite(caseId)) reload();
  }, [caseId, reload]);

  async function withBusy(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  if (error && !caseData) {
    return (
      <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-10">
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</div>
      </main>
    );
  }
  if (!caseData) return null;

  return (
    <AppShell officer={officer} title={`Case #${caseData.id}`} subtitle={`${caseData.seed_address} · ${caseData.chain}`}>
{error && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</div>
      )}

      <section className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Tile label="Reached" value={caseData.label ?? entityPlainLabel(caseData.entity_type)}
              color={entityColor(caseData.entity_type)} />
        <Tile label="Confidence" value={caseData.confidence != null ? `${(caseData.confidence * 100).toFixed(0)}%` : "—"} />
        <Tile label="Hops" value={String(caseData.hop_count ?? "—")} />
        <Tile label="Risk" value={caseData.risk_level} />
      </section>

      <section className="mb-6">
        <SectionTitle>Case management</SectionTitle>
        <div className="flex flex-wrap items-end gap-3 text-xs">
          <Field label="Status">
            <select
              value={caseData.status}
              disabled={busy}
              onChange={(e) => withBusy(() => updateCase(caseId, { status: e.target.value as CaseDetail["status"] }))}
              className="rounded-md border border-wire bg-paper-raised px-2 py-1.5 capitalize"
            >
              <option value="open">Open</option>
              <option value="pending">Pending</option>
              <option value="closed">Closed</option>
            </select>
          </Field>
          <Field label="NCRP acknowledgement">
            <input
              value={ncrp}
              onChange={(e) => setNcrp(e.target.value)}
              onBlur={() => ncrp !== (caseData.ncrp_ack_number ?? "") && withBusy(() => updateCase(caseId, { ncrp_ack_number: ncrp }))}
              placeholder="e.g. 12345678901234"
              className="w-44 rounded-md border border-wire bg-paper-raised px-2 py-1.5 font-mono"
            />
          </Field>
          <Field label="CCTNS FIR number">
            <input
              value={cctns}
              onChange={(e) => setCctns(e.target.value)}
              onBlur={() => cctns !== (caseData.cctns_fir_number ?? "") && withBusy(() => updateCase(caseId, { cctns_fir_number: cctns }))}
              placeholder="e.g. FIR 0142/2026"
              className="w-44 rounded-md border border-wire bg-paper-raised px-2 py-1.5 font-mono"
            />
          </Field>
        </div>
      </section>

      <section className="mb-6">
        <SectionTitle>SAHYOG disclosure request</SectionTitle>
        <p className="mb-2 text-xs text-ink-soft">
          Manual status tracking — nothing syncs automatically, since no public SAHYOG API exists to
          sync against. Update the status yourself as the request moves through the real portal.
        </p>
        {!caseData.sahyog_status ? (
          <button
            onClick={() => withBusy(() => generateSahyogDraft(caseId))}
            disabled={busy}
            className="rounded-md bg-navy px-4 py-2 text-xs font-semibold text-white disabled:opacity-50"
          >
            {busy ? "Generating…" : "Generate SAHYOG request"}
          </button>
        ) : (
          <div className="rounded-md border border-wire bg-paper-raised p-4 text-xs">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className="font-semibold text-navy">
                {(caseData.sahyog_draft?.recommended_instrument as { label?: string })?.label ?? caseData.sahyog_instrument}
              </span>
              <select
                value={caseData.sahyog_status}
                disabled={busy}
                onChange={(e) => withBusy(() => updateSahyogStatus(caseId, e.target.value))}
                className="rounded-md border border-wire bg-paper-raised px-2 py-1 capitalize"
              >
                {SAHYOG_PIPELINE.map((s) => (
                  <option key={s} value={s}>
                    {s.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </div>
            <p className="mb-2 text-ink-soft">
              {(caseData.sahyog_draft?.recommended_instrument as { reason?: string })?.reason}
            </p>
            <button
              onClick={() => withBusy(() => generateSahyogDraft(caseId))}
              disabled={busy}
              className="text-navy underline"
            >
              Regenerate draft
            </button>
          </div>
        )}
      </section>

      <section>
        <SectionTitle>Timeline</SectionTitle>
        <div className="flex flex-col gap-2">
          {caseData.events.length === 0 && <div className="text-xs text-ink-soft">No events yet.</div>}
          {caseData.events.map((e) => (
            <div key={e.id} className="flex items-center justify-between text-xs">
              <span className="font-medium">{e.action.replaceAll("_", " ")}</span>
              <span className="text-ink-soft">{new Date(e.created_at).toLocaleString()}</span>
            </div>
          ))}
        </div>
      </section>
    </AppShell>
  );
}

function Tile({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-lg border border-wire bg-paper-raised px-4 py-3">
      <div className="text-[11px] uppercase tracking-wide text-ink-soft">{label}</div>
      <div className="font-mono text-lg font-semibold" style={{ color: color ?? "var(--color-ink)" }}>
        {value}
      </div>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-soft">{children}</h3>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[11px] text-ink-soft">{label}</span>
      {children}
    </label>
  );
}
