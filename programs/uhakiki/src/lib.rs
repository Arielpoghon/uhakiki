pub mod constants;
pub mod error;
pub mod instructions;
pub mod state;

use anchor_lang::prelude::*;

pub use constants::*;
pub use error::*;
pub use instructions::*;
pub use state::*;

declare_id!("FEvabxdQJsdDaQuHi9fzWH7MvUygpMUS7DWUtmQkGVtd");

#[program]
pub mod uhakiki {
    use super::*;

    /// Upsert an attestation for (issuer, asset_id). Only records what the
    /// deterministic rules engine decided — never generates verdicts.
    pub fn issue_attestation(
        ctx: Context<IssueAttestation>,
        asset_id: String,
        asset_class: String,
        verdict: Verdict,
        rule_pack_hash: [u8; 32],
        rationale_uri: String,
        issuer_ref: Pubkey,
    ) -> Result<()> {
        crate::instructions::issue::handle_issue(
            ctx, asset_id, asset_class, verdict, rule_pack_hash, rationale_uri, issuer_ref,
        )
    }

    /// Revoke an attestation (wrong evidence, superseded decision, …).
    pub fn revoke_attestation(ctx: Context<RevokeAttestation>, asset_id: String, reason: String) -> Result<()> {
        crate::instructions::revoke::handle_revoke(ctx, asset_id, reason)
    }
}
