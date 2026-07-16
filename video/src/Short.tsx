/**
 * RDH Short — Gallery White editorial system.
 * Design language from imports/chatgptYoutubeShortTemplate/RDH_SHORT_TEMPLATE_SPEC.md
 * (operator-approved typography/overlays), executed with proper cover-cropped
 * footage. Scene-driven data model so the worker can parameterize every post.
 */
import {
  AbsoluteFill,
  Easing,
  Img,
  OffthreadVideo,
  Sequence,
  continueRender,
  delayRender,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { z } from "zod";

// Manrope is a variable-weight file served from public/ — no font CDN dep
const fontFamily = "Manrope, sans-serif";
const fontHandle = delayRender("load Manrope");
new FontFace("Manrope", `url(${staticFile("Manrope-Bold.ttf")})`)
  .load()
  .then((f) => {
    document.fonts.add(f);
    continueRender(fontHandle);
  })
  .catch(() => continueRender(fontHandle));

// tokens — lockstep with web/src/app/globals.css
const TEAL = "#1f3d4d";
const INK = "#1a1a1a";
const MIST = "#eef1ef";
const MIST_DEEP = "#e3e8e5";
const WARM = "#c2493d";

const EASE = Easing.bezier(0.22, 1, 0.36, 1); // spec's motion token
const FPS = 30;

export const shortSchema = z.object({
  building: z.string(),
  unit: z.string(),
  area: z.string(),
  scenes: z.array(
    z.object({
      source: z.string(),
      sourceStart: z.number(),
      duration: z.number(), // seconds
      eyebrow: z.string(),
      headline: z.array(z.string()),
      body: z.string().optional(),
      footer: z.string().optional(),
      layout: z.enum(["full", "editorial"]),
    })
  ),
  ctaText: z.string(),
  trustLine: z.string(),
  positioning: z.array(z.string()),
});
export type Props = z.infer<typeof shortSchema>;

/** spec motion token: 220ms fade, 16px rise — pure, hook-safe anywhere */
const rise = (frame: number, delayFrames = 0) => {
  const t = interpolate(frame - delayFrames, [0, 7], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: EASE,
  });
  return { opacity: t, transform: `translateY(${(1 - t) * 16}px)` };
};

const eyebrowStyle: React.CSSProperties = {
  fontFamily: "Menlo, monospace",
  textTransform: "uppercase",
  letterSpacing: "0.24em",
  fontSize: 25,
  fontWeight: 700,
};

const Eyebrow: React.FC<{ text: string; light?: boolean; delay?: number }> = ({
  text,
  light,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        ...eyebrowStyle,
        color: light ? "rgba(238,241,239,0.85)" : TEAL,
        ...rise(frame, delay),
      }}
    >
      {text}
    </div>
  );
};

/** stacked sentence-case headline (minimal v2), one line per row, staggered rise */
const Headline: React.FC<{ lines: string[]; light?: boolean; size?: number; delay?: number }> = ({
  lines,
  light,
  size = 88,
  delay = 3,
}) => {
  const frame = useCurrentFrame();
  return (
  <div>
    {lines.map((line, i) => (
      <div
        key={i}
        style={{
          fontFamily,
          fontWeight: 800,
          fontSize: size,
          lineHeight: 1.12,
          letterSpacing: "-0.015em",
          color: light ? "#ffffff" : TEAL,
          ...rise(frame, delay + i * 3),
        }}
      >
        {line}
      </div>
    ))}
  </div>
  );
};

/** minimal v2: tiny translucent pill chip, top-left */
const Chip: React.FC<{ text: string; dark?: boolean }> = ({ text, dark }) => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        position: "absolute",
        top: 64,
        left: 64,
        background: dark ? "rgba(26,26,26,0.45)" : "rgba(238,241,239,0.22)",
        border: "1px solid rgba(238,241,239,0.35)",
        backdropFilter: "blur(6px)",
        borderRadius: 999,
        padding: "16px 30px",
        ...rise(frame, 2),
      }}
    >
      <span style={{ ...eyebrowStyle, fontSize: 21, color: "#ffffff" }}>{text}</span>
    </div>
  );
};

const RedRule: React.FC<{ delay?: number }> = ({ delay = 10 }) => {
  const frame = useCurrentFrame();
  const w = interpolate(frame - delay, [0, 10], [0, 88], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: EASE,
  });
  return <div style={{ height: 6, width: w, background: WARM, marginTop: 28 }} />;
};

const Video: React.FC<{ src: string; startFrom: number }> = ({ src, startFrom }) => (
  <OffthreadVideo
    muted
    src={staticFile(src)}
    startFrom={Math.round(startFrom * FPS)}
    style={{ width: "100%", height: "100%", objectFit: "cover" }}
  />
);

/** full-bleed footage, dark lower gradient, text block bottom-left */
const FullScene: React.FC<Props["scenes"][number]> = (s) => {
  const frame = useCurrentFrame();
  return (
  <AbsoluteFill style={{ background: INK }}>
    <Video src={s.source} startFrom={s.sourceStart} />
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(to top, rgba(26,26,26,0.82) 0%, rgba(26,26,26,0.3) 34%, transparent 58%)",
      }}
    />
    <Chip text={s.eyebrow} />
    <AbsoluteFill style={{ justifyContent: "flex-end", padding: 72, paddingBottom: 230 }}>
      <Headline lines={s.headline} light />
      {s.body && (
        <div
          style={{
            fontFamily,
            fontWeight: 400,
            fontSize: 35,
            color: "rgba(255,255,255,0.82)",
            marginTop: 22,
            ...rise(frame, 12),
          }}
        >
          {s.body}
        </div>
      )}
    </AbsoluteFill>
  </AbsoluteFill>
  );
};

/** Gallery White editorial page: text block up top, cover-cropped footage card */
const EditorialScene: React.FC<Props["scenes"][number]> = (s) => {
  const frame = useCurrentFrame();
  const card = rise(frame, 8);
  return (
    <AbsoluteFill style={{ background: MIST }}>
      {/* minimal v2: white editorial band on top, footage flush full-width below */}
      <div style={{ padding: "110px 64px 64px", borderBottom: `1px solid ${MIST_DEEP}` }}>
        <Eyebrow text={s.eyebrow} />
        <div style={{ height: 26 }} />
        <Headline lines={s.headline} size={76} />
        {s.body && (
          <div
            style={{
              fontFamily,
              fontWeight: 400,
              fontSize: 35,
              color: "rgba(26,26,26,0.7)",
              marginTop: 22,
              ...rise(frame, 10),
            }}
          >
            {s.body}
          </div>
        )}
        <RedRule />
      </div>
      <div style={{ flex: 1, overflow: "hidden", ...card }}>
        <Video src={s.source} startFrom={s.sourceStart} />
      </div>
      {s.footer && (
        <div
          style={{
            ...eyebrowStyle,
            fontSize: 21,
            color: "rgba(26,26,26,0.5)",
            padding: "36px 64px 120px",
            ...rise(frame, 14),
          }}
        >
          {s.footer}
        </div>
      )}
    </AbsoluteFill>
  );
};

/** end card — spec's lead card: giant unit, positioning stack, CTA pill */
const EndCard: React.FC<Props> = (p) => {
  const frame = useCurrentFrame();
  return (
  <AbsoluteFill style={{ background: MIST, padding: "120px 64px 150px" }}>
    <div style={{ ...eyebrowStyle, color: TEAL, ...rise(frame, 0) }}>REAL DEAL HOUSING</div>
    <RedRule delay={4} />
    <div
      style={{
        fontFamily,
        fontWeight: 800,
        fontSize: 200,
        letterSpacing: "-0.03em",
        color: TEAL,
        marginTop: 90,
        lineHeight: 1,
        ...rise(frame, 6),
      }}
    >
      {p.unit}
    </div>
    <div style={{ ...eyebrowStyle, color: INK, marginTop: 18, ...rise(frame, 9) }}>
      {p.building.toUpperCase()}
    </div>
    <div style={{ marginTop: 100 }}>
      <Headline lines={p.positioning} size={96} delay={12} />
    </div>
    <div style={{ flex: 1 }} />
    <div
      style={{
        background: TEAL,
        borderRadius: 22,
        padding: "34px 44px",
        ...rise(frame, 18),
      }}
    >
      <div style={{ ...eyebrowStyle, fontSize: 27, color: MIST, letterSpacing: "0.12em" }}>
        {p.ctaText}
      </div>
    </div>
    <div
      style={{
        fontFamily,
        fontWeight: 400,
        fontSize: 36,
        color: "rgba(26,26,26,0.75)",
        marginTop: 56,
        whiteSpace: "pre-line",
        ...rise(frame, 22),
      }}
    >
      {p.trustLine}
    </div>
    <div style={{ ...eyebrowStyle, fontSize: 21, color: "rgba(26,26,26,0.5)", marginTop: 60, ...rise(frame, 24) }}>
      {p.area.toUpperCase()} · MUMBAI
    </div>
    <AbsoluteFill style={{ alignItems: "flex-end", padding: "104px 64px", pointerEvents: "none" }}>
      <Img src={staticFile("rdh-mark.png")} style={{ width: 110, ...rise(frame, 2) }} />
    </AbsoluteFill>
  </AbsoluteFill>
  );
};

export const Short: React.FC<Props> = (p) => {
  let at = 0;
  const seqs = p.scenes.map((s, i) => {
    const from = at;
    const dur = Math.round(s.duration * FPS);
    at += dur;
    return (
      <Sequence key={i} from={from} durationInFrames={dur}>
        {s.layout === "full" ? <FullScene {...s} /> : <EditorialScene {...s} />}
      </Sequence>
    );
  });
  return (
    <AbsoluteFill style={{ background: INK, fontFamily }}>
      {seqs}
      <Sequence from={at} durationInFrames={140}>
        <EndCard {...p} />
      </Sequence>
    </AbsoluteFill>
  );
};

export const totalFrames = (p: Props) =>
  p.scenes.reduce((acc, s) => acc + Math.round(s.duration * FPS), 0) + 140;
