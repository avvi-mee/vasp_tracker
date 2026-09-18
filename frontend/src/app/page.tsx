"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  type ChainInfo,
  type TraceResponse,
  downloadCertificate,
  getChains,
  traceWallet,
} from "@/lib/api";
import {
  Answer,
  CandidateList,
  DepositCallout,
  FieldRow,
  NextStep,
  PathFlow,
  RiskBadge,
  TypologyPanel,
} from "@/components/Verdict";
import { detectChain } from "@/lib/chainDetect";
import { InvestigationGraph, type GraphSelection } from "@/components/InvestigationGraph";
import { ExposureWheel, SeedExposureWheel } from "@/components/ExposureWheel";
import { TransactionsTable } from "@/components/TransactionsTable";
import { DetailDrawer } from "@/components/DetailDrawer";
import { AuthGuard } from "@/components/AuthGuard";
import { AppShell } from "@/components/AppShell";
import {
  Badge,
  Button,
  Card,
  Input,
  SectionTitle,
  Skeleton,
  Stat,
  Tabs,
} from "@/components/ui";
import type { Officer } from "@/lib/auth";

export default function Home() {
  return <AuthGuard>{(officer) => <HomeContent officer={officer} />}</AuthGuard>;
}

function HomeContent({ officer }: { officer: Officer }) {
  const searchParams = useSearchParams();
  const [chains, setChains] = useState<Record<string, ChainInfo>>({});
  const [address, setAddress] = useState(() => searchParams.get("address") ?? "");
  const [chain, setChain] = useState<string>("");
  const [caseReference, setCaseReference] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TraceResponse | null>(null);
  const [certBusy, setCertBusy] = useState(false);
  const [tab, setTab] = useState<"graph" | "transactions">("graph");
  const [activeAsset, setActiveAsset] = useState<string | null>(null);
  const [selection, setSelection] = useState<GraphSelection | null>(null);

  // Live, client-side, before the officer even submits -- the one thing
  // they asked for: which chain this address will actually be traced on.
  const detected = useMemo(() => detectChain(address), [address]);

  const assets = useMemo(
    () => Array.from(new Set((result?.trace.candidates ?? []).map((c) => c.asset?.[0]).filter(Boolean))) as string[],
    [result]
  );

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
    await runTraceFor(address);
  }

  async function runTraceFor(addr: string) {
    if (!addr.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await traceWallet({ address: addr.trim(), chain: chain || undefined });
      setResult(res);
      setActiveAsset(null);
      setSelection(null);
      setTab("graph");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Trace failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  // Arrived via the Dashboard's quick-lookup (?address=...) -- trace it
  // immediately rather than making the officer paste it again and click.
  useEffect(() => {
    const fromQuery = searchParams.get("address");
    if (fromQuery) runTraceFor(fromQuery);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  const trace = result?.trace;

  return (
    <AppShell
      officer={officer}
      title="Investigate a wallet"
      subtitle="Follow the money to the nearest exchange, and say what the wallet's own behaviour shows"
    >
      <form onSubmit={runTrace} className="flex flex-col gap-2 sm:flex-row">
        <div className="flex-1">
          <Input
            value={address}
            onChange={setAddress}
            mono
            className="w-full"
            ariaLabel="Wallet address"
            placeholder="Paste any wallet address — Ethereum, Polygon, Tron, Solana, Bitcoin or BNB"
          />
          {address.trim() && (
            <div className="mt-1 flex items-center gap-1.5 text-[11px]">
              {detected.chain ? (
                <>
                  <span className="font-semibold text-navy">Detected: {detected.chain}</span>
                  <span className="text-ink-faint">&mdash; {detected.note}</span>
                </>
              ) : (
                <span className="text-ink-faint">{detected.note}</span>
              )}
            </div>
          )}
        </div>
        <select
          value={chain}
          onChange={(e) => setChain(e.target.value)}
          aria-label="Chain"
          className="h-fit rounded-md border border-wire bg-paper-raised px-3 py-2 text-sm outline-none focus:border-navy"
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
        <Button type="submit" disabled={loading} className="h-fit">
          {loading ? "Tracing…" : "Trace wallet"}
        </Button>
      </form>

      {error && (
        <div
          className="mt-4 rounded-lg border px-3 py-2 text-sm"
          style={{
            color: "var(--color-risk-high-fg)",
            background: "var(--color-risk-high-bg)",
            borderColor: "var(--color-risk-high-line)",
          }}
        >
          {error}
        </div>
      )}

      {loading && <TraceSkeleton />}

      {!loading && !result && !error && <Primer />}

      {!loading && result && trace && (
        <div className="mt-6">
          <div className="grid gap-3 lg:grid-cols-[3fr_2fr]">
            <Answer
              label={trace.label}
              entityType={trace.entity_type}
              hopCount={trace.hop_count}
              confidence={trace.confidence}
              source={trace.source}
              maxHops={trace.max_hops}
              chain={result.chain}
            />
            <RiskBadge risk={result.risk} />
          </div>

          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Chain" value={result.chain} />
            <Stat
              label="Asset followed"
              value={trace.asset?.[0] ?? "—"}
              hint={trace.asset?.[1] ? "token contract on file" : "native asset"}
            />
            <Stat
              label="Search depth"
              value={`${trace.hop_count} / ${trace.max_hops}`}
              hint={trace.hop_count < trace.max_hops ? "stopped early — entity found" : "hop limit reached"}
            />
            <Stat label="Case ID" value={result.case_id ? `#${result.case_id}` : "not saved"} />
          </div>

          {trace.caveats.length > 0 && (
            <div
              className="mt-3 rounded-lg border px-3 py-2 text-xs leading-relaxed"
              style={{
                color: "var(--color-risk-medium-fg)",
                background: "var(--color-risk-medium-bg)",
                borderColor: "var(--color-risk-medium-line)",
              }}
            >
              <b>Limits of this search</b>
              <ul className="mt-1 list-disc space-y-0.5 pl-4">
                {trace.caveats.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          )}

          <SectionTitle hint="Computed from this wallet's own transactions — no label required">
            Laundering typologies
          </SectionTitle>
          <TypologyPanel typologies={trace.typologies} />

          <SectionTitle
            hint={
              trace.explorer_flagged.length > 0
                ? `${trace.explorer_flagged.length} address(es) flagged by the block explorer`
                : undefined
            }
          >
            Traced path
          </SectionTitle>
          <Card padded>
            <PathFlow
              path={trace.path}
              entityType={trace.entity_type}
              label={trace.label}
              flagged={trace.explorer_flagged}
            />
          </Card>

          {trace.deposit && (
            <>
              <SectionTitle>Deposit address</SectionTitle>
              <DepositCallout deposit={trace.deposit} />
            </>
          )}

          <SectionTitle hint="Shares can overlap — a path touching two categories counts toward both">
            Exposure
          </SectionTitle>
          <div className="grid gap-3 xl:grid-cols-2">
            <Card title="Along the trace" subtitle="Direct = immediate counterparty · Indirect = reached through intermediaries">
              <ExposureWheel direct={trace.exposure.direct} indirect={trace.exposure.indirect} />
            </Card>
            <Card title="At this address" subtitle="Who paid in, and where it went out">
              <SeedExposureWheel
                receiving={trace.seed_exposure.receiving}
                sending={trace.seed_exposure.sending}
              />
            </Card>
          </div>

          <SectionTitle
            hint={
              assets.length > 1 ? (
                <span className="flex flex-wrap gap-1.5">
                  <AssetChip active={activeAsset === null} onClick={() => setActiveAsset(null)}>
                    All assets
                  </AssetChip>
                  {assets.map((a) => (
                    <AssetChip key={a} active={activeAsset === a} onClick={() => setActiveAsset(a)}>
                      {a}
                    </AssetChip>
                  ))}
                </span>
              ) : undefined
            }
          >
            Transaction graph
          </SectionTitle>
          <div className="mb-3">
            <Tabs
              value={tab}
              onChange={setTab}
              options={[
                { value: "graph", label: "Graph" },
                { value: "transactions", label: `Transactions (${trace.edges.length})` },
              ]}
            />
          </div>

          {tab === "graph" ? (
            <InvestigationGraph
              seedAddress={trace.seed_address}
              candidates={trace.candidates}
              edges={trace.edges}
              activeAsset={activeAsset}
              flagged={trace.explorer_flagged}
              onSelect={setSelection}
            />
          ) : (
            <TransactionsTable
              edges={trace.edges}
              onSelect={(edge) => setSelection({ kind: "edge", edge })}
            />
          )}

          <SectionTitle hint={`${trace.candidates.length} terminal${trace.candidates.length === 1 ? "" : "s"} reached`}>
            Where the value went
          </SectionTitle>
          <CandidateList candidates={trace.candidates} />

          <SectionTitle>Next step</SectionTitle>
          <NextStep draft={result.sahyog_draft} />

          <SectionTitle>Evidence record</SectionTitle>
          <Card padded>
            <FieldRow label="Subject address" value={trace.seed_address} mono />
            <FieldRow label="Chain" value={result.chain} />
            <FieldRow label="Attributed entity" value={trace.label ?? "None — unattributed"} />
            <FieldRow label="Attribution source" value={trace.source ?? "—"} mono />
            <FieldRow
              label="Risk basis"
              value={
                <span className="flex flex-wrap justify-end gap-1">
                  <Badge tone={result.risk.risk_level}>{result.risk.risk_level}</Badge>
                  <Badge tone="neutral">{result.risk.basis}</Badge>
                  {result.risk.typologies.map((t) => (
                    <Badge key={t} tone="neutral">
                      {t.replace(/_/g, " ")}
                    </Badge>
                  ))}
                </span>
              }
            />
            <FieldRow
              label="Compliance status"
              value={`${result.risk.compliance_status} — ${result.risk.compliance_detail}`}
            />
            {trace.reason && <FieldRow label="Trace outcome" value={trace.reason} />}
          </Card>

          <SectionTitle>Court evidence certificate — s.63 BSA, 2023</SectionTitle>
          <Card padded>
            <p className="mb-3 text-xs leading-relaxed text-ink-soft">
              Generates Part A and Part B pre-filled with the trace findings and the SHA-256 of the record,
              leaving every sworn statement blank for the officer and expert who must sign it. Nothing here
              is signed automatically.
            </p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input
                value={caseReference}
                onChange={setCaseReference}
                className="flex-1"
                placeholder="Case / FIR reference (appears on the certificate)"
              />
              <Button tone="accent" onClick={handleCertificate} disabled={certBusy}>
                {certBusy ? "Generating…" : "Download evidence pack"}
              </Button>
            </div>
          </Card>
        </div>
      )}

      <DetailDrawer
        selection={selection}
        candidates={trace?.candidates ?? []}
        edges={trace?.edges ?? []}
        chain={result?.chain ?? ""}
        onClose={() => setSelection(null)}
      />
    </AppShell>
  );
}

/** A trace is seconds of real network work against rate-limited public APIs.
 * A disabled button and an unchanged page reads as a hang. */
function TraceSkeleton() {
  return (
    <div className="mt-6">
      <div className="grid gap-3 lg:grid-cols-[3fr_2fr]">
        <Skeleton className="h-28 rounded-xl" />
        <Skeleton className="h-28 rounded-xl" />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-16 rounded-lg" />
        ))}
      </div>
      <p className="mt-4 text-xs text-ink-soft">
        Following the money hop by hop against live block-explorer APIs. Branches that reach a named
        exchange stop early; unattributed ones run to the hop limit, so a wallet with nothing to find takes
        longest.
      </p>
      <Skeleton className="mt-3 h-48 rounded-xl" />
    </div>
  );
}

function Primer() {
  return (
    <div className="mt-8 grid gap-3 sm:grid-cols-3">
      {[
        {
          h: "1 · Attribute",
          p: "Follows the value outward, ranking every material split rather than the single biggest edge, until it reaches an address a dataset can name.",
        },
        {
          h: "2 · Assess",
          p: "Scores the wallet on its own behaviour — funnelling, layering, smurfing, peel chains — so a scam wallet is flagged even when nothing on its trail carries a label.",
        },
        {
          h: "3 · Act",
          p: "Names the deposit address, the recommended instrument (BNSS s.94 / s.107, PMLA s.5) and generates the s.63 BSA evidence pack for an officer to sign.",
        },
      ].map((c) => (
        <Card key={c.h}>
          <div className="text-sm font-semibold text-navy">{c.h}</div>
          <p className="mt-1 text-xs leading-relaxed text-ink-soft">{c.p}</p>
        </Card>
      ))}
    </div>
  );
}

function AssetChip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold transition-colors ${
        active ? "border-gold bg-gold/10 text-gold" : "border-wire text-ink-soft hover:border-wire-strong"
      }`}
    >
      {children}
    </button>
  );
}
