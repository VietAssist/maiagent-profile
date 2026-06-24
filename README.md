# MaiAgent Hermes Profile

Local Hermes profile distribution for Mai, VietAssist's bilingual assistant for Vietnamese professionals working with Western clients.

## Install

```bash
hermes profile install https://github.com/VietAssist/maiagent-profile.git --name maiagent --alias --force -y
```

Run it with:

```bash
maiagent chat
```

## Contents

- `distribution.yaml` - Hermes distribution manifest
- `SOUL.md` - Mai system prompt, copied from `MAI-SYSTEM-PROMPT.md`
- `config.yaml` - minimal model/tool config for this machine
- `skills/` - 38 Mai skill folders

The distribution does not ship credentials, memories, sessions, logs, or runtime state.
