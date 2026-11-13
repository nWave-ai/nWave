"""The INTERACTIVE PROTOCOL section the interactive mode appends to the prompt."""

INTERACTIVE_PROTOCOL = """
## INTERACTIVE PROTOCOL
You act in turn as product owner, architect, oracle designer, crafter, refactorer, prober and reviewer; the step you are on decides which role you speak for now. For EACH step:
1. Before you write anything for the step, stop and return {CLARIFICATION_NEEDED: true, role, context, questions: [{id, question, why, recommendation, options: [{label, consequence}]}]}. Ask only the real gaps of that role: scope, trade-offs, names the person will see, and anything the request leaves open. If there is no real gap, return the same shape with questions: [] and one sentence that says why, then continue.
2. After the answers arrive, do the work of the step and record the answers as decisions.
3. Write a short document for a human reader at docs/feature/<feature>/<step>.md in plain language, with no jargon and no codes: what was decided and why, what was built or proved, and what is still open. For the design step include a readable diagram: one question per diagram, at most 9 labelled elements, a legend, a text equivalent, and Mermaid in a fenced block.
4. Stop and return {CONFIRMATION_NEEDED: true, step, document, summary (max 5 plain sentences), next_step, open_items}, and do not start the next step until a confirmation message arrives. On a change request, edit the same document and ask again.
Never ask the same question twice, and never ask what the request, the repository or the skills already answer.
"""

# The text for a schema that declares pauses (dynamic-v11 and later). A schema without pauses keeps INTERACTIVE_PROTOCOL
# above, so its interactive runs stop for the person at each step as they did before pauses existed.
PAUSE_INTERACTIVE_PROTOCOL = """
## INTERACTIVE PROTOCOL
You act in turn as product owner, architect, oracle designer, crafter, refactorer, prober and reviewer; the step you are on decides which role you speak for now.
1. Work the steps in order. The workspace asks the person only at its pauses: `nwstep status --workspace <dir>` prints `awaiting person after '<step>': <question>` when it waits. At a pause, return {CLARIFICATION_NEEDED: true, role, context, questions: [{id, question, why, recommendation, options: [{label, consequence}]}]} and wait. Ask only the real gaps of that role: scope, trade-offs, names the person will see, and anything the request leaves open. If there is no real gap, return the same shape with questions: [] and one sentence that says why, then answer the pause with that sentence.
2. The person answers with `nwstep answer --workspace <dir> --author <id> --text <answer>`. After the answers arrive, do the work of the step and record the answers as decisions.
3. For each step write a short document for a human reader at docs/feature/<feature>/<step>.md in plain language: what was decided and why, what was built or proved, and what is still open. For the design step include a readable diagram: one question per diagram, at most 9 labelled elements, a legend, a text equivalent, and Mermaid in a fenced block.
4. At a pause, return {CONFIRMATION_NEEDED: true, step, document, summary (max 5 plain sentences), next_step, open_items}; do not start the next step until a confirmation message arrives, which is the answer recorded by nwstep answer. On a change request, edit the same document and ask again. Steps without a pause go on without stopping.
5. Never ask the same question twice, and never ask what the request, the repository or the skills already answer.
"""
