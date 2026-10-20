# Formative evaluation analysis template

> **No study results are included in this template.** Complete it only after sessions have been conducted and
> observations have been reviewed. Do not fill unknowns with estimates or create illustrative participant
> values. Keep raw notes in approved restricted storage; this document should contain de-identified summaries.

## Study record

- Study dates: `[enter dates or omit if sensitive]`
- Participants recruited / sessions completed: `[n / n]`
- Recruitment and relevant experience summary (broad, non-identifying): `[enter]`
- Device/browser and setting: `[enter]`
- Backend/model version if known: `[enter]`
- Protocol changes, interruptions, or missing observations: `[enter]`
- Data exclusions and reasons: `[enter without identifying details]`

## Data preparation

Use the rows in `task_observation_sheet.csv`; one row represents one participant-task attempt. Validate that
participant IDs are pseudonyms and that no names, employer identities, contact information, actual candidate
information, or resume text are present. Keep `not-attempted` separate from `not-complete`. Preserve `NA` for
unrecorded time rather than interpreting it as zero. Note facilitator prompts and protocol deviations. Do not
silently discard incomplete tasks or inconvenient observations.

Recommended completion-status values:

- `complete-unaided` — observable criteria met without facilitator help.
- `complete-assisted` — criteria met after help.
- `partial` — some criteria met but not all.
- `not-complete` — attempted and abandoned or unable to meet criteria.
- `not-attempted` — not presented or declined.

Count errors consistently with the plan: observable slips/missteps, not reasonable alternate paths. Keep error
counts separate from error descriptions and record recovery. Use the `errors` CSV field as a numeric count plus
optional short de-identified codes (for example `2; E1,E3`), or use a separate analysis copy with clearly named
columns. Do not embed sensitive participant quotations in the CSV.

## Task completion rate

For each task, calculate:

`completion rate = (complete-unaided + complete-assisted) / attempted participants × 100`

Also report **unaided completion** separately:

`unaided completion rate = complete-unaided / attempted participants × 100`

Show numerator, denominator, and count alongside every percentage (for example, `x/n`; do not insert a sample
value here). Exclude `not-attempted` from the denominator and report how many were not attempted. Do not pool
all tasks into one number without also showing task-level results. Describe success against the observable
criteria in the plan, not whether a participant chose the same candidate or score as the researchers.

| Task | Attempted n | Unaided complete n | Assisted complete n | Partial n | Not complete n | Not attempted n | Completion rate | Notes |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| T1 | | | | | | | | |
| T2 | | | | | | | | |
| T3 | | | | | | | | |
| T4 | | | | | | | | |
| T5 | | | | | | | | |
| T6 | | | | | | | | |
| T7 | | | | | | | | |

## Median task completion time

For each task, calculate the median in seconds among participants who completed it. State whether assisted
completions are included; preferably show unaided and assisted groups separately when the numbers permit.
Report the number of observations used (`n`) and the range or interquartile range for context. Keep incomplete
task elapsed times separate from completion time. If the sample is too small or the times are not comparable,
report individual de-identified values or a qualitative summary only, consistent with the consent and privacy
plan. Do not treat a lower time as better if it came with more errors or less understanding.

| Task | Median completed time (s) | n | Assistance grouping | Range / IQR | Context |
|---|---:|---:|---|---|---|
| T1 | | | | | |
| T2 | | | | | |
| T3 | | | | | |
| T4 | | | | | |
| T5 | | | | | |
| T6 | | | | | |
| T7 | | | | | |

## Error frequency and assistance

Summarize observed errors by task and concise error category. A useful denominator is attempted tasks; show raw
counts as well as any rate. Distinguish an error opportunity from an error event and define categories before
counting. Report recoverable errors, unrecovered errors, and facilitator assistance separately. Do not infer
carelessness, skill, or intent from a misstep.

| Task / category | Error events | Participants affected | Recovered? | Assistance frequency | Evidence / de-identified note |
|---|---:|---:|---|---:|---|
| | | | | | |

## SUS scoring

Use only complete ten-item SUS questionnaires. For odd items (1, 3, 5, 7, 9), subtract 1 from the response.
For even items (2, 4, 6, 8, 10), subtract the response from 5. Sum the ten adjusted values and multiply by
2.5 to produce the 0–100 SUS score. This is a scale score, not a percentage. Do not impute missing answers.

Report the number of complete questionnaires, the distribution (for this small study, median and range are
usually more transparent than only a mean), and item-level response patterns if useful. SUS is a perceived
usability measure; it does not measure fairness, accuracy, trustworthiness, or suitability for hiring. Do not
interpret a small formative sample against a benchmark as proof of success or generalize to a population.

- Complete SUS questionnaires: `[n]`
- Missing/incomplete SUS questionnaires: `[n; no imputation]`
- Summary chosen and rationale: `[enter]`
- Item-level observations: `[enter or state not analyzed]`

## Qualitative theme analysis

1. Familiarize yourself with de-identified observation notes and optional consented quotations.
2. Code concrete interaction evidence (hesitation, repeated action, misinterpretation, recovery, unexpected
   outcome, request for help) before making broader interpretations.
3. Group related codes into candidate themes, keeping themes tied to interface behavior and task context.
4. Review themes against the source notes; record contradictory cases and observations that do not fit.
5. If multiple researchers are available, compare coding and discuss differences. Do not claim statistical
   intercoder reliability from an informal discussion.
6. For each theme, document supporting task IDs/participant pseudonyms, counterexamples, severity/impact, and
   a possible design response. Use de-identified excerpts only when consent permits.

| Theme | Observed behavior / evidence | Task(s) | Counterexample or uncertainty | Potential design response |
|---|---|---|---|---|
| | | | | |

Separate **observation** (“participant reopened the explanation twice”) from **interpretation** (“the label may
not reveal the distinction clearly”). Perceived trust or fairness is a participant perception, not evidence of
model validity or fairness.

## Limitations and reporting guidance

Report the small convenience/formative sample, recruitment channel, relevant experience mix, study setting,
devices, protocol deviations, task wording, backend availability, and any missing data. Note that participants
used synthetic fixtures and that the results may not transfer to real hiring workflows or sensitive documents.
The app’s scores can be affected by extraction quality, finite vocabulary coverage, semantic-model behavior,
and possible model bias. This usability study cannot establish algorithmic fairness, accuracy, predictive
validity, accessibility conformance in all assistive technologies, legal compliance, or employment outcomes.

Do not fabricate values, use synthetic fixture outcomes as participant findings, or claim population-wide
usability. State plainly that the tool is human decision support and that a person must make hiring decisions.
Include only analyses actually conducted and label exploratory analyses as such.

## Summary for design iteration

- Issues to address first (evidence and impact): `[enter after study]`
- Questions needing follow-up evaluation: `[enter after study]`
- Changes made after the study: `[enter after implementation; do not imply validated until retested]`
