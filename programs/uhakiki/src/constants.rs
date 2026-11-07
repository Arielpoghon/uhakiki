//! Uhakiki on-chain constants.

/// PDA seed for the attestation account.
#[constant]
pub const ATTESTATION_SEED: &[u8] = b"attestation";

#[constant]
pub const MAX_ASSET_ID_LEN: usize = 64;

#[constant]
pub const MAX_ASSET_CLASS_LEN: usize = 32;

#[constant]
pub const MAX_RATIONALE_URI_LEN: usize = 128;
