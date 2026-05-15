// Package productionapp — toy minimal signup feature for the polyglot pilot.
//
// Composition root: constructs the in-memory registry and audit log, exposes
// Signup (driving operation) and CaptureUniverse (state inspection at
// port-exposed slots). Real-feature shape: in-process domain + driven ports
// (here both in-memory).
//
// Universe slots exposed:
//   - "registry.users" : []UserRecord
//   - "audit.events"   : []AuditEvent
//
// Internal field names are NOT part of the universe — refactoring internals
// stays GREEN.
package productionapp

import (
	"errors"
	"fmt"
	"strings"
)

// UserRecord is one entry in the in-memory registry.
type UserRecord struct {
	Email string
}

// AuditEvent is one entry in the in-memory audit log.
type AuditEvent struct {
	Type  string
	Email string
}

// DuplicateSignupError signals an already-registered email.
type DuplicateSignupError struct {
	Email string
}

func (e *DuplicateSignupError) Error() string {
	return fmt.Sprintf("duplicate signup rejected: %s", e.Email)
}

// ErrEmptyEmail is returned when Signup receives a blank email.
var ErrEmptyEmail = errors.New("signup: email must be non-empty")

// Options reserves space for future port-swap hooks (clock, RNG, paid APIs).
// The toy feature uses none.
type Options struct{}

// SignupInput is the driving-port input shape for Signup.
type SignupInput struct {
	Email string
}

// App is the production composition root for the toy signup feature.
type App struct {
	users  []UserRecord
	events []AuditEvent
}

// New constructs an App with empty in-memory state.
func New(_ Options) *App {
	return &App{
		users:  []UserRecord{},
		events: []AuditEvent{},
	}
}

// Signup is the driving port — registers a user by email. Returns
// *DuplicateSignupError when the email already exists, ErrEmptyEmail when
// the input is blank.
func (a *App) Signup(in SignupInput) (UserRecord, error) {
	email := strings.ToLower(strings.TrimSpace(in.Email))
	if email == "" {
		return UserRecord{}, ErrEmptyEmail
	}
	for _, u := range a.users {
		if u.Email == email {
			return UserRecord{}, &DuplicateSignupError{Email: email}
		}
	}
	record := UserRecord{Email: email}
	a.users = append(a.users, record)
	a.events = append(a.events, AuditEvent{Type: "UserSignedUp", Email: email})
	return record, nil
}

// CaptureUniverse returns a snapshot of the requested universe slots.
// Returned slices are defensive copies so test assertions cannot mutate
// production state by accident.
//
// The snapshot uses []interface{} for slice-shaped slots so the generic
// statedelta predicates (AppendedWithItem / PrependedWithItem) can DeepEqual
// against them without type-juggling.
func (a *App) CaptureUniverse(keys []string) map[string]interface{} {
	snapshot := make(map[string]interface{}, len(keys))
	for _, key := range keys {
		switch key {
		case "registry.users":
			out := make([]interface{}, len(a.users))
			for i, u := range a.users {
				out[i] = u
			}
			snapshot[key] = out
		case "audit.events":
			out := make([]interface{}, len(a.events))
			for i, e := range a.events {
				out[i] = e
			}
			snapshot[key] = out
		default:
			// Unknown slot — leave as nil so state-delta sees the absence
			// explicitly rather than silently fabricating a value.
			snapshot[key] = nil
		}
	}
	return snapshot
}
