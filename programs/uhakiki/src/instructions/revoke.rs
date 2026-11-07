//! revoke_attestation — mark an attestation revoked (the slot remains, the
//! verdict is no longer trustworthy; reads must check `revoked`).

use anchor_lang::prelude::*;
use solana_sha256_hasher::hash;

use crate::constants::*;
use crate::error::UhakikiError;
use crate::state::*;
use anchor_lang::{AnchorDeserialize, AnchorSerialize};

#[derive(Accounts)]
#[instruction(asset_id: String, reason: String)]
pub struct RevokeAttestation<'info> {
    #[account(mut)]
    pub issuer: Signer<'info>,

    /// CHECK: PDA derived from THIS signer — a different issuer cannot even
    /// reach the original attestation, and ownership is re-checked below.
    #[account(
        mut,
        seeds = [ATTESTATION_SEED, issuer.key().as_ref(), solana_sha256_hasher::hash(asset_id.as_bytes()).as_ref()],
        bump
    )]
    pub attestation: Account<'info, Attestation>,
}

pub fn handle_revoke(ctx: Context<RevokeAttestation>, asset_id: String, reason: String) -> Result<()> {
    let info = ctx.accounts.attestation.to_account_info();
    require!(info.data_len() > 0, UhakikiError::NotInitialized);
    require!(*info.owner == crate::ID, UhakikiError::ForeignAttestation);

    let mut att = Attestation::deserialize(&mut &info.try_borrow_data()?[8..])?;
    require!(!att.revoked, UhakikiError::AttestationRevoked);
    att.revoked = true;
    let mut buf: Vec<u8> = Vec::with_capacity(8 + Attestation::INIT_SPACE);
    buf.extend_from_slice(&Attestation::DISCRIMINATOR);
    att.serialize(&mut buf)?;
    info.data.borrow_mut()[..buf.len()].copy_from_slice(&buf);

    emit!(AttestationRevoked { asset_id, reason });
    Ok(())
}

#[event]
pub struct AttestationRevoked {
    pub asset_id: String,
    pub reason: String,
}
