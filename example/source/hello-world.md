---
title: Hello World
description: A personal static site generator for a simple blog
date: 2018-01-01
location: Kathmandu, Nepal
draft: false
---

## Introduction

`harmonique` is a personal static site generator for a simple blog.


### Code

Here we learn the famous hello world.

```python
def hello_world():
    print("Hello world")
```

This hello world example is the first ritualistic task in the cult of
programming.

## Links and footnotes

Links can also be specified like this:

```markdown
You can search more using [google][1] but there are
other search engines like [bing][bng] or [DuckDuckGo][duck].

[1]: https://google.com/ "Google search"
[bng]: https://bing.com/ "Bing search"
[duck]: https://duckduckgo.com "DuckDuckGo"
```

Footnotes are also very easy:

```markdown
Footnotes are references[^ref]. Manually creating reference
links can be tedious.[^1]

[^1]: https://wikipedia.org
[^ref]: This is note id
```

## Interlink

Interlinking can be used to create links between articles while
retaining the readability that is on par with the markdown syntax. The
syntax to interlink is as follows:

```markdown
[il:<slug>]	[<anchor>]
```

Slug and anchor can be separated using zero to 3 spaces. Not tabs.

The patterns and the URL template can be customized through the
`harmonique.yml` config file.

## Tables

Tables are also very easy. The syntax below will produce a table.

```markdown
| Head1 | Head2 | Head3 |
|-------|-------|-------|
| row1  | row1  | row1  |
| row2  | row2  | row2  |
```

The result:

| Head1 | Head2 | Head3 |
|-------|-------|-------|
| row1  | row1  | row1  |
| row2  | row2  | row2  |
