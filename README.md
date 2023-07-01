# sceptre-amplify-config-generate-hook
Hook that will build an Amplify configuration by querying AWS for cognito
information.

:warning: This is hook super opinionated, and needs to be generalized.

## Overview

A brief description. Be clear about the purpose of the hook,
its capabilities and limitations.

## Installation

Installation instructions

To install directly from PyPI
```shell
pip install sceptre-hook-template
```

To install from the git repo
```shell
pip install git+https://github.com/Sceptre/sceptre-hook-template.git
```

## Usage/Examples

Use the hook with a [hook point](https://docs.sceptre-project.org/latest/docs/hooks.html#hook-points)

```yaml
hooks:
  hook_point:
    - !custom <args>
```

## Example

```yaml
hooks:
  before_create:
    - !custom "HelloWorld"
```
