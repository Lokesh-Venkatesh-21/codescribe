# LangGraph Agent Workflow

```mermaid
flowchart TD
    Start["PR Diff"]
    Parse["Parse Changed Files"]
    Symbols["Detect Functions and Classes"]
    Intelligence["Classify, Score Risk, Scan Security"]
    Generate["Generate Summary and Documentation"]
    Review["Create Review Decision and Comments"]
    Validate["Validate Comment-Only Changes"]
    Publish["Publish Enabled Outputs"]

    Start --> Parse
    Parse --> Symbols
    Symbols --> Intelligence
    Intelligence --> Generate
    Generate --> Review
    Review --> Validate
    Validate --> Publish
```

The graph keeps the PR review path linear and auditable: understand the diff, generate grounded
analysis, validate branch edits, then publish only the outputs the repository enabled.
