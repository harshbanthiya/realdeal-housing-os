import { Composition } from "remotion";
import { Short, shortSchemaChecked, totalFrames, type Props } from "./Short";

// Scene plan adapted from the operator-approved spec
// (imports/chatgptYoutubeShortTemplate/RDH_SHORT_TEMPLATE_SPEC.md)
const defaultProps: Props = {
  building: "Imperial Heights",
  // Public-facing config, never the flat number — operator rule.
  config: "3.5 BHK",
  area: "Goregaon West",
  phone: "+91 829 129 3889", // canonical, from web/src/lib/site.ts

  scenes: [
    {
      source: "ekta-view-loop.mp4",
      sourceStart: 0,
      duration: 4.2,
      eyebrow: "GOREGAON WEST · FROM OUR ARCHIVE",
      headline: ["Then you", "get home."],
      body: "The skyline from an Ekta Tripolis living room.",
      layout: "full",
    },
    {
      source: "walkthrough.mp4",
      sourceStart: 42,
      duration: 5.5,
      eyebrow: "IMPERIAL HEIGHTS · 3.5 BHK",
      headline: ["One room.", "Three daily", "zones."],
      body: "Living, dining and kitchen stay connected.",
      footer: "OCCUPIED FLAT / UNSTAGED",
      layout: "editorial",
    },
    {
      source: "walkthrough.mp4",
      sourceStart: 50,
      duration: 5.2,
      eyebrow: "02 / DAILY USE",
      headline: ["The kitchen", "stays in the", "conversation."],
      body: "Open to the living and dining room.",
      footer: "IMPERIAL HEIGHTS · GOREGAON WEST",
      layout: "editorial",
    },
    {
      source: "walkthrough.mp4",
      sourceStart: 30.5,
      duration: 5.2,
      eyebrow: "03 / THE VIEW",
      headline: ["A planted edge.", "A very Mumbai", "view."],
      body: "High-rises and open green below.",
      layout: "full",
    },
    {
      source: "ih-pool-loop.mp4",
      sourceStart: 0.5,
      duration: 5,
      eyebrow: "04 / DOWNSTAIRS",
      headline: ["The pool", "deck."],
      body: "Imperial Heights · Goregaon West",
      layout: "full",
    },
  ],
  ctaText: 'DM "IH" FOR CURRENT AVAILABILITY',
  trustLine: "Specific facts. Real footage.\nNo brochure language.",
  positioning: ["Tracked", "floor by", "floor."],
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Short"
    component={Short}
    durationInFrames={totalFrames(defaultProps)}
    fps={30}
    width={1080}
    height={1920}
    schema={shortSchemaChecked}
    defaultProps={defaultProps}
  />
);
