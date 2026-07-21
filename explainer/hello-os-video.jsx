/* hello_os — animated physics explainer. Scenes + theme wiring.
   Exports window.HelloOSVideo. Loads after animations-v2.jsx + tweaks-panel.jsx. */

const { SceneStage, useScene, interpolate, animate, Easing, clamp } = window;
const {
  useTweaks, TweaksPanel, TweakSection, TweakToggle, TweakSelect, TweakColor,
} = window;

/* ── Palette (Nocturne tokens) ──────────────────────────────────── */
const C = {
  bg: "#161826",
  surface: "#232532",
  surface2: "#2b2e3f",
  text: "#e9e9ed",
  mute: "#9397ab",
  mute2: "#b2b6ca",
  line: "#3f424d",
  line2: "#595d6c",
  section: "#262a60",
  sectionGlow: "#353b80",
  good: "#5fd08a",
  caution: "#e6b53c",
  unsafe: "#e5595b",
};
const FONT = "'Inter', system-ui, sans-serif";
const MONO = "'Inter', ui-monospace, monospace";

/* ── Real material data (from hello_os/core.py) ─────────────────── */
const MATERIALS = {
  "Ti-6Al-4V":        { density: 4430, tensile: 900e6,  color: "#4a90e2" },
  "Carbon Composite": { density: 1600, tensile: 1500e6, color: "#2ecc71" },
  "Beryllium":        { density: 1850, tensile: 400e6,  color: "#e74c3c" },
  "Maraging Steel":   { density: 8000, tensile: 2400e6, color: "#9b59b6" },
  "Silicon Nitride":  { density: 3200, tensile: 3000e6, color: "#f1c40f" },
};
const MAT_NAMES = Object.keys(MATERIALS);
// safe tip speed = sqrt(3 * tensile / density)  (radius cancels)
const safeTip = (m) => Math.sqrt((3 * m.tensile) / m.density);
const MAX_TIP = Math.max(...MAT_NAMES.map((n) => safeTip(MATERIALS[n]))); // ~1677
const specificStrength = (m) => m.tensile / m.density / 1000; // kN·m/kg

/* ── Theme context (carries tweak values into scenes) ───────────── */
const ThemeCtx = React.createContext({ accent: C.section, material: "Silicon Nitride", captions: true });
const useTheme = () => React.useContext(ThemeCtx);

/* ── Small helpers ──────────────────────────────────────────────── */
function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const fade = (p, a, b) => clamp((p - a) / (b - a), 0, 1); // ramp p over [a,b]->[0,1]

/* Lower-third caption. Fades in early, holds to end (clean cut). */
function Caption({ progress, kicker, title, sub, accent }) {
  const { captions } = useTheme();
  if (!captions) return null;
  const o = fade(progress, 0.04, 0.16);
  const y = (1 - o) * 26;
  return (
    <div style={{
      position: "absolute", left: 96, right: 96, bottom: 88,
      opacity: o, transform: `translateY(${y}px)`,
    }}>
      {kicker && (
        <div style={{
          fontFamily: FONT, fontSize: 22, letterSpacing: "0.22em", textTransform: "uppercase",
          color: accent, fontWeight: 600, marginBottom: 14,
        }}>{kicker}</div>
      )}
      <div style={{
        fontFamily: FONT, fontSize: 46, lineHeight: 1.15, fontWeight: 500,
        color: C.text, maxWidth: 1180, textWrap: "pretty",
      }}>{title}</div>
      {sub && (
        <div style={{
          fontFamily: FONT, fontSize: 26, lineHeight: 1.4, color: C.mute2,
          marginTop: 16, maxWidth: 1020, textWrap: "pretty",
        }}>{sub}</div>
      )}
    </div>
  );
}

/* ── Pseudo-3D rotor array (SVG, tilted ring of spinning discs) ──── */
function RotorArray({ spin, reveal, count, cx, cy, ringRx, ringRy, discR, accent, glow }) {
  const rotors = [];
  for (let i = 0; i < count; i++) {
    const ang = (i / count) * Math.PI * 2 - Math.PI / 2;
    const x = cx + ringRx * Math.cos(ang);
    const y = cy + ringRy * Math.sin(ang);
    const depth = (Math.sin(ang) + 1) / 2;          // 0 back … 1 front
    const scale = 0.62 + depth * 0.5;
    // staggered assembly reveal
    const rShow = clamp(reveal * count - i * 0.55, 0, 1);
    rotors.push({ i, x, y, scale, depth, rShow });
  }
  rotors.sort((a, b) => a.y - b.y); // paint back-to-front

  const disc = (r) => {
    const R = discR * r.scale;
    const ry = R * 0.34;
    const spokes = [];
    const nSpokes = 6;
    for (let s = 0; s < nSpokes; s++) {
      const th = (s / nSpokes) * Math.PI * 2 + spin * (1 + r.i * 0.03);
      spokes.push(
        <line key={s}
          x1="0" y1="0"
          x2={(R - 3) * Math.cos(th)} y2={ry * 0.9 * Math.sin(th)}
          stroke={accent} strokeWidth={2.2} strokeLinecap="round" opacity={0.85} />
      );
    }
    const op = r.rShow;
    return (
      <g key={r.i} transform={`translate(${r.x} ${r.y})`} opacity={op}>
        <ellipse cx="0" cy={ry * 0.5} rx={R} ry={ry} fill="#000" opacity={0.28 * r.depth} />
        <ellipse cx="0" cy="0" rx={R} ry={ry} fill={C.surface2}
          stroke={C.line2} strokeWidth={1.5} />
        <ellipse cx="0" cy="0" rx={R * 0.72} ry={ry * 0.72} fill="none"
          stroke={accent} strokeWidth={1} opacity={0.35} />
        {spokes}
        <circle cx="0" cy="0" r={R * 0.16} fill={accent} />
        <circle cx="0" cy="0" r={R * 0.16} fill="none" stroke={C.text} strokeWidth={0.6} opacity={0.4} />
      </g>
    );
  };

  return (
    <g>
      {glow > 0 && (
        <ellipse cx={cx} cy={cy} rx={ringRx * 1.28} ry={ringRy * 1.5}
          fill={accent} opacity={0.12 * glow}
          style={{ filter: "blur(46px)" }} />
      )}
      {/* orbit ring guide */}
      <ellipse cx={cx} cy={cy} rx={ringRx} ry={ringRy} fill="none"
        stroke={C.line2} strokeWidth={1.5} strokeDasharray="2 10"
        opacity={0.4 * clamp(reveal * 1.5, 0, 1)} />
      {rotors.map(disc)}
    </g>
  );
}

/* ═══════════════ SCENES ═══════════════ */

function Opening({ progress, localTime }) {
  const { accent } = useTheme();
  const spin = localTime * 2.4;
  const titleO = fade(progress, 0.12, 0.34);
  const subO = fade(progress, 0.34, 0.52);
  const lineW = fade(progress, 0.2, 0.5);
  return (
    <div style={{ position: "absolute", inset: 0, background: C.bg, overflow: "hidden" }}>
      <div style={{
        position: "absolute", inset: 0,
        background: `radial-gradient(1200px 900px at 72% 30%, ${accent}22, transparent 60%)`,
      }} />
      <svg viewBox="0 0 1920 1080" style={{ position: "absolute", inset: 0, opacity: 0.9 }}>
        <RotorArray spin={spin} reveal={1} count={1}
          cx={1360} cy={430} ringRx={0} ringRy={0} discR={168} accent={accent} glow={fade(progress, 0, 0.4)} />
      </svg>
      <div style={{ position: "absolute", left: 96, top: 388 }}>
        <div style={{
          fontFamily: MONO, fontSize: 96, fontWeight: 600, letterSpacing: "-0.02em",
          color: C.text, opacity: titleO, transform: `translateY(${(1 - titleO) * 20}px)`,
        }}>hello_os</div>
        <div style={{
          height: 3, background: accent, marginTop: 8, marginBottom: 28,
          width: `${lineW * 340}px`, borderRadius: 2,
        }} />
        <div style={{
          fontFamily: FONT, fontSize: 40, fontWeight: 400, color: C.mute2, maxWidth: 720,
          lineHeight: 1.3, opacity: subO, transform: `translateY(${(1 - subO) * 16}px)`, textWrap: "pretty",
        }}>Spin mass fast enough, and it bends spacetime.</div>
      </div>
    </div>
  );
}

function Idea({ progress, localTime }) {
  const { accent } = useTheme();
  const spin = localTime * 1.8;
  const reveal = fade(progress, 0.06, 0.62);
  return (
    <div style={{ position: "absolute", inset: 0, background: C.bg, overflow: "hidden" }}>
      <svg viewBox="0 0 1920 1080" style={{ position: "absolute", inset: 0 }}>
        <RotorArray spin={spin} reveal={reveal} count={10}
          cx={960} cy={430} ringRx={430} ringRy={150} discR={92} accent={accent}
          glow={fade(progress, 0.25, 0.7)} />
      </svg>
      <Caption progress={progress} accent={accent}
        kicker="The core idea"
        title="An array of fast-spinning rotors — a tabletop gravitomagnetic field generator."
        sub="Each rotor carries angular momentum. Together, the array makes a faint, measurable field." />
    </div>
  );
}

function Materials({ progress, localTime }) {
  const { accent, material } = useTheme();
  // selector sweeps to the tweak-selected material
  const selIdx = MAT_NAMES.indexOf(material);
  const cardW = 300, gap = 24, startX = 96, topY = 236;
  return (
    <div style={{ position: "absolute", inset: 0, background: C.bg, overflow: "hidden" }}>
      <div style={{
        position: "absolute", left: 96, top: 108,
        fontFamily: FONT, fontSize: 22, letterSpacing: "0.22em", textTransform: "uppercase",
        color: accent, fontWeight: 600, opacity: fade(progress, 0.02, 0.14),
      }}>Choose a material</div>
      <div style={{
        position: "absolute", left: 96, top: 146, maxWidth: 1200,
        fontFamily: FONT, fontSize: 42, fontWeight: 500, color: C.text,
        opacity: fade(progress, 0.05, 0.18),
      }}>The material sets the limit — stronger and lighter spins faster, safely.</div>

      {MAT_NAMES.map((name, i) => {
        const m = MATERIALS[name];
        const appear = fade(progress, 0.14 + i * 0.06, 0.32 + i * 0.06);
        const selected = i === selIdx;
        const selOn = fade(progress, 0.6, 0.72) * (selected ? 1 : 0);
        const x = startX + i * (cardW + gap);
        const barW = (safeTip(m) / MAX_TIP);
        return (
          <div key={name} style={{
            position: "absolute", left: x, top: topY, width: cardW, height: 372,
            background: C.surface, borderRadius: 12,
            border: `1.5px solid ${selOn > 0.3 ? accent : C.line}`,
            boxShadow: selOn > 0.3 ? `0 0 0 ${selOn * 3}px ${accent}33, 0 18px 40px #0007` : "0 8px 24px #0005",
            opacity: appear, transform: `translateY(${(1 - appear) * 30}px) scale(${1 + selOn * 0.02})`,
            padding: 24, boxSizing: "border-box",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
              <span style={{ width: 16, height: 16, borderRadius: 4, background: m.color, boxShadow: `0 0 12px ${m.color}88` }} />
              <span style={{ fontFamily: MONO, fontSize: 22, fontWeight: 600, color: C.text }}>{name}</span>
            </div>
            <Stat label="Density" value={`${m.density.toLocaleString()} kg/m³`} />
            <Stat label="Tensile strength" value={`${(m.tensile / 1e6).toLocaleString()} MPa`} />
            <Stat label="Specific strength" value={`${Math.round(specificStrength(m))} kN·m/kg`} />
            <div style={{ marginTop: 22, fontFamily: FONT, fontSize: 15, color: C.mute, marginBottom: 8 }}>Safe tip speed</div>
            <div style={{ height: 10, background: C.surface2, borderRadius: 6, overflow: "hidden" }}>
              <div style={{
                height: "100%", width: `${barW * appear * 100}%`, borderRadius: 6,
                background: `linear-gradient(90deg, ${accent}, ${m.color})`,
              }} />
            </div>
            <div style={{ fontFamily: MONO, fontSize: 20, color: C.text, marginTop: 8 }}>
              {Math.round(safeTip(m))} m/s
            </div>
          </div>
        );
      })}
      <Caption progress={progress} accent={accent}
        title={`Silicon Nitride & Carbon Composite win on strength-to-weight — the safest path to high field strength.`} />
    </div>
  );
}
function Stat({ label, value }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10 }}>
      <span style={{ fontFamily: FONT, fontSize: 15, color: C.mute }}>{label}</span>
      <span style={{ fontFamily: MONO, fontSize: 16, color: C.mute2 }}>{value}</span>
    </div>
  );
}

function Safety({ progress, localTime }) {
  const { accent } = useTheme();
  // needle sweeps up through the bands, then settles in GOOD (~0.55)
  const sweep = interpolate([0, 0.45, 0.62, 0.8, 1], [0, 0.95, 0.7, 0.55, 0.55], Easing.easeInOutCubic)(progress);
  const rpm = Math.round(interpolate([0, 0.45, 0.8, 1], [0, 34000, 20000, 20000], Easing.easeInOutCubic)(progress));
  const cx = 960, cy = 560, R = 300;
  // gauge arc 180° (left to right). stress 0..1
  const a0 = Math.PI, a1 = 0;
  const ang = a0 + (a1 - a0) * clamp(sweep, 0, 1);
  const band = sweep < 0.6 ? { label: "GOOD", col: C.good } : sweep < 0.85 ? { label: "CAUTION", col: C.caution } : { label: "UNSAFE", col: C.unsafe };
  const arcPt = (frac, rr) => [cx + rr * Math.cos(a0 + (a1 - a0) * frac), cy - rr * Math.sin(a0 + (a1 - a0) * frac)];
  const seg = (f0, f1, col, w) => {
    const p0 = arcPt(f0, R), p1 = arcPt(f1, R);
    return `M ${p0[0]} ${p0[1]} A ${R} ${R} 0 0 1 ${p1[0]} ${p1[1]}`;
  };
  const nx = cx + (R - 40) * Math.cos(ang), ny = cy - (R - 40) * Math.sin(ang);
  const o = fade(progress, 0.04, 0.16);
  return (
    <div style={{ position: "absolute", inset: 0, background: C.bg, overflow: "hidden" }}>
      <div style={{
        position: "absolute", left: 96, top: 108, opacity: o,
        fontFamily: FONT, fontSize: 22, letterSpacing: "0.22em", textTransform: "uppercase",
        color: accent, fontWeight: 600,
      }}>Safety first</div>
      <div style={{
        position: "absolute", left: 96, top: 146, maxWidth: 1300, opacity: o,
        fontFamily: FONT, fontSize: 42, fontWeight: 500, color: C.text,
      }}>Every design is scored against its material’s breaking point.</div>

      <svg viewBox="0 0 1920 1080" style={{ position: "absolute", inset: 0, opacity: o }}>
        <path d={seg(0, 0.6)} fill="none" stroke={C.good} strokeWidth={34} strokeLinecap="round" opacity={0.85} />
        <path d={seg(0.6, 0.85)} fill="none" stroke={C.caution} strokeWidth={34} opacity={0.85} />
        <path d={seg(0.85, 1)} fill="none" stroke={C.unsafe} strokeWidth={34} strokeLinecap="round" opacity={0.85} />
        {/* threshold ticks */}
        {[0.6, 0.85].map((f, i) => {
          const p = arcPt(f, R + 26);
          return <text key={i} x={p[0]} y={p[1]} fill={C.mute2} fontSize={20} fontFamily={MONO} textAnchor="middle">{f}</text>;
        })}
        <line x1={cx} y1={cy} x2={nx} y2={ny} stroke={C.text} strokeWidth={6} strokeLinecap="round" />
        <circle cx={cx} cy={cy} r={16} fill={accent} stroke={C.text} strokeWidth={2} />
        <text x={cx} y={cy - 90} textAnchor="middle" fill={band.col} fontSize={64} fontWeight="700" fontFamily={FONT}>{band.label}</text>
        <text x={cx} y={cy + 78} textAnchor="middle" fill={C.mute} fontSize={24} fontFamily={FONT}>stress ratio</text>
        <text x={cx} y={cy + 128} textAnchor="middle" fill={C.text} fontSize={46} fontFamily={MONO}>{sweep.toFixed(2)}</text>
      </svg>
      <div style={{
        position: "absolute", right: 120, top: 300, textAlign: "right", opacity: fade(progress, 0.2, 0.34),
      }}>
        <div style={{ fontFamily: FONT, fontSize: 18, color: C.mute, letterSpacing: "0.1em" }}>ROTOR SPEED</div>
        <div style={{ fontFamily: MONO, fontSize: 60, color: C.text }}>{rpm.toLocaleString()}</div>
        <div style={{ fontFamily: FONT, fontSize: 20, color: C.mute2 }}>rpm</div>
      </div>
      <Caption progress={progress} accent={accent}
        title="Push past the limit and the model flags it UNSAFE — before anything spins in the real world." />
    </div>
  );
}

function Detector({ progress, localTime }) {
  const { accent } = useTheme();
  const N = 240, x0 = 150, x1 = 1770, y0 = 300, y1 = 640;
  const pts = React.useMemo(() => {
    const rnd = mulberry32(42);
    const arr = [];
    for (let i = 0; i < N; i++) {
      const tt = i / (N - 1);
      const env = Math.cos(2 * Math.PI * 0.4 * tt * 5);
      const sig = Math.sin(2 * Math.PI * 1.8 * tt * 5) * env;
      const noise = (rnd() - 0.5) * 1.7 + (rnd() - 0.5) * 0.9;
      arr.push({ tt, sig, raw: sig + noise });
    }
    return arr;
  }, []);
  const sx = (tt) => x0 + tt * (x1 - x0);
  const sy = (v) => (y0 + y1) / 2 - v * 130;
  const reveal = fade(progress, 0.08, 0.6);
  const cutoff = reveal;
  const sigO = fade(progress, 0.5, 0.78);
  const line = (key, color, w, valOf, op) => {
    let d = "";
    pts.forEach((p, i) => {
      if (p.tt > cutoff) return;
      d += (i === 0 ? "M" : "L") + sx(p.tt).toFixed(1) + " " + sy(valOf(p)).toFixed(1) + " ";
    });
    return <path key={key} d={d} fill="none" stroke={color} strokeWidth={w} opacity={op} strokeLinejoin="round" />;
  };
  const snr = (progress > 0.5 ? interpolate([0.5, 0.8], [0, 6.2], Easing.easeOutCubic)(progress) : 0);
  const o = fade(progress, 0.04, 0.16);
  return (
    <div style={{ position: "absolute", inset: 0, background: C.bg, overflow: "hidden" }}>
      <div style={{
        position: "absolute", left: 96, top: 96, opacity: o,
        fontFamily: FONT, fontSize: 22, letterSpacing: "0.22em", textTransform: "uppercase",
        color: accent, fontWeight: 600,
      }}>Reading the signal</div>
      <div style={{
        position: "absolute", left: 96, top: 134, maxWidth: 1400, opacity: o,
        fontFamily: FONT, fontSize: 42, fontWeight: 500, color: C.text,
      }}>The field is faint — buried in noise until we integrate over time.</div>
      <svg viewBox="0 0 1920 1080" style={{ position: "absolute", inset: 0 }}>
        <rect x={x0} y={y0} width={x1 - x0} height={y1 - y0} fill={C.surface} rx={10} opacity={o} />
        <line x1={x0} y1={(y0 + y1) / 2} x2={x1} y2={(y0 + y1) / 2} stroke={C.line} strokeWidth={1} opacity={o} />
        {line("raw", C.mute, 1.4, (p) => p.raw, 0.55 * o)}
        {line("sig", accent, 3.2, (p) => p.sig, sigO)}
      </svg>
      <div style={{
        position: "absolute", right: 150, top: 700, display: "flex", gap: 56, opacity: fade(progress, 0.55, 0.75),
      }}>
        <Readout label="SNR / sec" value={snr.toFixed(1)} accent={accent} />
        <Readout label="to 5σ" value={snr > 0.1 ? `${Math.round(Math.pow(5 / snr, 2))} s` : "—"} accent={accent} />
      </div>
      <div style={{
        position: "absolute", left: 150, top: 700, opacity: fade(progress, 0.5, 0.72),
        display: "flex", gap: 32, alignItems: "center",
      }}>
        <Legend color={C.mute} label="signal + noise" />
        <Legend color={accent} label="recovered signal" />
      </div>
      <Caption progress={progress} accent={accent}
        title="hello_os simulates the full detector trace — so you know what you’d need to measure." />
    </div>
  );
}
function Readout({ label, value, accent }) {
  return (
    <div style={{ textAlign: "right" }}>
      <div style={{ fontFamily: FONT, fontSize: 16, color: C.mute, letterSpacing: "0.1em", textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontFamily: MONO, fontSize: 52, color: accent }}>{value}</div>
    </div>
  );
}
function Legend({ color, label }) {
  return (
    <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
      <span style={{ width: 26, height: 4, background: color, borderRadius: 2 }} />
      <span style={{ fontFamily: FONT, fontSize: 18, color: C.mute2 }}>{label}</span>
    </div>
  );
}

function Payoff({ progress, localTime }) {
  const { accent } = useTheme();
  const spin = localTime * 1.5;
  const o = fade(progress, 0.08, 0.3);
  const cliO = fade(progress, 0.4, 0.6);
  return (
    <div style={{ position: "absolute", inset: 0, background: C.bg, overflow: "hidden" }}>
      <div style={{
        position: "absolute", inset: 0,
        background: `radial-gradient(1100px 800px at 50% 44%, ${accent}22, transparent 62%)`,
      }} />
      <svg viewBox="0 0 1920 1080" style={{ position: "absolute", inset: 0, opacity: 0.85 }}>
        <RotorArray spin={spin} reveal={1} count={10}
          cx={960} cy={400} ringRx={360} ringRy={122} discR={78} accent={accent} glow={1} />
      </svg>
      <div style={{ position: "absolute", left: 0, right: 0, top: 640, textAlign: "center" }}>
        <div style={{
          fontFamily: MONO, fontSize: 40, color: C.mute2, opacity: o, marginBottom: 16,
        }}>hello_os</div>
        <div style={{
          fontFamily: FONT, fontSize: 60, fontWeight: 500, color: C.text, opacity: o,
          transform: `translateY(${(1 - o) * 18}px)`, maxWidth: 1200, margin: "0 auto", lineHeight: 1.15,
        }}>Explore the physics safely — in code.</div>
        <div style={{
          display: "inline-block", marginTop: 34, padding: "16px 30px", borderRadius: 10,
          background: C.surface, border: `1.5px solid ${C.line}`, opacity: cliO,
          transform: `translateY(${(1 - cliO) * 14}px)`,
        }}>
          <span style={{ fontFamily: MONO, fontSize: 26, color: C.mute }}>$ </span>
          <span style={{ fontFamily: MONO, fontSize: 26, color: C.text }}>python -m hello_os --optimize</span>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════ ROOT ═══════════════ */
const TWEAK_DEFAULTS = window.TWEAK_DEFAULTS || { motionEditor: true, accent: "#9184d9", material: "Silicon Nitride", captions: true };

function HelloOSVideo(props) {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const theme = { accent: t.accent, material: t.material, captions: t.captions };
  return (
    <ThemeCtx.Provider value={theme}>
      <SceneStage
        width={1920} height={1080} bg={C.bg}
        scenes={props.scenes} playback={props.playback}>
        {{ Opening, Idea, Materials, Safety, Detector, Payoff }}
      </SceneStage>
      <TweaksPanel>
        <TweakSection label="Story" />
        <TweakSelect label="Featured material" value={t.material}
          options={MAT_NAMES} onChange={(v) => setTweak("material", v)} />
        <TweakToggle label="Captions" value={t.captions} onChange={(v) => setTweak("captions", v)} />
        <TweakSection label="Theme" />
        <TweakColor label="Accent" value={t.accent}
          options={["#9184d9", "#5fd08a", "#4a90e2", "#e6b53c"]}
          onChange={(v) => setTweak("accent", v)} />
        <TweakSection label="Editor" />
        <TweakToggle label="Motion editor" value={t.motionEditor} onChange={(v) => setTweak("motionEditor", v)} />
      </TweaksPanel>
    </ThemeCtx.Provider>
  );
}

window.HelloOSVideo = HelloOSVideo;
