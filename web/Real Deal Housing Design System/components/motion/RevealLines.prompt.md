Masked headline reveal: each line rises from behind an overflow clip (0.9s, expo ease, 90ms stagger). For hero + statement headlines only — body copy keeps the plain Reveal.

```jsx
<RevealLines as="h1" lines={["Your Future Home", "Is Right Here"]}
  style={{ fontSize: 88, fontWeight: 800, lineHeight: 1.02, color: "var(--teal)" }} />
```
