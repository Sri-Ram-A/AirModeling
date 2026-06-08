const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType,
  VerticalAlign, PageNumber, Header, Footer, LevelFormat,
  TableOfContents, SectionType, Column, PageBreak
} = require('docx');
const fs = require('fs');

// ─── Helpers ──────────────────────────────────────────────────────────────────

const BORDER_NONE = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const NO_BORDERS = { top: BORDER_NONE, bottom: BORDER_NONE, left: BORDER_NONE, right: BORDER_NONE };
const THIN_BORDER = { style: BorderStyle.SINGLE, size: 4, color: "CCCCCC" };
const TABLE_BORDERS = { top: THIN_BORDER, bottom: THIN_BORDER, left: THIN_BORDER, right: THIN_BORDER };
const CELL_MARGINS = { top: 80, bottom: 80, left: 120, right: 120 };

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 280, after: 120 },
    children: [new TextRun({ text, font: "Times New Roman", size: 24, bold: true, allCaps: true })]
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 200, after: 80 },
    children: [new TextRun({ text, font: "Times New Roman", size: 22, bold: true, italics: true })]
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 160, after: 60 },
    children: [new TextRun({ text, font: "Times New Roman", size: 20, bold: true })]
  });
}

function body(text, opts = {}) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { before: 60, after: 60, line: 276 },
    children: [new TextRun({ text, font: "Times New Roman", size: 20, ...opts })]
  });
}

function bodyRuns(runs) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { before: 60, after: 60, line: 276 },
    children: runs.map(r =>
      typeof r === 'string'
        ? new TextRun({ text: r, font: "Times New Roman", size: 20 })
        : new TextRun({ font: "Times New Roman", size: 20, ...r })
    )
  });
}

function italic(text) {
  return new TextRun({ text, font: "Times New Roman", size: 20, italics: true });
}

function bold(text) {
  return new TextRun({ text, font: "Times New Roman", size: 20, bold: true });
}

function formula(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 100, after: 100 },
    children: [new TextRun({ text, font: "Courier New", size: 20, italics: true })]
  });
}

function figCaption(num, title, desc) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 60, after: 120 },
    children: [
      new TextRun({ text: `Fig. ${num}. `, font: "Times New Roman", size: 18, bold: true }),
      new TextRun({ text: `${title} — ${desc}`, font: "Times New Roman", size: 18, italics: true })
    ]
  });
}

function figurePlaceholder(num, title, desc) {
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 100, after: 40 },
      border: {
        top: THIN_BORDER, bottom: THIN_BORDER, left: THIN_BORDER, right: THIN_BORDER
      },
      children: [
        new TextRun({ text: `[FIGURE ${num}: ${title}]`, font: "Times New Roman", size: 18, bold: true, color: "555555" })
      ]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 20, after: 20 },
      children: [new TextRun({ text: `[${desc}]`, font: "Times New Roman", size: 16, italics: true, color: "777777" })]
    }),
    figCaption(num, title, desc)
  ];
}

function spacer() {
  return new Paragraph({ spacing: { before: 80, after: 80 }, children: [new TextRun("")] });
}

function tableHead(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text, font: "Times New Roman", size: 18, bold: true })]
  });
}

function tableCell(text, isHeader = false, shadeColor = null) {
  return new TableCell({
    borders: TABLE_BORDERS,
    margins: CELL_MARGINS,
    shading: shadeColor ? { fill: shadeColor, type: ShadingType.CLEAR } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text, font: "Times New Roman", size: 18, bold: isHeader })]
    })]
  });
}

// ─── CONTENT SECTIONS ─────────────────────────────────────────────────────────

// Title section (single column)
const titleContent = [
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 200, after: 120 },
    children: [new TextRun({
      text: "Air Pollution Attribution: Tracking Pollutant Transport Across Urban Monitoring Stations Using Classical Inversion and Deep Learning",
      font: "Times New Roman", size: 28, bold: true
    })]
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 80, after: 80 },
    children: [new TextRun({ text: "[Author Name]", font: "Times New Roman", size: 20, italics: true })]
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 40, after: 40 },
    children: [new TextRun({ text: "Department of [Field], [Institution]", font: "Times New Roman", size: 18 })]
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 40, after: 200 },
    children: [new TextRun({ text: "[City, Country | email@institution.edu]", font: "Times New Roman", size: 18 })]
  }),

  // Abstract box
  new Paragraph({
    spacing: { before: 60, after: 60 },
    children: [
      new TextRun({ text: "Abstract", font: "Times New Roman", size: 20, bold: true, italics: true }),
      new TextRun({ text: "—This paper presents a systematic pipeline for attributing urban air-pollution concentrations to their likely source stations using a physics-based Gaussian plume transport model coupled with classical inverse solvers and a deep-learning LSTM framework. Fourteen monitoring stations across Bengaluru were extracted from the Central Pollution Control Board (CPCB) database for the year 2025. After rigorous imputation of missing sensor data, a transport matrix T was constructed for multiple pollutants and used to invert observed concentration vectors C into emission-rate vectors Q via Least Squares, Non-Negative Least Squares, Tikhonov Regularisation, Truncated SVD, and Bayesian Inference. An LSTM-based deep-learning model was subsequently trained to capture temporal dynamics. Results demonstrate that physics-informed reconstruction substantially outperforms data-only baselines, and Bayesian inference provides meaningful uncertainty bounds on attributed emission rates.", font: "Times New Roman", size: 20 })
    ]
  }),
  new Paragraph({
    spacing: { before: 60, after: 120 },
    children: [
      new TextRun({ text: "Index Terms", font: "Times New Roman", size: 20, bold: true, italics: true }),
      new TextRun({ text: "—Air pollution attribution, Gaussian plume model, transport matrix inversion, Bayesian inference, LSTM, CPCB, Bengaluru.", font: "Times New Roman", size: 20 })
    ]
  }),
];

// Two-column body content
const bodyContent = [
  // ─── I. INTRODUCTION ───────────────────────────────────────────────────────
  h1("I.  Introduction"),

  body("Urban air quality monitoring is critical for public health, urban planning, and environmental policy. While individual sensor stations report local concentrations of pollutants such as PM2.5, PM10, NO₂ and SO₂, understanding how those concentrations arise—and specifically, how pollution generated at one location is transported and deposited at another—remains an open challenge."),

  body("This work addresses the air-pollution attribution problem: given a vector of observed concentrations C at N monitoring stations, and a physics-derived transport matrix T that encodes the fraction of emissions at station j reaching station i, recover the underlying emission-rate vector Q such that:"),

  formula("C = T · Q"),

  bodyRuns([
    "where ",
    italic("C"),
    " ∈ ℝᴺ is the observed concentration vector [μg/m³], ",
    italic("T"),
    " ∈ ℝᴺˣᴺ is the transport matrix [μg m⁻³ per g s⁻¹], and ",
    italic("Q"),
    " ∈ ℝᴺ is the unknown emission-rate vector [g/s]."
  ]),

  body("The dataset comprises 14 CPCB stations in Bengaluru with 15-minute frequency readings throughout 2025. The pipeline follows three major stages: (1) Exploratory Data Analysis and Imputation, (2) Classical Transport-Matrix Inversion, and (3) Deep Learning (LSTM) attribution. The framework is intentionally extensible—future work will incorporate Graph Neural Networks (GNNs) and additional pollution sources such as vehicular traffic and construction activity."),

  spacer(),

  // ─── II. DATASET ─────────────────────────────────────────────────────────
  h1("II.  Dataset and Study Area"),

  body("Data were retrieved from the Central Pollution Control Board (CPCB) of India for the year 2025. The study covers 14 ambient air quality monitoring stations across Bengaluru, Karnataka, recording measurements at 15-minute intervals. The pollutants measured include PM2.5, PM10, NO₂, SO₂, CO, O₃, NH₃, NO, NOₓ, benzene, toluene, and meteorological variables (wind speed, wind direction, relative humidity, temperature, solar radiation, rainfall)."),

  body("Each station provides GPS coordinates (latitude, longitude) used both for spatial visualisation and as inputs to the Gaussian plume transport computation. The station-level data were merged into a single master dataset, partitioned by station identifier, and aligned on a common UTC timestamp index."),

  spacer(),
  ...figurePlaceholder(
    1, "Station Map — Bengaluru",
    "Geographic layout of the 14 CPCB monitoring stations. Markers coloured by mean annual PM2.5 level. Attach the station map image here."
  ),
  spacer(),

  // ─── III. STAGE 1 — IMPUTATION ─────────────────────────────────────────
  h1("III.  Stage 1 — Exploratory Data Analysis and Imputation"),

  h2("A.  Missing Data Analysis"),

  body("Before any modelling, the completeness of every column was quantified per station. A heatmap of percentage-missing (green → red) revealed that five pollutant columns exceeded 90% missingness across all stations: o_xylene, xylene, vertical_wind_speed, ethyl_benzene, and mp_xylene. These columns were dropped entirely, as imputing more than 90% of a column manufactures data rather than recovering it."),

  body("The remaining columns exhibit varying patterns of missingness driven by sensor downtime, calibration intervals, and network outages. Wind direction in particular showed extremely large gaps (≈100,000 null values) requiring specialised circular-interpolation treatment."),

  h2("B.  Imputation Strategy"),

  body("Imputation was applied per station independently to avoid introducing cross-station correlations. For each station, the time index was regularised to exactly 15-minute frequency using asfreq('15min'), inserting empty rows for any missing timestamps. The following priority-ordered strategy was then applied:"),

  // Imputation strategy table
  new Paragraph({ spacing: { before: 80, after: 40 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "TABLE I", font: "Times New Roman", size: 18, bold: true, allCaps: true })] }),
  new Paragraph({ spacing: { before: 0, after: 60 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Imputation Priority and Trigger Conditions", font: "Times New Roman", size: 18, italics: true })] }),

  new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [720, 2880, 3360, 2400],
    rows: [
      new TableRow({ children: [
        tableCell("Priority", true, "D5E8F0"),
        tableCell("Method", true, "D5E8F0"),
        tableCell("Trigger Condition", true, "D5E8F0"),
        tableCell("Column(s)", true, "D5E8F0"),
      ]}),
      new TableRow({ children: [tableCell("1"), tableCell("Forward Fill (ffill)"), tableCell("Cumulative nature"), tableCell("Rainfall")] }),
      new TableRow({ children: [tableCell("2"), tableCell("Circular Interpolation"), tableCell("Wrap-around 0–360°"), tableCell("wind_direction")] }),
      new TableRow({ children: [tableCell("3"), tableCell("Linear Interpolation"), tableCell("Gap ≤ 6 h (24 steps)"), tableCell("All numeric")] }),
      new TableRow({ children: [tableCell("4"), tableCell("1-hr Rolling Median"), tableCell("Isolated spikes"), tableCell("All numeric")] }),
      new TableRow({ children: [tableCell("5"), tableCell("Previous-Day Same Hour"), tableCell("Gap 6–48 hrs"), tableCell("All numeric")] }),
      new TableRow({ children: [tableCell("6"), tableCell("Previous-Week Same Hour"), tableCell("Gap 2–7 days"), tableCell("All numeric")] }),
      new TableRow({ children: [tableCell("7"), tableCell("Monthly × Hour Median"), tableCell("Gap > 7 days"), tableCell("All numeric")] }),
      new TableRow({ children: [tableCell("8"), tableCell("Column-Wide Median"), tableCell("Last resort"), tableCell("All numeric")] }),
    ]
  }),

  spacer(),

  h2("C.  Circular Interpolation of Wind Direction"),

  body("Wind direction is a circular variable in [0°, 360°). Naive linear interpolation produces physically incorrect results near the 0°/360° wrap boundary; for example, the midpoint between 350° and 10° should be 0°, not 180°. Circular interpolation resolves this by projecting angles onto the unit circle:"),

  formula("sin(θ), cos(θ)  →  linear interpolation  →  atan2(sin_interp, cos_interp)"),

  body("An interactive HTML visualisation was generated to help readers intuit the wrap-around behaviour and confirm that the imputed wind directions follow meteorologically realistic diurnal patterns."),

  h2("D.  Validation of Imputation"),

  body("Two validation steps were performed. First, an imputation log tracked exactly how many values each method filled for each column and station, enabling a stacked-bar summary of relative method usage. Second, distribution plots (violin + boxplot overlays) comparing the pre- and post-imputation distributions for every column at every station confirmed that the imputed values did not substantially alter the empirical distributions."),

  spacer(),
  ...figurePlaceholder(
    2, "Imputation Dashboard",
    "Four-panel: (a) fills by method, (b) fills by column (top 15), (c) station-level fills, (d) percentage of missing values reconstructed. Attach imputation dashboard image here."
  ),
  spacer(),

  // ─── IV. GAUSSIAN PLUME MODEL ──────────────────────────────────────────
  h1("IV.  Stage 2 — Gaussian Plume Transport Model"),

  h2("A.  Physical Model"),

  body("The Gaussian Plume Model (GPM) is the foundational analytical solution to the atmospheric diffusion equation under steady-state, homogeneous wind conditions [Seinfeld & Pandis, 2016]. The full three-dimensional ground-reflected concentration at a receptor (x, y, z) from a point source emitting at rate Q [g/s] with effective stack height H [m] under mean wind speed u [m/s] is:"),

  formula("C(x,y,z) = Q / (2π u σ_y σ_z)"),
  formula("  × exp(-y² / (2σ_y²))"),
  formula("  × [exp(-(z-H)² / (2σ_z²)) + exp(-(z+H)² / (2σ_z²))]"),

  body("At ground level (z = 0), the reflection term doubles and the formula simplifies to:"),

  formula("C(x,y,0) = (Q / (π u σ_y σ_z)) × exp(-y²/(2σ_y²)) × exp(-H²/(2σ_z²))"),

  bodyRuns([
    "where ",
    italic("σ_y"),
    " and ",
    italic("σ_z"),
    " are the lateral and vertical dispersion coefficients [m], parameterised using Pasquill–Gifford (P-G) stability class power laws:"
  ]),

  formula("σ_y(x) = a_y · x^(b_y)"),
  formula("σ_z(x) = a_z · x^(b_z)"),

  body("The P-G stability class (A through F) is determined from the wind speed and solar radiation at the source station, capturing the atmospheric turbulence regime (unstable convective conditions in class A to stable nocturnal conditions in class F)."),

  h2("B.  Inter-Station Geometry"),

  body("For every ordered pair of stations (source j → receptor i), the downwind distance x and the crosswind offset y are computed from GPS coordinates using the haversine great-circle formula:"),

  formula("d = 2R · arcsin(√(sin²(Δφ/2) + cos(φ₁)cos(φ₂)sin²(Δλ/2)))"),

  body("where R = 6,371,000 m is the Earth's mean radius. The wind bearing at the source station is then used to rotate the displacement vector into a wind-aligned frame, yielding the downwind distance x (parallel to wind) and crosswind offset y (perpendicular to wind)."),

  body("Physical validity bounds are enforced: wind speeds below 0.5 m/s are replaced by this calm-wind threshold (the P-G formulation diverges as u → 0), and downwind distances below 500 m are clamped (the power-law σ parameterisation was calibrated at x ≥ 500 m). The maximum σ_z is capped at 500 m to prevent unphysical near-zero dilution on long-range stable runs."),

  h2("C.  Transport Matrix Construction"),

  body("A single snapshot timestamp is selected for each analysis: the earliest time at which all 14 stations simultaneously report valid pollutant concentration, wind speed, and wind direction values. The transport matrix T is then built as:"),

  formula("T[i, j] = C(x_{ij}, y_{ij}, 0; u_j, WD_j, stab_j, H)  /  1   [µg m⁻³ g⁻¹ s]"),

  body("where the source index j drives the geometry computation and the receptor index i selects which element of the plume footprint is evaluated. The diagonal entries T[i,i] represent self-impact (local source → local receptor at zero offset), and are non-zero because the formulae are evaluated at the minimum safe distance."),

  spacer(),
  ...figurePlaceholder(
    3, "Transport Matrix and Station Wind Map",
    "Left: T matrix visualised on a log₁₀ colour scale (plasma palette); white cells indicate upwind/zero contribution. Right: Station map with wind vectors overlaid showing transport direction. Attach Figure 1 from notebook here."
  ),
  spacer(),
  ...figurePlaceholder(
    4, "NetworkX Transport Graph",
    "Directed graph of inter-station transport edges; edge thickness proportional to log₁₀(T[i,j]); red edges indicate active transport paths. Attach NetworkX graph here."
  ),
  spacer(),

  // ─── V. CLASSICAL INVERSION METHODS ─────────────────────────────────────
  h1("V.  Classical Source Inversion Methods"),

  body("Given the transport matrix T ∈ ℝᴺˣᴺ and the observed concentration vector C ∈ ℝᴺ, the objective is to recover the emission-rate vector Q ∈ ℝᴺ that best explains the observations. Four classical methods are compared below."),

  h2("A.  Least Squares (LSQ)"),

  body("The standard minimum-norm linear least-squares problem finds Q̂ that minimises the squared Euclidean residual:"),

  formula("Q̂_LSQ = argmin_{Q} ‖C − T·Q‖₂²"),
  formula("Solution: Q̂ = T⁺C = (TᵀT)⁻¹ TᵀC  (full-rank case)"),

  body("When T is ill-conditioned (high condition number κ(T) = σ_max/σ_min), the pseudoinverse amplifies measurement noise. Negative entries in Q̂ are physically invalid as emission rates cannot be negative, indicating model ill-posedness at this snapshot."),

  h2("B.  Non-Negative Least Squares (NNLS)"),

  body("NNLS adds the hard physical constraint Q ≥ 0 to the least-squares objective:"),

  formula("Q̂_NNLS = argmin_{Q ≥ 0} ‖C − T·Q‖₂²"),

  body("Implemented via the active-set algorithm (Lawson & Hanson, 1974), NNLS zeroes out stations with no attributed emission, yielding a sparse solution. Although the residual ‖C − TQ̂‖ is larger than unconstrained LSQ, the physically admissible solution is far more interpretable for pollution attribution."),

  h2("C.  Tikhonov Regularisation"),

  body("Tikhonov (L2) regularisation stabilises the inversion by penalising large-norm solutions:"),

  formula("Q̂_Tikh = argmin_{Q} { ‖C − T·Q‖₂² + λ‖Q‖₂² }"),
  formula("Closed form: Q̂ = (TᵀT + λI)⁻¹ TᵀC"),

  body("The regularisation parameter λ controls the bias–variance trade-off: large λ shrinks Q̂ toward zero (high bias, low variance), while small λ approaches the unregularised solution. An L-curve or cross-validation procedure can identify the optimal λ. In this work λ = 0.1 was used as a baseline."),

  h2("D.  Truncated Singular Value Decomposition (TSVD)"),

  body("TSVD constructs a rank-k pseudoinverse by retaining only singular values above a threshold ratio r = σ_k / σ_max:"),

  formula("T = U Σ Vᵀ  (full SVD)"),
  formula("T⁺_k = V_k Σ_k⁻¹ Uₖᵀ  (truncated pseudoinverse)"),
  formula("Q̂_SVD = T⁺_k · C"),

  body("Singular values encoding measurement noise are eliminated, yielding a smooth, physically regular solution. The default threshold ratio is 10⁻³, meaning any singular value less than 0.1% of the largest is zeroed out."),

  h2("E.  Comparison Table"),

  new Paragraph({ spacing: { before: 80, after: 40 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "TABLE II", font: "Times New Roman", size: 18, bold: true, allCaps: true })] }),
  new Paragraph({ spacing: { before: 0, after: 60 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Classical Solver Comparison: Residual ‖C − TQ‖₂", font: "Times New Roman", size: 18, italics: true })] }),

  new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [2160, 2400, 2400, 2400],
    rows: [
      new TableRow({ children: [
        tableCell("Method", true, "D5E8F0"),
        tableCell("Constraint", true, "D5E8F0"),
        tableCell("Residual ‖C−TQ‖", true, "D5E8F0"),
        tableCell("Negative Q", true, "D5E8F0"),
      ]}),
      new TableRow({ children: [tableCell("LSQ"), tableCell("None"), tableCell("[attach value]"), tableCell("Possible")] }),
      new TableRow({ children: [tableCell("NNLS"), tableCell("Q ≥ 0"), tableCell("[attach value]"), tableCell("None ✓")] }),
      new TableRow({ children: [tableCell("Tikhonov"), tableCell("L2 penalty"), tableCell("[attach value]"), tableCell("Possible")] }),
      new TableRow({ children: [tableCell("Trunc. SVD"), tableCell("Rank truncation"), tableCell("[attach value]"), tableCell("Possible")] }),
    ]
  }),

  spacer(),
  ...figurePlaceholder(
    5, "Classical Solver Attribution",
    "Four-panel figure: (a) emission Q per station per method, (b) residual norms, (c) condition number analysis, (d) observed vs reconstructed C for each solver. Attach Figure 2 from notebook."
  ),
  spacer(),
  ...figurePlaceholder(
    6, "Observed vs Reconstructed Concentrations",
    "Bar chart comparing observed C and reconstructed C = TQ for all four classical methods across 14 stations. Attach Figure 4 from notebook here."
  ),
  spacer(),

  // ─── VI. BAYESIAN INFERENCE ──────────────────────────────────────────────
  h1("VI.  Bayesian Inference"),

  h2("A.  Motivation"),

  body("Classical methods return point estimates of Q with no measure of uncertainty. Bayesian inference instead recovers the full posterior distribution p(Q | C, T), providing credible intervals that reflect both measurement noise and model uncertainty. This is critical for policy decisions where the analyst must communicate confidence bounds alongside attribution estimates."),

  h2("B.  Prior Formulation"),

  body("Emission rates must be non-negative. A HalfNormal prior is placed on each Q_i:"),

  formula("Q_i ~ HalfNormal(σ = 2)    for i = 1, …, N"),

  body("Alternatively, a log-normal prior enforces Q > 0 and captures the heavy-tailed, right-skewed nature of urban emission distributions:"),

  formula("Q_i ~ LogNormal(μ₀, σ₀²)"),
  formula("log p(Q_i) = −(log Q_i − μ₀)² / (2σ₀²) − log Q_i − log σ₀ − log√(2π)"),

  h2("C.  Likelihood"),

  body("Assuming additive Gaussian observation noise with standard deviation σ_C, the likelihood of the observed concentration vector is:"),

  formula("C | Q, T ~ Normal(T·Q, σ_C²·I)"),
  formula("log p(C | Q) = −‖C − T·Q‖₂² / (2σ_C²) − (N/2) log(2πσ_C²)"),

  h2("D.  Posterior and MCMC Sampling"),

  body("By Bayes' theorem, the posterior is proportional to the product of likelihood and prior:"),

  formula("p(Q | C, T) ∝ p(C | Q, T) · p(Q)"),

  body("The posterior is sampled using PyMC's No-U-Turn Sampler (NUTS), a gradient-based Hamiltonian Monte Carlo variant that is efficient in moderate dimensions (N = 14). For numerical stability, the transport matrix and observations are normalised (T_norm = T / T_max, C_norm = C / C_max) before sampling. Posterior samples are rescaled back to physical units as:"),

  formula("Q_physical = Q_sampled × (C_max / T_max)    [g/s]"),

  body("Convergence is assessed using the Gelman-Rubin statistic R̂ (target < 1.01) and the bulk effective sample size ESS (target > 400)."),

  h2("E.  MAP Estimate vs Posterior Mean"),

  body("Two point summaries are reported: the Maximum A Posteriori (MAP) estimate (mode of the posterior) and the posterior mean. The MAP estimate minimises the combined regularised loss:"),

  formula("Q̂_MAP = argmax_Q { log p(C|Q) + log p(Q) }"),

  body("which is equivalent to Tikhonov regularisation when the prior is Gaussian. The posterior mean accounts for the full shape of the distribution and is generally more robust under skewed priors."),

  spacer(),
  ...figurePlaceholder(
    7, "Bayesian Posterior — Emission Rates",
    "Left: Horizontal bar chart of posterior mean Q with 90% credible intervals (whiskers); NNLS point estimates overlaid as diamonds. Right: Posterior predictive check comparing T·Q_posterior with observed C. Attach Figure 3 from notebook."
  ),
  spacer(),
  ...figurePlaceholder(
    8, "MCMC Trace Plots",
    "Trace and density plots for the first 6 Q parameters showing chain mixing and posterior shape. Attach trace plot from notebook."
  ),
  spacer(),

  // ─── VII. DEEP LEARNING ──────────────────────────────────────────────────
  h1("VII.  Stage 3 — Deep Learning Attribution"),

  h2("A.  Motivation and Framing"),

  body("Classical inversion methods operate on a single snapshot timestamp at a time. They cannot capture temporal dynamics—diurnal cycles, weather fronts, weekly traffic patterns—that govern how pollution propagates across a city over time. Recurrent neural networks, in particular Long Short-Term Memory (LSTM) architectures, are well-suited for learning these dynamics directly from multi-station time-series data."),

  body("Two architectures are compared: a Baseline LSTM that directly predicts observed concentrations C from a window of past observations, and a Physics-Informed LSTM that predicts the latent emission-rate vector Q̂, then reconstructs concentrations through the forward model C_pred = T · Q̂."),

  h2("B.  Sequence Dataset Construction"),

  body("The master dataset is pivoted into a wide table of shape (T_timesteps × N_stations). A sliding window of length L = 24 timesteps (6 hours at 15-minute frequency) is used to create input sequences X ∈ ℝ^(L×N). Labels for the Baseline LSTM are the concentration vectors C ∈ ℝᴺ at the next timestep. Labels for the Physics-Informed LSTM are the NNLS-derived emission rates Q̂ ∈ ℝᴺ."),

  body("The dataset is split 70% training / 15% validation / 15% test, with no shuffling to preserve temporal order and avoid data leakage. All features are standardised (zero mean, unit variance) using statistics computed only on the training split."),

  h2("C.  LSTM Architecture"),

  body("Both models share a common LSTM encoder:"),

  formula("h_t, c_t = LSTM(x_t, h_{t-1}, c_{t-1})"),
  formula("ŷ = W_out · h_T + b_out"),

  body("Configuration: hidden dimension = 128, 2 stacked LSTM layers, dropout = 0.15 between layers. The output head is a fully connected layer projecting from hidden_dim to N (number of stations). For the Physics-Informed model, a ReLU activation is added at the output to enforce Q ≥ 0, and the loss is computed on the reconstructed concentration rather than the raw prediction:"),

  formula("L_physics = ‖C_obs − T · LSTM(X)‖₂²"),
  formula("L_baseline = ‖C_obs − LSTM(X)‖₂²"),

  h2("D.  Training"),

  body("Both models are trained for up to 40 epochs using the Adam optimiser (lr = 10⁻³, weight decay = 10⁻⁵) with early stopping based on validation loss (patience = 8 epochs). The learning rate is not yet decayed; a ReduceLROnPlateau scheduler is planned for future runs."),

  h2("E.  Evaluation Metrics"),

  body("Model performance is evaluated on the held-out test split using three metrics:"),

  formula("MAE  = (1/N) Σᵢ |C_obs,i − C_pred,i|"),
  formula("RMSE = √[(1/N) Σᵢ (C_obs,i − C_pred,i)²]"),
  formula("R²   = 1 − Σ(C_obs − C_pred)² / Σ(C_obs − C̄_obs)²"),

  spacer(),
  ...figurePlaceholder(
    9, "LSTM Training and Validation Loss Curves",
    "Two-panel: baseline LSTM (left) and physics-informed LSTM (right). X-axis: epoch; Y-axis: MSE loss. Attach training curve plots."
  ),
  spacer(),
  ...figurePlaceholder(
    10, "Predicted vs Observed Concentrations — LSTM",
    "Scatter plots of C_pred vs C_obs for both LSTM variants across the test set. Attach scatter comparison figure."
  ),
  spacer(),

  h2("F.  Comparative Analysis Roadmap"),

  body("The following table provides a suggested comparative roadmap from baseline to state-of-the-art methods, representing the planned progression of this research:"),

  new Paragraph({ spacing: { before: 80, after: 40 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "TABLE III", font: "Times New Roman", size: 18, bold: true, allCaps: true })] }),
  new Paragraph({ spacing: { before: 0, after: 60 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Deep Learning Methods — Baseline to Advanced", font: "Times New Roman", size: 18, italics: true })] }),

  new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [1800, 2800, 2400, 2360],
    rows: [
      new TableRow({ children: [
        tableCell("Level", true, "D5E8F0"),
        tableCell("Method", true, "D5E8F0"),
        tableCell("Key Strength", true, "D5E8F0"),
        tableCell("Status", true, "D5E8F0"),
      ]}),
      new TableRow({ children: [tableCell("Baseline"), tableCell("Vanilla LSTM"), tableCell("Temporal memory"), tableCell("Implemented ✓")] }),
      new TableRow({ children: [tableCell("Baseline"), tableCell("Physics-Informed LSTM"), tableCell("Forward model constraint"), tableCell("Implemented ✓")] }),
      new TableRow({ children: [tableCell("Intermediate"), tableCell("Temporal Convolutional Net (TCN)"), tableCell("Parallel dilated conv, fast"), tableCell("Planned")] }),
      new TableRow({ children: [tableCell("Intermediate"), tableCell("Transformer (Attention)"), tableCell("Long-range dependency"), tableCell("Planned")] }),
      new TableRow({ children: [tableCell("Advanced"), tableCell("Spatial GCN + LSTM"), tableCell("Graph topology encoding"), tableCell("Planned")] }),
      new TableRow({ children: [tableCell("Advanced"), tableCell("Diffusion GNN (DCRNN)"), tableCell("Directed transport graph"), tableCell("Planned")] }),
      new TableRow({ children: [tableCell("Advanced"), tableCell("Physics-Informed GNN"), tableCell("T matrix as edge weights"), tableCell("Planned")] }),
    ]
  }),

  spacer(),

  body("GNN-based methods are particularly well-motivated for this problem: the directed Gaussian plume transport graph provides a natural and physically meaningful edge structure that can be wired directly into a DCRNN or GraphSAGE encoder. The edge weight T[i,j] quantifies how strongly source j influences receptor i, providing richer spatial inductive bias than a purely data-driven adjacency matrix."),

  // ─── VIII. DISCUSSION ─────────────────────────────────────────────────────
  h1("VIII.  Discussion"),

  body("Several observations emerged from the classical inversion experiments. First, the transport matrix T exhibits high condition number κ(T) ≫ 1, meaning small noise in C is amplified into large errors in Q when using unconstrained methods. This motivates the use of regularisation (Tikhonov, TSVD) or physical constraints (NNLS) in practice."),

  body("Second, Bayesian inference provides the most complete picture: beyond point estimates, credible intervals identify stations where the emission-rate attribution is uncertain (wide intervals) versus well-constrained (narrow intervals). Stations upwind of most others tend to have wider intervals as their contribution is diffused across many receptors, making inversion harder."),

  body("Third, the physics-informed LSTM benefits from the explicit incorporation of the transport model: even early in training, the model's predictions respect the spatial structure of pollution transport, whereas the baseline LSTM treats all stations as exchangeable inputs."),

  h2("A.  Limitations and Future Work"),

  body("The current framework has several limitations. The Gaussian plume model assumes steady-state wind and flat terrain, neither of which holds exactly in Bengaluru's complex urban topography. Future work will integrate a diagnostic wind-field model (e.g., CALMET) to account for street-canyon channelling and topographic blocking. Additionally, the single-snapshot transport matrix should be replaced by a time-varying T(t) computed at each 15-minute step to capture changing wind conditions. Finally, the source term model currently treats each monitoring station as a point source; a more realistic treatment would distribute emissions across census-derived spatial grids of traffic density, industrial activity, and construction sites."),

  // ─── IX. CONCLUSION ─────────────────────────────────────────────────────
  h1("IX.  Conclusion"),

  body("This paper has presented an end-to-end pipeline for air-pollution attribution across 14 urban monitoring stations in Bengaluru. Beginning with robust multi-strategy imputation of 15-minute CPCB data, the pipeline constructs a physics-derived Gaussian plume transport matrix and applies classical (LSQ, NNLS, Tikhonov, TSVD) and Bayesian inversion methods to attribute observed PM2.5 concentrations to station-level emission sources. A physics-informed LSTM extends this attribution to the temporal domain."),

  body("The framework is modular and extensible: additional pollution sources (vehicular traffic, construction, biomass burning) can be incorporated as additional columns in the emission vector Q, and GNN-based architectures can replace the LSTM to exploit the spatial structure of the transport graph. Together, these advances move toward a comprehensive, uncertainty-aware urban air-quality attribution system."),

  spacer(),

  // ─── ACKNOWLEDGMENT ─────────────────────────────────────────────────────
  h1("Acknowledgment"),
  body("The authors gratefully acknowledge the Central Pollution Control Board (CPCB), India, for making air quality monitoring data publicly available."),

  spacer(),

  // ─── REFERENCES ─────────────────────────────────────────────────────────
  h1("References"),

  ...[
    "[1] J. H. Seinfeld and S. N. Pandis, Atmospheric Chemistry and Physics: From Air Pollution to Climate Change, 3rd ed. Wiley, 2016.",
    "[2] F. Pasquill and F. B. Smith, Atmospheric Diffusion, 3rd ed. Ellis Horwood, 1983.",
    "[3] D. B. Turner, Workbook of Atmospheric Dispersion Estimates, EPA, 1970.",
    "[4] C. L. Lawson and R. J. Hanson, Solving Least Squares Problems. SIAM, 1995.",
    "[5] A. N. Tikhonov and V. Y. Arsenin, Solutions of Ill-Posed Problems. Winston, 1977.",
    "[6] A. Gelman et al., Bayesian Data Analysis, 3rd ed. CRC Press, 2013.",
    "[7] S. Hochreiter and J. Schmidhuber, 'Long short-term memory,' Neural Computation, vol. 9, no. 8, pp. 1735–1780, 1997.",
    "[8] Y. Li et al., 'Diffusion convolutional recurrent neural network: Data-driven traffic forecasting,' ICLR, 2018.",
    "[9] Central Pollution Control Board (CPCB), India. National Ambient Air Quality Monitoring Programme. [Online]. Available: https://cpcb.nic.in/",
  ].map(ref => new Paragraph({
    spacing: { before: 40, after: 40 },
    indent: { left: 360, hanging: 360 },
    children: [new TextRun({ text: ref, font: "Times New Roman", size: 18 })]
  })),
];

// ─── DOCUMENT ASSEMBLY ────────────────────────────────────────────────────────

const doc = new Document({
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  styles: {
    default: {
      document: { run: { font: "Times New Roman", size: 20 } }
    },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Times New Roman" },
        paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, italics: true, font: "Times New Roman" },
        paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 20, bold: true, font: "Times New Roman" },
        paragraph: { spacing: { before: 160, after: 60 }, outlineLevel: 2 } },
    ]
  },
  sections: [
    // Section 1: Title (single column)
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1080, bottom: 1440, left: 1080 }
        }
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "444444", space: 1 } },
            spacing: { before: 0, after: 120 },
            children: [new TextRun({ text: "Air Pollution Attribution — CPCB Bengaluru 2025", font: "Times New Roman", size: 18, italics: true })]
          })]
        })
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ text: "Page ", font: "Times New Roman", size: 18 }),
              new TextRun({ children: [PageNumber.CURRENT], font: "Times New Roman", size: 18 }),
            ]
          })]
        })
      },
      children: titleContent,
    },
    // Section 2: Two-column body
    {
      properties: {
        type: SectionType.CONTINUOUS,
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1080, bottom: 1440, left: 1080 }
        },
        column: {
          count: 2,
          space: 720,
          equalWidth: true,
          separate: true,
        }
      },
      children: bodyContent,
    }
  ]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("Air_Pollution_Attribution.docx", buf);
  console.log("Done: Air_Pollution_Attribution.docx");
});