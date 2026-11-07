//! Uhakiki on-chain state — an EAS-style attestation registry for RWA verdicts.

use anchor_lang::prelude::*;

/// The verdict the deterministic rules engine produced. Uhakiki never
/// invents verdicts on-chain — it records what the engine decided.
#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq, InitSpace)]
pub enum Verdict {
    Allow,
    Restrict,
    Deny,
}

/// One compliance attestation: (issuer, asset_id) → verdict + provenance.
/// PDA seeds: ["attestation", issuer, asset_id] — one slot per issuer per
/// asset; re-issuing overwrites (upsert) so verdicts update as new evidence
/// arrives, leaving a complete history in the transaction log.
#[account]
#[derive(InitSpace)]
pub struct Attestation {
    pub issuer: Pubkey,
    #[max_len(64)]
    pub asset_id: String,
    #[max_len(32)]
    pub asset_class: String,
    pub verdict: Verdict,
    /// sha256 of the YAML rule pack that produced this verdict — makes the
    /// decision reproducible from the pack stored off-chain.
    pub rule_pack_hash: [u8; 32],
    /// URI to the full AI rationale + audit trail (off-chain artifact).
    #[max_len(128)]
    pub rationale_uri: String,
    /// Rules-engine run reference (off-chain trace id).
    pub issuer_ref: Pubkey,
    pub revoked: bool,
    pub created_at: i64,
    pub bump: u8,
}
