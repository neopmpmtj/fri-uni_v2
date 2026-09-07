# Interview mechanics

Load this when the questioning format is unclear, the user asks to be grilled, or a round is about to mix dependent questions.

## Design tree

Treat the project as decisions with decisions hanging off them. Example: "how many apps?" before "which app owns clients?" before "does clients.email have to be unique?"

Do not ask a question whose answer depends on another question still open in this round. That later question belongs to the next round.

## Frontier rounds

The frontier is every decision whose prerequisites are already settled.

- Ask the whole frontier in one round, numbered, **5–8 questions max**.
- If more than eight independent questions are ready, pick the most load-bearing eight. The rest wait.
- After the user answers, recompute the frontier. Later rounds must clearly use earlier answers.
- Independent questions may share a round. Dependent questions must not.

One-question-at-a-time is allowed if the user asks for it. Default is a frontier round.

## Recommended answers

Every question gets one concrete recommendation and a one-line why. Recommendations exist so the user can push back. If they accept every recommendation without comment, pause once and say so: the value is in the disagreements.

Do not hide a second decision inside the recommendation.

## Facts vs decisions

| Kind | Who | Example |
| --- | --- | --- |
| Fact | Agent looks it up | Whether `docs/preliminary_project-plan.md` already lists an admin app; whether a `clients` table exists in migrations |
| Decision | User | Whether there should be a mobile app; whether price changes need a reason |

Never ask the user to recap their own files. If a fact is missing from the repo, say it is missing and ask the decision, not the fact.

## Shared understanding gate

A phase is not done when questions run out. Summarize, then wait until the user confirms they are comfortable. Then wait again for explicit go-ahead before writing that phase's document.

If the user says they are comfortable with the plan but not ready to write the file, stay in chat and do not start Phase B until they confirm the plan is settled.

## Steering

- "Ask me questions" → current phase, largest remaining gap.
- "Wrap up" → summarize, list open questions, ask whether to write docs.
- "I don't know" → park as an open question; do not invent a table or app.
- Ungrillable items (how a screen should feel) → note them as open; do not pad the round with UI guesswork. This skill does not prototype.
