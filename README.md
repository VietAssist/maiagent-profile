# MaiAgent Hermes Profile

Local Hermes profile distribution for Mai, VietAssist's bilingual assistant for Vietnamese professionals working with Western clients.

## Install

```bash
tmp=$(mktemp -d)
curl -fsSL https://github.com/VietAssist/maiagent-profile/archive/refs/tags/v1.0.6.tar.gz \
  | tar -xz --strip-components=1 -C "$tmp"
hermes profile install "$tmp" --name maiagent --alias --force -y
```

Run it with:

```bash
maiagent chat
```

## Contents

- `distribution.yaml` - Hermes distribution manifest
- `SOUL.md` - Mai system prompt, copied from `MAI-SYSTEM-PROMPT.md`
- `config.yaml` - minimal model/tool config for this machine
- Browser automation is enabled for CLI and Telegram through Hermes' local,
  headless browser tools. Private-network browsing and real-profile access
  remain disabled.
- `plugins/` - MaiAgent commands, including `/connect_chatgpt`; a successful
  ChatGPT/Codex connection selects `gpt-5.6-luna` with `max` reasoning
- `skills/` - 38 Mai skill folders

The distribution does not ship credentials, memories, sessions, logs, or runtime state.
