//! Toy ProductionApp — minimal signup feature for the polyglot pilot.
//!
//! Composition root: constructs the in-memory registry and audit log, exposes
//! `signup` (driving operation) and `capture_universe` (state inspection at
//! port-exposed slots). Real-feature shape: in-process domain + driven ports
//! (here both in-memory).
//!
//! Universe slots exposed:
//!   - "registry.users" : Vec<UserRecord> as JSON array
//!   - "audit.events"   : Vec<AuditEvent> as JSON array
//!
//! Internal field names are NOT part of the universe — refactoring internals
//! stays GREEN.

use std::collections::BTreeMap;
use std::fmt;

use serde_json::{json, Value};

use crate::common::state_delta::Snapshot;

#[derive(Debug, Clone)]
pub struct UserRecord {
    pub email: String,
}

#[derive(Debug, Clone)]
pub struct AuditEvent {
    pub event_type: String,
    pub email: String,
}

#[derive(Debug)]
pub struct DuplicateSignupError {
    pub email: String,
}

impl fmt::Display for DuplicateSignupError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Duplicate signup rejected: {}", self.email)
    }
}

impl std::error::Error for DuplicateSignupError {}

#[derive(Debug)]
pub enum SignupError {
    Empty,
    Duplicate(DuplicateSignupError),
}

impl fmt::Display for SignupError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            SignupError::Empty => write!(f, "signup: email must be non-empty"),
            SignupError::Duplicate(d) => fmt::Display::fmt(d, f),
        }
    }
}

impl std::error::Error for SignupError {}

#[derive(Debug, Default)]
pub struct ProductionApp {
    users: Vec<UserRecord>,
    events: Vec<AuditEvent>,
}

impl ProductionApp {
    pub fn new() -> Self {
        Self::default()
    }

    /// Driving port — signup a user by email. Rejects duplicates by returning
    /// `Err(SignupError::Duplicate)`. On success: appends to registry AND
    /// appends a single `UserSignedUp` audit event.
    pub fn signup(&mut self, email: &str) -> Result<UserRecord, SignupError> {
        let normalised = email.trim().to_lowercase();
        if normalised.is_empty() {
            return Err(SignupError::Empty);
        }
        if self.users.iter().any(|u| u.email == normalised) {
            return Err(SignupError::Duplicate(DuplicateSignupError {
                email: normalised,
            }));
        }
        let record = UserRecord {
            email: normalised.clone(),
        };
        self.users.push(record.clone());
        self.events.push(AuditEvent {
            event_type: "UserSignedUp".to_string(),
            email: normalised,
        });
        Ok(record)
    }

    /// State-inspection port — return a snapshot of the universe slots
    /// requested. Snapshots are owned `serde_json::Value` copies so test
    /// assertions cannot mutate production state.
    pub fn capture_universe(&self, keys: &[&str]) -> Snapshot {
        let mut snapshot: BTreeMap<String, Value> = BTreeMap::new();
        for key in keys {
            let value = match *key {
                "registry.users" => Value::Array(
                    self.users
                        .iter()
                        .map(|u| json!({"email": u.email}))
                        .collect(),
                ),
                "audit.events" => Value::Array(
                    self.events
                        .iter()
                        .map(|e| json!({"type": e.event_type, "email": e.email}))
                        .collect(),
                ),
                // Unknown slot — return Null so state-delta sees the absence
                // explicitly rather than silently fabricating a value.
                _ => Value::Null,
            };
            snapshot.insert((*key).to_string(), value);
        }
        snapshot
    }
}
