/**
 * RDH Short — Gallery White editorial system.
 * Design language from imports/chatgptYoutubeShortTemplate/RDH_SHORT_TEMPLATE_SPEC.md
 * (operator-approved typography/overlays), executed with proper cover-cropped
 * footage. Scene-driven data model so the worker can parameterize every post.
 */
import {
  AbsoluteFill,
  Audio,
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
// ponytail: 28s default timed out on ~1 frame in 900 under 4x concurrency;
// generous timeout + retries beats restructuring the load. Raise if it recurs.
const fontHandle = delayRender("load Manrope", {
  timeoutInMilliseconds: 120000,
  retries: 2,
});
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
  /**
   * Public-facing configuration ONLY — "3.5 BHK", never a unit/flat number.
   * Operator rule: we do not expose which flat the footage is from.
   */
  config: z.string(),
  area: z.string(),
  /** persistent on-screen contact, whole duration */
  phone: z.string(),
  /** headline price on the end card, e.g. "₹4.10 Cr" */
  price: z.string().optional(),
  /** qualifier under the price, e.g. "SOLD FURNISHED" */
  priceNote: z.string().optional(),
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
      /**
       * CSS object-position for the cover crop, e.g. "50% 80%" to bias low.
       * Landscape footage in a 1080x1920 frame loses ~68% of its width, so the
       * subject is often outside a centre crop. Defaults to centre.
       */
      focus: z.string().optional(),
      /** slow a reveal down (1 = realtime). Lets a short pan fill a longer scene. */
      playbackRate: z.number().optional(),
      /**
       * CSS filter, e.g. "brightness(1.3) contrast(1.1)" — lifts the dark 480p
       * night footage. Grades what was shot; does not invent detail.
       */
      filter: z.string().optional(),
    })
  ),
  ctaText: z.string(),
  trustLine: z.string(),
  /** optional stacked statement on the end card; omit to drop it */
  positioning: z.array(z.string()).optional(),
  /** filename in public/ — footage is muted, so this is the only audio */
  music: z.string().optional(),
  musicVolume: z.number().optional(),
});

/**
 * Flat numbers must never reach a public video. Matches "B-4005", "B 4005",
 * "Flat 402", "#1203". Deliberately at the schema boundary, not in a comment:
 * step 2 feeds these props from the DB, where unit numbers genuinely live.
 * ponytail: regex, not a parser — widen it if a real caption trips it.
 */
export const UNIT_NUMBER =
  /(\b(flat|unit|apt|apartment)\s*(no\.?|number)?\s*#?\s*[a-z]?-?\s*\d{2,4}\b)|(\b[a-z]\s*-\s*\d{3,4}\b)|(#\s*\d{3,4}\b)/i;

const scrubbed = (label: string) => (v: string, ctx: z.RefinementCtx) => {
  const hit = v.match(UNIT_NUMBER);
  if (hit)
    ctx.addIssue({
      code: "custom",
      message: `${label} exposes a flat number ("${hit[0]}"). Use the configuration ("3.5 BHK") instead.`,
    });
};

export const shortSchemaChecked = shortSchema.superRefine((p, ctx) => {
  scrubbed("config")(p.config, ctx);
  scrubbed("ctaText")(p.ctaText, ctx);
  p.scenes.forEach((s, i) => {
    scrubbed(`scene ${i} eyebrow`)(s.eyebrow, ctx);
    scrubbed(`scene ${i} body`)(s.body ?? "", ctx);
    scrubbed(`scene ${i} footer`)(s.footer ?? "", ctx);
    s.headline.forEach((h) => scrubbed(`scene ${i} headline`)(h, ctx));
  });
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

/**
 * Persistent brand lockup — logo + phone, every frame of every scene.
 * Rides above all Sequences, so it must read on both dark footage and the
 * light MIST editorial band: hence the translucent ink pill behind the number.
 */
const Watermark: React.FC<{ phone: string }> = ({ phone }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <Img
        src={staticFile("rdh-mark.png")}
        style={{ position: "absolute", top: 52, right: 60, width: 96, ...rise(frame, 2) }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 54,
          right: 60,
          background: "rgba(26,26,26,0.55)",
          border: "1px solid rgba(238,241,239,0.30)",
          backdropFilter: "blur(6px)",
          borderRadius: 999,
          padding: "14px 28px",
          ...rise(frame, 4),
        }}
      >
        <span style={{ ...eyebrowStyle, fontSize: 20, color: "#ffffff", letterSpacing: "0.12em" }}>
          {phone}
        </span>
      </div>
    </AbsoluteFill>
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

const Video: React.FC<{
  src: string;
  startFrom: number;
  focus?: string;
  playbackRate?: number;
  filter?: string;
}> = ({ src, startFrom, focus, playbackRate, filter }) => {
  const frame = useCurrentFrame();
  const fill: React.CSSProperties = {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    objectPosition: focus ?? "center",
    filter,
  };
  if (/\.(jpe?g|png)$/i.test(src)) {
    // still image: slow Ken Burns push-in so photo scenes read as footage
    return (
      <Img
        src={staticFile(src)}
        style={{ ...fill, transform: `scale(${1.04 + frame * 0.0011})` }}
      />
    );
  }
  return (
    <OffthreadVideo
      muted
      src={staticFile(src)}
      startFrom={Math.round(startFrom * FPS)}
      playbackRate={playbackRate}
      style={fill}
    />
  );
};

/** full-bleed footage, dark lower gradient, text block bottom-left */
const FullScene: React.FC<Props["scenes"][number]> = (s) => {
  const frame = useCurrentFrame();
  return (
  <AbsoluteFill style={{ background: INK }}>
    <Video src={s.source} startFrom={s.sourceStart} focus={s.focus} playbackRate={s.playbackRate} filter={s.filter} />
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
        <Video src={s.source} startFrom={s.sourceStart} focus={s.focus} playbackRate={s.playbackRate} filter={s.filter} />
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
        // ponytail: 168 not 200 — "3.5 BHK" is wider than "B-4005" and would
        // overrun the 952px text column at 200.
        fontSize: 168,
        letterSpacing: "-0.03em",
        color: TEAL,
        marginTop: 90,
        lineHeight: 1,
        whiteSpace: "nowrap",
        ...rise(frame, 6),
      }}
    >
      {p.config}
    </div>
    <div style={{ ...eyebrowStyle, color: INK, marginTop: 18, ...rise(frame, 9) }}>
      {p.building.toUpperCase()}
    </div>
    {p.price && (
      <div style={{ marginTop: 44, ...rise(frame, 11) }}>
        <div
          style={{
            fontFamily,
            fontWeight: 800,
            fontSize: 92,
            letterSpacing: "-0.02em",
            color: WARM,
            lineHeight: 1,
          }}
        >
          {p.price}
        </div>
      </div>
    )}
    {p.priceNote && (
      <div
        style={{
          ...eyebrowStyle,
          fontSize: 22,
          color: "rgba(26,26,26,0.6)",
          marginTop: p.price ? 14 : 44,
          ...rise(frame, 11),
        }}
      >
        {p.priceNote}
      </div>
    )}
    {p.positioning && p.positioning.length > 0 && (
      <div style={{ marginTop: p.price ? 56 : 100 }}>
        <Headline lines={p.positioning} size={96} delay={12} />
      </div>
    )}
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
  </AbsoluteFill>
  );
};

export const Short: React.FC<Props> = (p) => {
  // Remotion validates `schema` only in the Studio props editor — it does NOT
  // check --props at render time. So the flat-number rule is enforced HERE, the
  // one gate every render passes through. Fails the render loudly, by design.
  const leak = [
    p.config,
    p.ctaText,
    p.priceNote ?? "",
    ...p.scenes.flatMap((s) => [s.eyebrow, s.body ?? "", s.footer ?? "", ...s.headline]),
  ]
    .map((t) => t.match(UNIT_NUMBER)?.[0])
    .find(Boolean);
  if (leak) {
    throw new Error(
      `Short: refusing to render — "${leak}" looks like a flat number. ` +
        `Public videos show the configuration ("3.5 BHK"), never the unit.`
    );
  }

  const total = totalFrames(p);
  const vol = p.musicVolume ?? 0.32;
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
      <Watermark phone={p.phone} />
      {p.music && (
        <Audio
          src={staticFile(p.music)}
          // fade in off the top, duck out under the end card
          volume={(f) =>
            interpolate(f, [0, 18, total - 45, total - 5], [0, vol, vol, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })
          }
        />
      )}
    </AbsoluteFill>
  );
};

export const totalFrames = (p: Props) =>
  p.scenes.reduce((acc, s) => acc + Math.round(s.duration * FPS), 0) + 140;
