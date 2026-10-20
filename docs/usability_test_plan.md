# Resume Screener formative usability study plan

## Study status

This is a protocol for a study that has not yet been conducted. It contains no participant data or findings.
Use a fresh copy of the prototype and only the synthetic files in `docs/test_dataset/` during sessions.

## Objectives and research questions

This small formative evaluation will identify interaction problems, unclear terminology, and unmet information
needs in the existing screening workflow. It is intended to guide iteration, not to validate hiring outcomes.

Research questions:

1. Can participants enter a role, add and manage files, configure matching, run screening, and locate results?
2. Do participants understand what the match score and the separate meaning/skill signals represent?
3. Can participants tell detected text evidence from model-inferred similarity and understand the limits of
   “potentially missing” skills?
4. Can participants inspect and compare candidates, change result ordering, recover from a file error, and clear
   the page session without undue assistance?
5. Which terms, controls, or status messages cause hesitation, errors, or mistaken expectations?

Do not frame the study as testing whether the algorithm is fair, accurate for hiring, or predictive of job
performance. A five-to-eight-person formative sample cannot establish population-wide usability, fairness,
validity, or hiring effectiveness.

## Participants and recruitment

Aim for approximately **5–8 participants**, adjusting to project constraints. Recruit adults who can plausibly
review recruitment materials, such as people with recruiting, hiring, HR, career-services, or relevant academic
research experience. Include a range of familiarity with resume screening and automated decision-support tools.
Record experience in broad categories rather than collecting employer or candidate details. Participation is
voluntary; avoid recruiting anyone whose relationship with the facilitator makes refusal difficult. Do not
require access to participants’ real resumes, employee records, or candidate files. Do not describe this sample
as representative of recruiters or applicants.

## Materials and setup

- Use the app’s normal React frontend and FastAPI backend. The backend must be available before a session.
- Use only synthetic job descriptions and resumes in `test_dataset/`. The data are fictional task fixtures, not
  examples of real people and not ground truth for a hiring decision.
- Ensure the sample folder includes three readable resumes (strong, partial, and vocabulary-missing examples),
  plus an empty TXT and malformed PDF/DOCX for upload-error behavior.
- Use a dedicated browser profile or clear the screening session between participants. Do not use browser
  extensions that capture form contents. Keep the test computer private.
- Obtain separate, explicit consent before any screen/audio recording. If recording is not needed, take
  de-identified notes only.

## Representative tasks

Read one task at a time. Do not tell participants which resume is expected to rank highest, what score to expect,
or which control to use unless the participant asks for help. Participants may think aloud if they are
comfortable; silence is acceptable.

| ID | Participant task | Observable success criteria |
|---|---|---|
| T1 | “Prepare a screening session for the example backend role in the study folder.” | Loads the supplied job description into the job-description field. No specific wording or score is expected. |
| T2 | “Add the resume files in the study folder. Review the selected list, remove one file, and then add it again.” | Adds multiple files, identifies the selected-file list, removes the chosen item, and restores it. Record any invalid/unreadable status participants notice; do not explain it first. |
| T3 | “Set the two matching signals to contribute equally. Tell me what you expect this setting to change.” | Sets the slider to the equal-weight point and describes, in their own words, that it changes the blend/ranking when screening is run. Do not judge their wording as a technical exam; record misunderstandings. |
| T4 | “Run screening on the current files and tell me what the interface reports about processing.” | Starts screening, waits for completion, and locates selected/successful/failed counts and any file-specific error feedback. Do not imply that all files must succeed. |
| T5 | “Choose one result and explain what information you can learn about its match.” | Opens a candidate explanation and distinguishes at least one text-detected skill from meaning similarity, or explicitly reports that the distinction remains unclear. |
| T6 | “Compare two results, then change how the list is ordered.” | Selects two candidates, locates the comparison, and changes sort using a supported metric. Do not prescribe a preferred candidate or sort order. |
| T7 | “Finish this session and leave the page ready for another set of materials.” | Uses the session-clearing control, confirms the action after reading its prompt, and verifies the visible job/resume/results state is cleared. |

For T2, include the empty and malformed files with the readable fixtures so participants encounter real validation
feedback. The participant is not expected to repair these files. Record whether the error makes the next step
clear. T1–T7 can be shortened or split if the session is too long; record any protocol changes.

## Neutral facilitator script

### Welcome and consent

“Thank you for taking part. We are evaluating this prototype, not your ability. Some controls or messages may be
unclear; that is useful feedback. There are no right or wrong answers. Please use only the synthetic study files.
You may skip a question, pause, or stop at any time. We will record task observations under a pseudonym. We will
not collect real candidate documents or make hiring decisions from this session. May I take de-identified notes?
May I record the screen/audio? Recording is optional and requires your separate agreement.”

Do not proceed until consent is documented according to the project’s approved process. Do not promise ethics
approval or legal compliance unless the responsible institution has granted it.

### Before tasks

“Please work through each scenario as you normally would. If you are comfortable, say what you are looking for
and what you expect to happen. I will try not to guide you. You can ask for help at any time; I will note when
help is given.”

### During tasks

Use neutral prompts only when needed: “What are you looking for now?”, “What would you expect to happen next?”,
or “Please continue in whatever way makes sense to you.” If the participant asks how to proceed, first ask,
“What would you try if I were not here?” If they remain blocked, provide the minimum help needed, record the
exact assistance, and continue without treating the task as an unaided success. Do not praise a particular
candidate, score, interpretation, or choice.

### Close

“Thank you. What, if anything, felt unclear or harder than expected? Is there anything you would change? We will
analyze only de-identified observations. The prototype does not make hiring decisions and this session does not
evaluate fairness or job performance.”

## Measurement and recording

Use one row per participant per task in `task_observation_sheet.csv`. Assign a random pseudonym (for example,
`P-04`); do not put names, contact information, employer names, or resume details in the sheet.

- **Completion status:** use `complete-unaided`, `complete-assisted`, `partial`, `not-complete`, or `not-attempted`.
- **Completion time:** start when the task is read and the participant can act; stop at the task’s observable
  success point or when the task is abandoned. Record seconds as a number. Use `NA` if not attempted; record
  elapsed time to stop/abandon for incomplete tasks and label it in notes.
- **Errors:** count observable slips or recoverable missteps related to the task (wrong control, accidental
  removal, repeated invalid action, misinterpretation that changes the action). In the notes, briefly describe
  each error and whether the participant recovered. Do not count a reasonable alternative path as an error.
- **Assistance required:** record `none` or a concise description of the prompt/help and when it was needed.
- **Observed usability issues:** describe observable behavior and interface cues, not assumptions about
  participants’ ability, motivation, protected traits, or intent.
- **Notes:** include relevant quotes only if de-identified and consented; distinguish direct observation from
  facilitator interpretation. Avoid copying any candidate data into notes.

Use a consistent start/stop rule and the same task wording for all participants. If a task is interrupted, note
the interruption and exclude or separately report its time rather than silently treating it as comparable.

## Consent, privacy, and anonymization

Explain the study purpose, activities, optional recording, voluntary nature, withdrawal process, data use,
retention/deletion plan, and researcher contact before consent. Follow institutional review and data-protection
requirements that apply to the project; this document is not legal advice or a compliance certification.

Use synthetic files only. Store consent records separately from observations, restrict access to the facilitator
and approved research team, use pseudonyms, and remove identifying details from notes and quotations. Set and
follow a retention/deletion date before recruitment. Delete recordings after verified transcription if they are
not required longer; store any retained recording in approved protected storage. Do not include identifiable
participant information, actual candidate data, or raw resume contents in reports or this repository. Report
only aggregated or carefully de-identified observations. Participation and study responses must not affect
employment decisions.

## Interpretation boundaries

Report the sample size and relevant participant experience, setting, device/browser, task wording, backend/model
version if known, and protocol deviations. This small formative study can reveal issues to investigate; it cannot
establish population-wide usability, algorithmic fairness, validity, accuracy, or suitability for employment
decisions. Do not turn participant reactions or task completion into claims about model fairness or hiring
quality.
