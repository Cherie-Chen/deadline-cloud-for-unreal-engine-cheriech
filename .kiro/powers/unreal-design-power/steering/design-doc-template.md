# Design Document Template

Use this template to generate `docs/design/<feature-name>.md`.
Guide user through each section. Use prompts to gather information.
Don't skip sections — mark as "N/A" with justification if not applicable.

---

# Feature Name
Status: Draft | In Review | Accepted | Implemented

## 1. Summary

One paragraph overview.

**example prompts:**
- "What is the feature in one sentence?"
- "What is the end goal?"

## 2. Motivation

Problem statement, use cases, why now.

**example prompts:**
- "What pain point does this address?"
- "Who are the users and what do they need?"
- "What happens if we don't build this?"
- "How common is this use case?"

## 3. Basic Examples

How end-users would use it.

**example prompts:**
- "What is a concrete example of the happy path"
- "What is an error case example"

## 4. System Architecture

Architecture diagram, component interactions, data flow.

**example prompts:**
- "Which components are affected?"
- "How do they communicate?"
- "What's the data flow?"
- "Any external dependencies?"

## 5. Specification

Detailed technical specification:

### 5.1 Data Structures
Complete definitions of new or modified data structures:
- OpenJD template parameters
- Configuration objects
- API request/response formats
- Internal state representations

**example prompts:**
- What data needs to be stored/transmitted?
- What are the required vs optional fields?
- What are the validation rules?
- How does this integrate with existing data structures?

### 5.2 Submitter Plugin Changes (UX/UI)
- UI modifications in Unreal Editor
- New settings or configuration options
- User workflows and interactions
- Error messages and validation

**example prompts:**
- What UI changes are needed?
- How will users configure this?
- What error messages should users see?
- How do we validate user input?

### 5.3 Job Template Changes
- New OpenJD template parameters
- Step definitions
- Environment requirements
- Path mapping rules

**example prompts:**
- What new template parameters are needed or changing?
- How do these integrate with existing templates?
- What are the default values?

### 5.4 Adaptor Changes
- Command handlers
- Render pipeline modifications
- State management
- Error handling

**example prompts:**
- What adaptor changes are required?
- How do we handle errors?

## 6. Backwards Compatibility

- Is this a breaking change?
- Impact on existing users, templates, or workflows
- Migration path for existing users

**example prompts:**
- Will existing job templates still work?
- Do users need to update anything?
- If breaking: what version bump is needed? (major/minor)

**If backwards incompatible:**
- Call out explicitly in design
- Include migration guide
- Add version bump task to implementation plan (Section 10)

## 7. Security Considerations

- Security implications
- Threat model
- Mitigation strategies
- Authentication/authorization requirements

**prompts (CRITICAL):**
- Does this handle user input? How is it validated?
- Does this access sensitive data? How is it protected?
- What are the potential attack vectors?
- How do we authenticate/authorize access?
- Are there any secrets or credentials involved?
- What happens if a malicious user tries to exploit this?

## 8. Design Choice Rationale

For each significant design decision:
- What options were considered?
- Why was this option chosen?
- What are the tradeoffs?

**example prompts:**
- What alternatives did you consider?
- Why did you choose this approach over others?
- What are the pros and cons of each option?
- What assumptions are you making?
- **Challenge mode:** What are the weaknesses of chosen approach?
- **Stress test:** What could go wrong with this design?

## 9. Observability & Monitoring

Consider whether observability needs to be implemented on the service side (AWS Deadline Cloud) vs client side.

- Metrics to track
- Logging requirements
- Alerting strategy

**example prompts:**
- What metrics indicate this feature is working correctly?
- What should we log for debugging?
- Is this client-side or service-side observability?
- Does this require changes to AWS Deadline Cloud service?

## 10. Work Required (Implementation Plan)

Break down implementation:
- **Milestones** (for large features)
- **Tasks** with clear deliverables
- **Dependencies** between tasks
- **Testing Requirements** for each task:
  - Unit tests (per task)
  - Integration tests (per milestone)
  - End-to-end tests (final milestone)
  - Manual test plan
- **Documentation** updates
- **Version bump** if backwards incompatible (see Section 6)

**example prompts:**
- What are the major milestones?

## 11. Prior Art

- Similar features in other systems
- How they're implemented
- What we can learn from them

**example prompts:**
- Have you seen this in other tools?
- How do they implement it?
- What can we learn from their approach?

## 12. Rejected Ideas

- Alternative approaches considered
- Why they were not pursued

**example prompts:**
- What other approaches did you consider?
- Why didn't you choose them?
- What would make you reconsider them in the future?

## 13. Future Iterations

- Features deferred to future releases
- Potential enhancements
- Known limitations

**example prompts:**
- What are you explicitly not doing in this version?
- What would you add in v2?
- What are the known limitations?

## Code Style

**Main sections** - Concise snippets showing changes:
```python
def existing_method(self):
    ...existing code...
    # NEW: Add feature support
    if self.feature_enabled:
        self._handle_feature()
```

**Appendix** - Full implementations with review markers:
```markdown
## Appendix: Full Code Implementations

<!-- REVIEW: New feature implementation -->

## A.1 FeatureHandler.process
\`\`\`python
def process(self, data: dict) -> None:
    """Complete implementation..."""
\`\`\`
```
