// Mirrors app/graph/chain_detect.py's regexes exactly (same order, same
// caveats) so the officer sees the chain this tool will actually use before
// they submit, not just in the result after. One string-pattern function
// isn't worth a network round-trip -- kept in sync by hand since both sides
// are a handful of lines that rarely change.

const EVM = /^0x[0-9a-fA-F]{40}$/;
const TRON = /^T[1-9A-HJ-NP-Za-km-z]{33}$/;
const BITCOIN = /^(bc1[0-9a-z]{25,90}|[13][1-9A-HJ-NP-Za-km-z]{25,34})$/;
// No fixed prefix for Solana -- base58, 32-44 chars, checked last so it
// doesn't swallow a Bitcoin/Tron match that also happens to be base58.
const SOLANA = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;

export interface DetectedChain {
  chain: string | null;
  note: string;
}

export function detectChain(address: string): DetectedChain {
  const trimmed = address.trim();
  if (!trimmed) return { chain: null, note: "" };

  if (EVM.test(trimmed)) {
    return {
      chain: "Ethereum",
      note: "EVM-format — same as Polygon and BNB Chain. Defaulting to Ethereum; pick a chain above if you meant one of the others.",
    };
  }
  if (TRON.test(trimmed)) return { chain: "Tron", note: "Tron-format address (starts with T)." };
  if (BITCOIN.test(trimmed)) return { chain: "Bitcoin", note: "Bitcoin-format address." };
  if (SOLANA.test(trimmed)) return { chain: "Solana", note: "Base58 — best guess Solana (no fixed prefix to be certain)." };
  return { chain: null, note: "Format not recognised yet — pick the chain manually." };
}
