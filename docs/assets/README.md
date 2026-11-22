# openScience Documentation Assets

This directory contains CSS, JavaScript, and image assets for the documentation site (Jekyll + just-the-docs).

## Structure

```
assets/
├── css/
│   └── custom.css       # Custom styles extending just-the-docs
└── images/
    ├── README.md        # This file — placeholder for the banner image
    └── (add .png/.svg here)
```

## Adding Images

1. Add files to `images/` (PNG, SVG, JPG)
2. Reference from docs pages with relative paths:

```markdown
![Alt text](assets/images/banner.png)
```

## Customizing Styles

Edit `css/custom.css` to override just-the-docs defaults. The file includes:

- Brand colors (CSS custom properties)
- Category badges for agent docs
- Code block styling
- Table and card styles
- Print and dark-mode adjustments

## Favicon

Place `favicon.ico` in the site root and reference it in `_config.yml`:

```yaml
# _config.yml
favicon: /favicon.ico
```

## Notes for Contributors

- Optimize images before committing (ImageOptim, oxipng, svgo)
- Use SVG for diagrams when possible
- Aim for <200 KB per image
- Use descriptive file names (`architecture-overview.svg`, not `img1.png`)
