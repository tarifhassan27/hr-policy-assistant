# Pilot Note: HR Policy Assistant

## What this is

A bilingual AI assistant that answers employee questions about HR policy — grounded in a provided handbook, with citations, in English or Bangla. Runs on the Gemini free tier. No infrastructure cost.

## Recommended starting point

**Field-force or frontline staff** are the highest-value pilot group. They generate the most repetitive HR queries (leave balances, allowances, attendance rules) and have the least direct access to HR teams. A bot that handles these queries reduces HR team load while giving staff faster answers.

## How to measure success

Track two numbers over the pilot period:

1. **Query deflection rate** — what share of questions the bot answers without escalation to HR
2. **Escalation quality** — whether the queries that do reach HR are more complex than before (a sign the bot is handling the routine ones)

No new tooling needed. A simple tally kept by the HR team is enough for a 30-day pilot.

## What the bot does well

- Answers factual policy questions accurately (tested at 95% English / 100% Bangla pass rate on a 50-question blind test set)
- Refuses out-of-scope questions cleanly — 10/10 on adversarial traps
- Cites the exact handbook section so staff can verify the answer themselves
- Responds in the language the question is asked in

## Known limitations

- Knowledge is limited to whatever handbook is loaded — it cannot answer questions outside it
- Does not have memory of previous conversations across sessions
- Scores above reflect automated test-set pass rates, not manually verified accuracy
- Not suitable for sensitive HR matters (disciplinary, grievance, personal circumstances)

## Expansion path

Once the pilot shows deflection rate and user comfort, two natural next steps are:

1. Expand the handbook scope (add compensation, performance, code of conduct sections)
2. Embed into an existing internal channel (Teams, Slack, or intranet) via API

Both are straightforward extensions of the current architecture.
