# Introduction

A sad little static blog generator. Nothing fancy.

## Installation

Run:

```
pip install harmonique
```

## Example blog project

Clone/download this repository and check out the `example` directory.

## Commands


### Compile everything, including drafts

```bash
harmonique dev
```

### Compile published, skip drafts

```bash
harmonique prod
```

Append `serve` on the commands above to run the local server that
serves the output files at `localhost:8889`. The server also watches
for file changes and rebuilds. Works with both `dev` and `prod` modes.
