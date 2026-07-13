Scroll reveal wrapper — the ONLY entrance animation in the system. Fade + 26px rise, 0.75s, once.

```jsx
{items.map((item, i) => (
  <Reveal key={item.id} delay={i * 0.05}>…</Reveal>
))}
```
