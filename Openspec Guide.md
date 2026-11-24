# OpenSpec

OpenSpec is a spec-driven development tool that organizes proposed software changes into requirements, technical design, and implementation tasks. Its file-based artifacts help coding assistants implement and verify changes consistently.

## 1. Install OpenSpec using npm

Prerequisite: Node.js and npm are already installed. Check the [current Node.js requirement](https://openspec.dev/docs/installation) for your OpenSpec version.

Run in **PowerShell** or your IDE terminal:

```powershell
npm install -g @fission-ai/openspec@latest
openspec --version
```

Useful npm maintenance commands:

```powershell
npm install -g @fission-ai/openspec@latest  # Upgrade
npm list -g --depth=0                      # List globally installed packages
npm uninstall -g @fission-ai/openspec      # Uninstall
```

## 2. Initialize OpenSpec for Codex

From the **root of your project**:

```powershell
cd 'C:\Projects\MyApp'  # Replace with your actual project directory
openspec init --tools codex
```

For a project that is already initialized, refresh its generated Codex skills:

```powershell
openspec update
```

Codex uses **skills** invoked in Codex chat with a `$` prefix, such as `$openspec-propose`. These are **not PowerShell commands**. OpenSpec CLI commands such as `openspec list` are run in PowerShell.

## 3. Enable the optional Verify skill

The default **core** profile includes `explore`, `propose`, `apply`, `update`, `sync`, and `archive`; **verify is not included by default**.

Run in PowerShell:

```powershell
openspec config profile
```

In the interactive selector, retain the core workflows and **select `verify`**. Save the selection. Then, from each OpenSpec project root:

```powershell
openspec update
Test-Path '.agents\skills\openspec-verify-change\SKILL.md'
```

The final command should return `True`. Restart the Codex chat/session so it discovers the new skill. Profile selection is machine-level; generated skills must be updated in each project.

## 4. Lifecycle: Explore → Propose → Apply → Verify → Archive

The following `$...` examples are entered in **Codex chat in your IDE**, not in the terminal. Always name the change explicitly once it exists, particularly when multiple changes are active.

### A. Explore — clarify the idea (optional)

```text
$openspec-explore Explore HTTP request parameter logging.
```

Explore is for investigation and trade-offs. It does not automatically create the complete change plan.

### B. Propose — generate the change plan (required before applying)

```text
$openspec-propose Add HTTP request parameter logging with sensitive-value redaction.
```

Review `proposal.md`, `specs/`, `design.md`, and `tasks.md`. Refine them as necessary before implementation. For an existing change, edit the Markdown directly or use:

```text
$openspec-update-change Add correlation IDs to "add-request-logging".
```

### C. Apply — implement the tasks

```text
$openspec-apply-change
Apply the change named "add-request-logging".
Implement only the first incomplete task in tasks.md.
Run relevant tests, update that task's checkbox if successful,
and stop for review. Do not proceed to another task.
```

Repeat for each task, explicitly specifying the task number if preferred. A one-task-at-a-time approach is an **instruction to Codex**, not a dedicated OpenSpec CLI flag.

### D. Verify — compare implementation with the plan

```text
$openspec-verify-change add-request-logging
```

Resolve findings and rerun verification as necessary. Also run your project's own test/build commands; skill-based verification does not replace automated testing or code review.

### E. Archive — complete and preserve the change

```text
$openspec-archive-change add-request-logging
```

Archive normally synchronizes accepted requirements into `openspec/specs/` and moves the change into `openspec/changes/archive/`. Inspect the resulting diff and commit it with the application code through your normal Git workflow.

## 5. Folder structure

```text
MyApp/
├── .agents/
│   └── skills/
│       ├── openspec-explore/SKILL.md
│       ├── openspec-propose/SKILL.md
│       ├── openspec-update-change/SKILL.md
│       ├── openspec-apply-change/SKILL.md
│       ├── openspec-verify-change/SKILL.md  # Optional: enable via profile
│       └── openspec-archive-change/SKILL.md
├── openspec/
│   ├── config.yaml                         # Project-wide OpenSpec configuration
│   ├── specs/                              # Accepted/current system requirements
│   │   └── request-logging/
│   │       └── spec.md
│   └── changes/
│       ├── add-request-logging/            # Active change
│       │   ├── .openspec.yaml              # Change schema/workflow metadata
│       │   ├── proposal.md                 # WHY: motivation, scope, impact
│       │   ├── design.md                   # HOW: architecture and decisions
│       │   ├── tasks.md                    # WORK: implementation/test checklist
│       │   └── specs/                      # WHAT: proposed requirement deltas
│       │       └── request-logging/
│       │           └── spec.md
│       └── archive/                        # Completed changes (dated folders)
└── src/                                    # Application code (illustrative)
```

> Exact generated files depend on OpenSpec version, profile, and schema. For example, `openspec/specs/` may initially be empty, and the optional Verify skill appears only after it is enabled and the project updated.

### What each change artifact means

| Artifact | Question answered | Typical contents |
| --- | --- | --- |
| `proposal.md` | **Why?** | Problem, motivation, scope, impact |
| `specs/<capability>/spec.md` | **What?** | Required behavior, acceptance scenarios, additions/modifications/removals |
| `design.md` | **How?** | Architecture, components, trade-offs, security decisions |
| `tasks.md` | **What work?** | Numbered implementation and testing checklist |
| `.openspec.yaml` | **Which workflow?** | Schema identifier such as `spec-driven` |

**Two specifications directories:** `openspec/specs/` describes the currently accepted system behavior. `openspec/changes/<change>/specs/` describes the **proposed changes** to that behavior. Archiving can merge the latter into the former.

## 6. Useful PowerShell commands

```powershell
openspec list                              # List active changes
openspec status --change add-request-logging
openspec validate add-request-logging --strict
openspec update                            # Refresh generated Codex skills
Get-ChildItem '.agents\skills' -Directory  # List installed project skills
git diff --check
git status
```

For multiple active changes, use a **distinct change name** in every Codex apply, verify, and archive instruction. Consider separate Git branches/worktrees for changes that might edit the same code.

## 7. Recommended working practices

1. Review and commit the planning artifacts before coding when practical.
2. Use a fresh Codex chat for implementation if the planning discussion was long; the files, not the chat, are the source of truth.
3. Apply one task at a time if you want explicit review gates.
4. Verify requirements, tests, and design adherence before archiving.
5. Review the archive/spec synchronization diff, then commit or open a pull request.

## Official references

1. [OpenSpec — Installation](https://openspec.dev/docs/installation)
2. [OpenSpec — Supported Tools (Codex skills)](https://github.com/Fission-AI/OpenSpec/blob/main/docs/supported-tools.md)
3. [OpenSpec — Profiles (enabling Verify)](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/customize/profiles.md)

