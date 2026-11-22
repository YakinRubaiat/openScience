# Images

Place image assets in this directory.

## Naming Convention

- Use kebab-case: `architecture-overview.svg`
- Group by type: `screenshots/`, `diagrams/`, `logos/`

## Optimization

Before committing:
- **PNG/JPG**: compress with [ImageOptim](https://imageoptim.com) or `oxipng -o 4`
- **SVG**: minimize with `svgo --pretty=false`

## Referencing

```markdown
<!-- In a docs page -->
![Alt text](assets/images/screenshot.png)
```

## Placeholders

`banner.png` is currently a placeholder text file. Replace it with an actual image, then remove the placeholder content and this note.
