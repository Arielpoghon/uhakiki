//! Uhakiki program tests — LiteSVM in-process (no validator, no SOL needed).
//! The verdict matrix of the on-chain layer: issue → upsert → revoke → auth.

use anchor_lang::{AnchorDeserialize, AnchorSerialize};
use litesvm::LiteSVM;
use solana_keypair::Keypair;
use solana_message::Message;
use solana_signer::Signer;
use solana_transaction::Transaction;
use uhakiki::{Attestation, Verdict};

const PROGRAM_PATH: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../target/deploy/uhakiki.so"
);

fn setup() -> (LiteSVM, Keypair) {
    let mut svm = LiteSVM::new();
    svm.add_program_file(PROGRAM_PATH).unwrap();
    let payer = Keypair::new();
    svm.airdrop(&payer.pubkey(), 10_000_000_000).unwrap();
    (svm, payer)
}

fn attestation_pda(issuer: &solana_pubkey::Pubkey, asset_id: &str) -> solana_pubkey::Pubkey {
    solana_pubkey::Pubkey::find_program_address(
        &[b"attestation", issuer.as_ref(), asset_id.as_bytes()],
        &uhakiki::ID,
    )
}

fn issue_ix(
    payer: &Keypair,
    asset_id: &str,
    verdict: Verdict,
    rule_pack_hash: [u8; 32],
) -> solana_instruction::Instruction {
    let pda = attestation_pda(&payer.pubkey(), asset_id);
    let accounts = uhakiki::accounts::IssueAttestation {
        issuer: payer.pubkey(),
        attestation: pda,
        system_program: solana_system_interface::program::ID,
    }
    .to_account_metas(None);
    let data = uhakiki::instruction::IssueAttestation {
        asset_id: asset_id.to_string(),
        asset_class: "invoice".to_string(),
        verdict,
        rule_pack_hash,
        rationale_uri: "https://uhakiki.demo/rationale/001".to_string(),
        issuer_ref: payer.pubkey(),
    }
    .data();
    solana_instruction::Instruction {
        program_id: uhakiki::ID,
        accounts,
        data,
    }
}

fn revoke_ix(payer: &Keypair, asset_id: &str, reason: &str) -> solana_instruction::Instruction {
    let pda = attestation_pda(&payer.pubkey(), asset_id);
    let accounts = uhakiki::accounts::RevokeAttestation {
        issuer: payer.pubkey(),
        attestation: pda,
    }
    .to_account_metas(None);
    let data = uhakiki::instruction::RevokeAttestation {
        asset_id: asset_id.to_string(),
        reason: reason.to_string(),
    }
    .data();
    solana_instruction::Instruction {
        program_id: uhakiki::ID,
        accounts,
        data,
    }
}

fn send(svm: &mut LiteSVM, payer: &Keypair, ixs: &[solana_instruction::Instruction]) -> Result<(), litesvm::InvokeError> {
    let blockhash = svm.latest_blockhash();
    let tx = Transaction::new(
        &[payer],
        Message::new(ixs, Some(&payer.pubkey())),
        blockhash,
    );
    svm.send_transaction(tx)
}

fn fetch(svm: &LiteSVM, pda: &solana_pubkey::Pubkey) -> Attestation {
    let raw = svm.get_account(pda).expect("attestation account must exist");
    let mut data = &raw.data[8..];
    Attestation::deserialize(&mut data).unwrap()
}

const PACK_HASH: [u8; 32] = [7u8; 32];

#[test]
fn issue_allow_creates_attestation() {
    let (mut svm, payer) = setup();
    send(&mut svm, &payer, &[issue_ix(&payer, "INV-TEST-0001", Verdict::Allow, PACK_HASH)])
        .expect("issue must succeed");
    let att = fetch(&svm, &attestation_pda(&payer.pubkey(), "INV-TEST-0001"));
    assert_eq!(att.verdict, Verdict::Allow);
    assert_eq!(att.asset_id, "INV-TEST-0001");
    assert_eq!(att.asset_class, "invoice");
    assert_eq!(att.rule_pack_hash, PACK_HASH);
    assert!(!att.revoked);
    assert_eq!(att.issuer, payer.pubkey());
}

#[test]
fn reissue_deny_flips_verdict_upsert() {
    let (mut svm, payer) = setup();
    send(&mut svm, &payer, &[issue_ix(&payer, "INV-TEST-0002", Verdict::Allow, PACK_HASH)])
        .expect("first issue must succeed");
    send(&mut svm, &payer, &[issue_ix(&payer, "INV-TEST-0002", Verdict::Deny, PACK_HASH)])
        .expect("upsert must succeed");
    let att = fetch(&svm, &attestation_pda(&payer.pubkey(), "INV-TEST-0002"));
    assert_eq!(att.verdict, Verdict::Deny, "upsert must overwrite the verdict");
}

#[test]
fn revoke_marks_revoked() {
    let (mut svm, payer) = setup();
    send(&mut svm, &payer, &[issue_ix(&payer, "INV-TEST-0003", Verdict::Restrict, PACK_HASH)])
        .expect("issue must succeed");
    send(&mut svm, &payer, &[revoke_ix(&payer, "INV-TEST-0003", "buyer sanctions hit")])
        .expect("revoke must succeed");
    let att = fetch(&svm, &attestation_pda(&payer.pubkey(), "INV-TEST-0003"));
    assert!(att.revoked);
}

#[test]
fn double_revoke_fails() {
    let (mut svm, payer) = setup();
    send(&mut svm, &payer, &[issue_ix(&payer, "INV-TEST-0004", Verdict::Deny, PACK_HASH)])
        .expect("issue must succeed");
    send(&mut svm, &payer, &[revoke_ix(&payer, "INV-TEST-0004", "first")])
        .expect("first revoke must succeed");
    let err = send(&mut svm, &payer, &[revoke_ix(&payer, "INV-TEST-0004", "second")])
        .expect_err("second revoke must fail");
    assert!(
        format!("{err:?}").contains("AttestationRevoked"),
        "expected AttestationRevoked, got {err:?}"
    );
}

#[test]
fn foreign_signer_cannot_touch_anothers_attestation() {
    let (mut svm, issuer) = setup();
    let attacker = Keypair::new();
    svm.airdrop(&attacker.pubkey(), 10_000_000_000).unwrap();
    send(&mut svm, &issuer, &[issue_ix(&issuer, "INV-TEST-0005", Verdict::Allow, PACK_HASH)])
        .expect("issue must succeed");
    // The attacker's PDA (derived from THEIR key) is a different, empty
    // account — revoke against it must fail, not touch the issuer's slot.
    let err = send(&mut svm, &attacker, &[revoke_ix(&attacker, "INV-TEST-0005", "hostile")])
        .expect_err("foreign revoke must fail");
    assert!(
        format!("{err:?}").contains("NotInitialized") || format!("{err:?}").contains("Foreign"),
        "expected an auth error, got {err:?}"
    );
    let att = fetch(&svm, &attestation_pda(&issuer.pubkey(), "INV-TEST-0005"));
    assert!(!att.revoked, "the issuer's attestation must remain untouched");
}

#[test]
fn oversized_asset_id_fails() {
    let (mut svm, payer) = setup();
    let long_id = "X".repeat(65);
    let err = send(&mut svm, &payer, &[issue_ix(&payer, &long_id, Verdict::Allow, PACK_HASH)])
        .expect_err("oversized asset_id must fail");
    assert!(
        format!("{err:?}").contains("AssetIdTooLong"),
        "expected AssetIdTooLong, got {err:?}"
    );
}
