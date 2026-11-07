use anchor_lang::prelude::*;

#[error_code]
pub enum UhakikiError {
    #[msg("asset_id must not be empty")]
    InvalidAssetId,
    #[msg("asset_id exceeds the 64-character limit")]
    AssetIdTooLong,
    #[msg("asset_class exceeds the 32-character limit")]
    AssetClassTooLong,
    #[msg("rationale_uri exceeds the 128-character limit")]
    RationaleUriTooLong,
    #[msg("attestation account belongs to another program")]
    ForeignAttestation,
    #[msg("attestation is not initialized")]
    NotInitialized,
    #[msg("attestation is already revoked")]
    AttestationRevoked,
    #[msg("only the issuer who created this attestation can revoke it")]
    UnauthorizedIssuer,
}
