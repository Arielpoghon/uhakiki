//! issue_attestation — upsert one attestation PDA per (issuer, asset_id).
//!
//! `init_if_needed` creates the account on first issue; re-issuing overwrites
//! the fields in place (upsert), so verdicts update as new evidence arrives.
//! Space is allocated at max string lengths, so no realloc is needed. The
//! PDA seeds include the issuer's key — a different issuer derives a
//! different PDA and can never touch another issuer's slot.

use anchor_lang::prelude::*;
use solana_sha256_hasher::hash;

use crate::constants::*;
use crate::error::UhakikiError;
use crate::state::*;

#[derive(Accounts)]
#[instruction(asset_id: String, verdict: Verdict, rule_pack_hash: [u8; 32], rationale_uri: String, issuer_ref: Pubkey)]
pub struct IssueAttestation<'info> {
    /// The rules-engine authority — must sign; its key is part of the PDA.
    #[account(mut)]
    pub issuer: Signer<'info>,

    #[account(
        init_if_needed,
        payer = issuer,
        space = Attestation::INIT_SPACE,
        // asset_id can be up to 64 chars — solana seeds are capped at 32 bytes,
        // so the seed uses sha256(asset_id) (bounded, deterministic).
        seeds = [ATTESTATION_SEED, issuer.key().as_ref(), solana_sha256_hasher::hash(asset_id.as_bytes()).as_ref()],
        bump
    )]
    pub attestation: Account<'info, Attestation>,

    pub system_program: Program<'info, System>,
}

pub fn handle_issue(
    ctx: Context<IssueAttestation>,
    asset_id: String,
    verdict: Verdict,
    rule_pack_hash: [u8; 32],
    rationale_uri: String,
    issuer_ref: Pubkey,
) -> Result<()> {
    require!(!asset_id.is_empty(), UhakikiError::InvalidAssetId);
    require!(asset_id.len() <= MAX_ASSET_ID_LEN, UhakikiError::AssetIdTooLong);
    require!(
        rationale_uri.len() <= MAX_RATIONALE_URI_LEN,
        UhakikiError::RationaleUriTooLong
    );

    let attestation = &mut ctx.accounts.attestation;
    attestation.set_inner(Attestation {
        issuer: ctx.accounts.issuer.key(),
        asset_id: asset_id.clone(),
        // Extensible in Cape Town (land deeds etc.) — fixed for the MVP so the
        // instruction has no two String args (Anchor 1.2 validate-macro quirk).
        asset_class: ASSET_CLASS_INVOICE.to_string(),
        verdict,
        rule_pack_hash,
        rationale_uri,
        issuer_ref,
        revoked: false,
        created_at: Clock::get()?.unix_timestamp,
        bump: ctx.bumps.attestation,
    });

    emit!(AttestationIssued {
        asset_id: asset_id.clone(),
        verdict: attestation.verdict,
    });
    Ok(())
}

#[event]
pub struct AttestationIssued {
    pub asset_id: String,
    pub verdict: Verdict,
}
