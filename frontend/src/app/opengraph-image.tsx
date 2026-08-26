import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { ImageResponse } from "next/og";

/** What a link to the shop looks like when it is pasted somewhere: a dashboard
 *  card, a chat window, a search result. Without this those all fall back to a
 *  screenshot of whatever the page happened to be showing, which for a shop
 *  between sales is an empty listing. */

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "FlashCart — limited stock, held fairly";

const PAPER = "#fdfcfa";
const INK = "#1a1815";
const INK_SOFT = "#4a453e";
const HOLD = "#a8762c";

/* The card is drawn on the server, where the site's webfonts do not exist, so
   the display face is read from a file kept beside this one. Vendored rather
   than fetched at build time: a card is not worth making the build depend on
   somebody else's CDN being reachable. */
async function displayFont() {
  return readFile(join(process.cwd(), "src/app/_og/playfair-display-600.ttf"));
}

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: PAPER,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "Playfair Display",
        }}
      >
        {/* The same cart that leans forward and trails motion lines. */}
        <svg width="230" height="144" viewBox="0 0 64 40" fill="none"
             stroke={HOLD} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <path d="M2 14h16M8 21h12M14 28h8" />
          <path d="M25 6h6l3 8m0 0 4 13h17l6-13H34Z" />
          <circle cx="40" cy="34" r="3.2" />
          <circle cx="52" cy="34" r="3.2" />
        </svg>

        <div style={{ marginTop: 34, fontSize: 116, letterSpacing: 16, color: INK }}>
          FlashCart
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 26, marginTop: 34 }}>
          <div style={{ width: 150, height: 1, background: HOLD, opacity: 0.5 }} />
          <div style={{ fontSize: 27, letterSpacing: 7, color: INK_SOFT, fontFamily: "sans-serif" }}>
            LIMITED STOCK. HELD FAIRLY.
          </div>
          <div style={{ width: 150, height: 1, background: HOLD, opacity: 0.5 }} />
        </div>
      </div>
    ),
    {
      ...size,
      fonts: [
        { name: "Playfair Display", data: await displayFont(), weight: 600, style: "normal" },
      ],
    },
  );
}
