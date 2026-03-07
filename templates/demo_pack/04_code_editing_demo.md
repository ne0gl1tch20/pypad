# Code Editing Demo

## Python

```python
def fibonacci(n: int) -> list[int]:
    # TODO: add bounds validation
    seq = [0, 1]
    while len(seq) < n:
        seq.append(seq[-1] + seq[-2])
    return seq[:n]
```

## JavaScript

```javascript
function greet(name) {
  // FIXME: sanitize user-provided value
  return `Hello, ${name}!`;
}
```

## JSON

```json
{
  "lint": true,
  "format": "strict",
  "targets": ["py", "js", "md"]
}
```

## Search Targets

- TODO: optimize startup
- FIXME: update icon mapping
- BUG: edge-case when file is empty
