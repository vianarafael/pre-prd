# pre prd

A single-page app for indie hackers to draft product specs and instantly generate artifacts for better AI-powered development.

## What it does

Write your PRD once, export 4 files:

- `PRD.md` - Product requirements
- `.cursor/rules/instructions.mdc` - AI coding rules
- `epics.json` - High-level features
- `tickets.json` - Detailed tasks with acceptance criteria

## Quick start

```bash
bash ./start.sh
# Open http://localhost:8000
```

## Stack

FastAPI + HTMX + DaisyUI + Jinja2. No database needed.

## Features

- **Multi-tab editor**: Script, Rules, Scenes (epics), Shots (tickets)
- **Inline editing**: Add/edit/delete scenes and shots directly
- **State persistence**: Work survives tab switches and browser refresh
- **Export options**: Download zip or share via signed links

Built for developers using Cursor AI who want structured specs to guide better code generation.
