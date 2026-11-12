---
name: nw-jtbd-core
description: Load when turning a request into promises, job stories or scenario titles.
user-invocable: false
disable-model-invocation: true
---

# Promises from a request

A promise is one outcome the request asks for: what an actor can do or see. Tests, slices and the closing statement all use these promises.

## 1. Decide before writing

1. Split the request into sentences. Mark each as an outcome, a reason or a constraint.
2. Write one promise per outcome sentence, in the request's own meaning. Add no input class, surface, failure mode or quality it does not state; drop none it states.
3. Map every request sentence to a promise or to a stated reason, and every promise back to a request sentence. A sentence with neither is a defect: fix it now.
4. Name the actor and the observable result in the actor's words: "Customer sees the order confirmed with an order number". Name no class, function, file, table or internal task.
5. Use job-story form when the situation matters: `When <situation>, I want to <capability>, so I can <outcome>`. Fill situation and outcome from the request; no UI element or technology.
6. Write a benefit, motivation or emotion only when the request or the human supplied it; else leave it out, write `Proposal: ...`, or for emotion "not supplied".
7. Keep a stated behaviour as stated. Lifecycle, failure or recovery ideas the request does not call for go under "Suggestions" in the closing statement, never in a promise or the diff.
8. Leave delivered behaviour as it is: no re-slice, rewrite or re-promise unless the request asks.
9. Mark an unconfirmed assumption `Open assumption`. It never appears as a requirement in a promise, an assertion or the closing statement.
10. Call an example "supplied" or "observed" only when its concrete stimulus and outcome were supplied or observed; else label it `Proposal`.

## 2. Write the scenario

Promise, then acceptance condition, then scenario (Given context, one When action, Then observable outcome). Use the request's concrete values (`$100.00`, `'Electronics'`); when none was supplied, label your value `Proposal`.

Title the scenario by what the user achieves. Rewrite any title holding a class, method, file or protocol term:

| Wrong | Right |
|---|---|
| FileWatcher triggers TreeView refresh | Dashboard updates in real time |
| Validator accepts JSON | Customer's valid order is accepted |

## 3. Closing statement

Lead with delivered behaviour, then gaps, then suggestions. State each promise in the user's words as what the user can now do or see; none names only a mechanism. Claim no motivation the request did not supply. Never say every outcome is covered while a request sentence has neither a test nor a stated gap.

## 4. Self-check

1. Each request outcome sentence has one promise; each reason sentence is kept as a reason; nothing added or dropped.
2. Each promise has an actor and an observable result in the actor's words.
3. No unsupplied benefit or emotion, or it is marked Proposal.
4. No scenario title with a class, method, file or protocol term.
5. No open assumption written as a requirement; no proposed example presented as supplied.
