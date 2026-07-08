Scroll parallax wrapper for feature imagery. Give the inner image extra height (e.g. 115%) so the drift never shows edges.

```jsx
<Parallax speed={0.12} style={{ aspectRatio: "21/9", borderRadius: 16 }}>
  <img src="…" style={{ width: "100%", height: "115%", objectFit: "cover" }} />
</Parallax>
```
