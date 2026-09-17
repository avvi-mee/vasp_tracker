"use client";

import { useEffect, useState } from "react";
import {
  type ChainInfo,
  type TraceResponse,
  downloadCertificate,
  getChains,
  traceWallet,
} from "@/lib/api";
import {
  CandidateList,
  DepositCallout,
  FieldRow,
  PathFlow,
  RiskBadge,
  SectionTitle,
  StatTile,
} from "@/components/Verdict";

export default function Home() {
  const [chains, setChains] = useState<Record<string, ChainInfo>>({});
  const [address, setAddress] = useState("");
  const [chain, setChain] = useState<string>("");
  const [caseReference, setCaseReference] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TraceResponse | null>(null);
  const [certBusy, setCertBusy] = useState(false);

  useEffect(() => {
    getChains()
      .then(setChains)
      .catch(() =>
        setError(
          "Can't reach the API — is it running? (uvicorn app.api.main:app --host 127.0.0.1 --port 8000)"
        )
      );
  }, []);

  async function runTrace(e: React.FormEvent) {
    e.preventDefault();
    if (!address.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await traceWallet({ address: address.trim(), chain: chain || undefined });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Trace failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  async function handleCertificate() {
    if (!address.trim()) return;
    setCertBusy(true);
    try {
      await downloadCertificate({
        address: address.trim(),
        chain: result?.chain,
        case_reference: caseReference,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Certificate generation failed");
    } finally {
      setCertBusy(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-10">
      <header className="mb-8">
        <div className="text-xl font-bold text-navy">VASP Trace</div>
        <div className="font-mono text-xs text-ink-soft">SIH26182 · MHA / I4C</div>
      </header>

      <form onSubmit={runTrace} className="flex flex-col gap-3 sm:flex-row">
        <input
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="Paste any wallet address — Ethereum, Polygon, Tron, Solana, or Bitcoin"
          className="flex-1 rounded-md border border-wire bg-paper-raised px-3 py-2 font-mono text-sm outline-none focus:border-navy"
        />
        <select
          value={chain}
          onChange={(e) => setChain(e.target.value)}
          className="rounded-md border border-wire bg-paper-raised px-3 py-2 text-sm"
        >
          <option value="">Auto-detect chain</option>
          {Object.entries(chains)
            .filter(([, cfg]) => cfg.enabled)
            .map(([name]) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
        </select>
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-navy px-5 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          {loading ? "Tracing…" : "Trace wallet"}
        </button>
      </form>

      {error && (
        <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-8">
          <SectionTitle>Verdict</SectionTitle>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile label="Entity type" value={result.trace.entity_type} />
            <StatTile
              label="Confidence"
              value={result.trace.confidence ? `${(result.trace.confidence * 100).toFixed(0)}%` : "—"}
            />
            <StatTile label="Hops traced" value={String(result.trace.hop_count)} />
            <StatTile label="Case ID" value={result.case_id ? `#${result.case_id}` : "not saved"} />
          </div>

          <div className="mt-3">
            <RiskBadge risk={result.risk} />
          </div>

          {result.trace.caveats.length > 0 && (
            <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
              {result.trace.caveats.map((c, i) => (
                <div key={i}>{c}</div>
              ))}
            </div>
          )}

          <SectionTitle>Traced path</SectionTitle>
          <PathFlow
            path={result.trace.path}
            entityType={result.trace.entity_type}
            label={result.trace.label}
          />

          {result.trace.candidates.length > 1 && (
            <>
              <SectionTitle>
                Ranked candidates — the value split {result.trace.candidates.length} ways
              </SectionTitle>
              <CandidateList candidates={result.trace.candidates} />
            </>
          )}

          {result.trace.deposit && (
            <>
              <SectionTitle>Deposit address</SectionTitle>
              <DepositCallout deposit={result.trace.deposit} />
            </>
          )}

          <SectionTitle>Evidence</SectionTitle>
          <div>
            <FieldRow label="Seed address" value={result.trace.seed_address} mono />
            <FieldRow label="Chain" value={result.chain} />
            <FieldRow label="Attributed entity" value={result.trace.label ?? "None — unattributed"} />
            <FieldRow
              label="Compliance status"
              value={`${result.risk.compliance_status} — ${result.risk.compliance_detail}`}
            />
            {result.trace.source && <FieldRow label="Label source" value={result.trace.source} mono />}
            {result.trace.reason && <FieldRow label="Trace outcome" value={result.trace.reason} />}
          </div>

          <SectionTitle>Court evidence certificate — s.63 BSA, 2023</SectionTitle>
          <p className="mb-2 text-xs text-ink-soft">
            Generates Part A and Part B pre-filled with the trace findings and the SHA-256 of the
            record, leaving every sworn statement blank for the officer and expert who must sign it.
          </p>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              value={caseReference}
              onChange={(e) => setCaseReference(e.target.value)}
              placeholder="Case / FIR reference (appears on the certificate)"
              className="flex-1 rounded-md border border-wire bg-paper-raised px-3 py-2 text-sm outline-none focus:border-navy"
            />
            <button
              onClick={handleCertificate}
              disabled={certBusy}
              className="rounded-md bg-gold px-5 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {certBusy ? "Generating…" : "Download evidence pack"}
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
