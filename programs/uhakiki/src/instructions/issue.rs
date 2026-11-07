//! issue_attestation — upsert one attestation PDA per (issuer, asset_id).
//!
//! The account is created via a direct system-program CPI when empty and
//! overwritten in place afterwards, so verdicts can flip as new evidence
//! arrives without re-deriving or reallocating anything (space is allocated
//! at max string lengths up front).

use anchor_lang::prelude::*;
use anchor_lang::system_program::{create_account, CreateAccount};

use crate::constants::*;
use crate::error::UhakikiError;
use crate::state::*;

#[derive(Accounts)]
#[instruction(asset_id: String, asset_class: String, rationale_uri: String)]
pub struct IssueAttestation<'info> {
    /// The rules-engine authority — must sign; its key is part of the PDA.
    #[account(mut)]
    pub issuer: Signer<'info>,

    /// CHECK: PDA derived as [ATTESTATION_SEED, issuer, asset_id]. Created
    /// here when empty; ownership + discriminator validated otherwise.
    #[account(
        mut,
        seeds = [ATTESTATION_SEED, issuer.key().as_ref(), asset_id.as_bytes()],
        bump
    )]
    pub attestation: UncheckedAccount<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handle_issue(
    ctx: Context<IssueAttestation>,
    asset_id: String,
    asset_class: String,
    verdict: Verdict,
    rule_pack_hash: [u8; 32],
    rationale_uri: String,
    issuer_ref: Pubkey,
) -> Result<()> {
    require!(!asset_id.is_empty(), UhakikiError::InvalidAssetId);
    require!(asset_id.len() <= MAX_ASSET_ID_LEN, UhakikiError::AssetIdTooLong);
    require!(
        asset_class.len() <= MAX_ASSET_CLASS_LEN,
        UhakikiError::AssetClassTooLong
    );
    require!(
        rationale_uri.len() <= MAX_RATIONALE_URI_LEN,
        UhakikiError::RationaleUriTooLong
    );

    let info = ctx.accounts.attestation.to_account_info();
    if info.data_len() == 0 {
        // First issue for this (issuer, asset_id): create the account.
        let space = Attestation::INIT_SPACE;
        let rent = Rent::get()?;
        let lamports = rent.minimum_balance(space);
        create_account(
            CpiContext::new(
                ctx.accounts.system_program.to_account_info(),
                CreateAccount {
                    from: ctx.accounts.issuer.to_account_info(),
                    to: info.clone(),
                },
            ),
            lamports,
            space as u64,
            &crate::ID(),
        )?;
    } else {
        require!(
            info.owner == &crate::ID(),
            UhakikiError::ForeignAttestation
        );
        let existing = Account::<Attestation>::try_from(&info)?;
        require!(
            existing.issuer == ctx.accounts.issuer.key(),
            UhakikiError::UnauthorizedIssuer
        );
    }

    let attestation = Attestation {
        issuer: ctx.accounts.issuer.key(),
        asset_id,
        asset_class,
        verdict,
        rule_pack_hash,
        rationale_uri,
        issuer_ref,
        revoked: false,
        created_at: Clock::get()?.unix_timestamp,
        bump: ctx.bumps.attestation,
    };

    // Overwrite in place: discriminator + borsh fields, bounded by INIT_SPACE.
    let mut buf: Vec<u8> = Vec::with_capacity(8 + Attestation::INIT_SPACE);
    buf.extend_from_slice(&Attestation::DISCRIMINATOR);
    attestation.serialize(&mut buf)?;
    info.data.borrow_mut()[..buf.len()].copy_from_slice(&buf);

    emit!(AttestationIssued {
        asset_id: attestation.asset_id,
        verdict: attestation.verdict,
    });
    Ok(())
}

#[event]
pub struct AttestationIssued {
    pub asset_id: String,
    pub verdict: Verdict,
}
