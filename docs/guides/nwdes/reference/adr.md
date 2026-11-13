# adr

Ratify a delivered ADR as Accepted. The operator decides; nwdes records who decided and when. Run the command from the top level of the checkout, after the feature that produced the ADR is integrated.

```sh
nwdes adr accept --key 001 --by "Operator Name"
```

- `--key KEY` names the ADR file to ratify, for example `001` or `NWD-004`. Each key of the project register is one file.
- `--by NAME` is required. It is the operator who decides the ratification; the record names it as given. nwdes cannot verify that a person, rather than a tool, supplied the name.
- The ADR file changes in one place: its `Status: Proposed` line becomes `Status: Accepted`. Its key, title, sections and every other byte stay as they were.
- The ratification record is written beside the ADR files as `ADR-KEY.ratification.json`. It holds the key, the operator name and the UTC time of the ratification in whole seconds, in the form `YYYY-MM-DDTHH:MM:SSZ`. The record is written before the status line changes.
- An ADR that already reads `Status: Accepted` is left unchanged; the command prints `UNCHANGED` with `(already Accepted)` and writes nothing.
- An ADR file whose layout is not the nwdes layout is refused with `AdrForeignLayout` and left unchanged. Restore the layout by hand, then run the command again.
- An ADR whose status supersedes it is refused with `AdrTransitionInvalid`. An unknown key is refused with `DanglingReference`.
- Without `--by`, or with a blank `--by`, the command is refused with `MissingFact` or `PartInvalid` and writes nothing.

The ADR directory is the `adr.directory` setting of the global and repository configuration tiers. A feature-tier file that declares `adr` is refused as malformed by every command that reads that tier, because the key is repository-wide. This command does not read feature tiers, so it does not report that refusal itself; the refusal appears in the feature's design commands. The feature handoff keeps its copy of each declaration's status until the next design close; the ADR file is the record that this command changes.

Every refusal prints WHAT, WHY and HOW. A refusal found before anything is written leaves every file unchanged.

A register directory that is a symlink is refused with `DestinationInvalid` for every status before the register is read. An ADR file that is a symlink is refused with `DestinationInvalid` for every status after the register has been read and before the ratification decision and any write; the verb reads the file's bytes before that refusal, and nothing is written through the link. The refusal is pinned by an acceptance test.

The ratification record is an unauthenticated declaration. It states the name given to `--by` and a UTC time. It is not a signature, and it proves neither that the command ran nor that a person made the decision: the name is free text, and any process or person that can write the ADR directory can write, edit or delete the record, or run the command with any name. After a crash between the two writes, the status line stays Proposed and a rerun overwrites the record with the rerun's name and time, so the interrupted attempt's entry is lost. When two ratifications of one key run at the same moment, the record that survives names whichever process wrote last, and the other ratifier leaves no trace and no error. Read the record as the claim of its author, not as evidence of human authorization.

Not tested: two ratifications of one key at the same moment, and an interruption between the two writes; both outcomes are described above and no test reproduces them. The write order (record first, status line last) is checked by the Quint model `models/adr_ratification_order.qnt` and its mutant; no test stops the process between the writes or runs two ratifications at once.
