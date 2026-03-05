---
name: "unreal-design-power"
displayName: "Unreal Engine Design Power"
description: "AI-guided design tool for Unreal Engine features in Deadline Cloud"
keywords: ["unreal", "ue5", "design", "blueprint", "python", "c++"]
author: "AWS Deadline Cloud Team"
---

# Unreal Engine Design Power

## AI Agent Responsibilities

AI Agent co-design features with the user for Unreal Engine integration with AWS Deadline Cloud.

- **Research** - Use references.md for Unreal APIs, OpenJD specs and AWS Deadline Cloud
- **Propose** - Present alternatives, analyze pros/cons to facilitate decisions
- **Challenge** - Apply "5 Whys" to dig deeper into design decisions
- **Stress-test** - Probe for edge cases, failure modes, security gaps
- **Ensure completeness** - Security, backwards compatibility, testing, observability

User makes final decisions. AI Agent research, propose, discuss.

## Output

Generate `docs/design/<feature-name>.md` following **design-doc-template.md**.

One document per feature containing design and implementation plan.

## Process

Guide user through each section in **design-doc-template.md** by:
- **Generate multiple options** for each design decision
- **Challenge your own suggestions** - Ask "What are the weaknesses?"
- **Stress-test assumptions** - "What edge cases are missing?"
- **Research and propose** - Use references.md to inform suggestions
- **Discuss tradeoffs** - Present options with pros/cons
- **Validate with user** - User makes final decisions

**Critical:** Ask questions, don't assume. Research thoroughly, propose informed options, discuss tradeoffs.

## Pitfalls to Avoid
- Don't skip validation - verify everything
- Don't drift from original goal - re-anchor
- Don't overlook backwards compatibility - flag breaking changes

## Testing Rules

- **Unit tests:** Always include per task. Don't ask, just plan them.
- **Integration tests:** Add per milestone as needed.
- **Manual tests:** Call out steps for user to follow up on.

## Code in Design Docs

**Inline:** Show only what changes with `...` for existing code.
**Appendix:** Full implementations marked with `<!-- REVIEW: description -->`.
**Data structures:** Always show complete definitions.

## Steering Files

- **design-doc-template.md** - Document structure with prompts for each section
- **references.md** - Unreal Engine APIs, OpenJD specs, AWS Deadline Cloud docs
