# Geotechnical Laboratory Tests in BRO

## Overview

This document describes the 12 determination types in **BHR-GT-BMA** (Boormonsteranalyse - Borehole Sample Analysis), part of the Dutch BRO (Basisregistratie Ondergrond) geotechnical borehole investigation standard.

BHR-GT-BMA contains laboratory measurements on extracted soil samples, complementing the visual descriptions in BHR-GT-BMB. These tests are critical for foundation design, settlement calculations, and geotechnical engineering.

## The 12 Determination Types

### 1. Water Content (Watergehalte)

**Purpose:** Measure moisture content as percentage of dry soil weight

**Data Structure:**
- 6 primary fields
- Complex nested `determinationResult`
- Multiple result values possible
- Drying temperature and period specifications
- Salt correction methods

**Charts & Visualizations:**
- **Depth Profile Chart**: Water content (%) vs. depth (m)
- **Bar Chart**: Comparison across multiple samples
- Usually single values, but can show variation with depth

---

### 2. Organic Matter Content (Organischestofgehalte)

**Purpose:** Determine percentage of organic material in soil

**Data Structure:**
- 7 primary fields
- Determination procedure and method codes
- Lutum correction flags
- Performance irregularities tracking

**Charts & Visualizations:**
- **Depth Profile Chart**: Organic content (%) vs. depth (m)
- **Bar Chart**: Horizontal bars showing organic content ranges
- Color-coded classification bands (low/medium/high)

---

### 3. Carbonate Content (Kalkgehalte)

**Purpose:** Measure calcium carbonate (limestone/chalk) content

**Data Structure:**
- Percentage measurements
- Procedure codes
- Material irregularities

**Charts & Visualizations:**
- **Depth Profile Chart**: CaCO₃ content (%) vs. depth (m)
- **Classification Diagram**: Zones showing calcareous soil categories
- Often combined with other soil properties

---

### 4. Volumetric Mass Density (Volumieke Massa - Bulk Density)

**Purpose:** Measure total mass per unit volume of soil (including pores)

**Data Structure:**
- Density values in g/cm³ or kg/m³
- Sample preparation methods
- Measurement procedures

**Charts & Visualizations:**
- **Depth Profile Chart**: Density (g/cm³ or kg/m³) vs. depth
- **Scatter Plot**: Correlation with water content
- Reference lines for typical soil types

---

### 5. Volumetric Mass Density of Solids (Volumieke massa Vaste delen - Specific Gravity)

**Purpose:** Measure mass per unit volume of solid particles only (excluding pores)

**Data Structure:**
- Particle density values
- Usually 2.60-2.75 g/cm³ for most soils
- Testing method specifications

**Charts & Visualizations:**
- **Bar Chart**: Comparing different soil layers
- **Histogram**: Distribution of particle densities
- Usually narrow range (2.60-2.75 g/cm³ for most soils)

---

### 6. Particle Size Distribution (Korrelgrootteverdeling) ⭐ MAJOR TEST

**Purpose:** Determine grain size distribution from gravel to clay

**Data Structure:**
- 11 primary fields
- Complex nested structures
- Multiple fraction distributions
- Optical models for fine particles
- Grain size curve data arrays (multiple measurement points)
- Dispersion method specifications
- Equivalent mass calculations

**Charts & Visualizations:**

**Primary: [Grain Size Distribution Curve](https://elementaryengineeringlibrary.com/civil-engineering/soil-mechanics/particle-size-distribution-curve/)**
- **X-axis**: Grain size (mm) on **logarithmic scale**
  - Range: 0.001 mm (clay) to 100 mm (gravel)
- **Y-axis**: Percent finer by weight (0-100%)
- Classic S-curve shape
- Shows gravel/sand/silt/clay boundaries:
  - Gravel: > 2 mm
  - Sand: 0.063 - 2 mm
  - Silt: 0.002 - 0.063 mm
  - Clay: < 0.002 mm

**Key Parameters Derived:**
- **D₁₀**: Effective size (10% passing)
- **D₃₀**: 30% passing size
- **D₆₀**: 60% passing size
- **Coefficient of Uniformity**: Cᵤ = D₆₀/D₁₀
  - Well-graded: Cᵤ > 4 (sand), Cᵤ > 6 (gravel)
- **Coefficient of Curvature**: Cᴄ = D₃₀²/(D₁₀×D₆₀)
  - Well-graded: 1 < Cᴄ < 3

**Soil Classification:**
- Well-graded: Wide range of particle sizes
- Poorly-graded: Narrow range (uniform) or gap-graded
- Used for USCS and AASHTO soil classification

**Data Format:** Array of (grain size, percent finer) pairs

---

### 7. Maximum Undrained Shear Strength (Ongedraineerde schuifsterkte)

**Purpose:** Measure shear strength when drainage is not allowed (undrained conditions)

**Data Structure:**
- Shear strength values in kPa
- Test procedure specifications
- Specimen preparation methods

**Charts & Visualizations:**
- **Depth Profile Chart**: Shear strength (kPa) vs. depth (m)
- **Bar Chart**: Strength values for different layers
- Reference lines for design values
- Typical range: 10-200 kPa for soft to stiff clays

---

### 8. Settlement Characteristics (Zettingseigenschappen) ⭐ MAJOR TEST

**Purpose:** Determine soil compressibility and consolidation behavior

**Data Structure:**
- **Arrays of measurement points** (5-20 steps)
- Each step contains:
  - Step number
  - Vertical stress (kPa)
  - Height change time series (DataArray format)
- Uses SWE (Sensor Web Enablement) DataArray encoding
- 3 levels of nesting: Determination → Step → DataArray

**Charts & Visualizations:**

**Primary: Consolidation Curve (e-log-p)**
- **X-axis**: Effective stress (kPa) on **logarithmic scale**
  - Range: 10-10,000 kPa typical
- **Y-axis**: Void ratio (e) or strain (%)
- Shows three regions:
  1. **Recompression curve**: Soil has been loaded before
  2. **Virgin compression line**: First-time loading
  3. **Unloading/reloading**: If stress is reduced

**Key Parameters Identified:**
- **Compression Index (Cᴄ)**: Slope of virgin compression line
  - Cᴄ = Δe / Δlog(σ')
  - Higher Cᴄ = more compressible soil
- **Recompression Index (Cᵣ)**: Slope of recompression line
  - Typically Cᵣ ≈ Cᴄ/10
- **Preconsolidation Pressure (σ'ₚ)**: Maximum past pressure
  - Determines if soil is overconsolidated

**Secondary: Time-Settlement Curve**
- **X-axis**: Time (minutes, hours) often on log scale
- **Y-axis**: Settlement (mm) or dial reading
- Shows:
  - **Primary consolidation**: Pore water expulsion
  - **Secondary consolidation**: Creep/viscous effects
- Used to determine coefficient of consolidation (Cᵥ)

**Engineering Use:** Calculate settlement magnitude and time for foundations on clay

---

### 9. Consistency Limits (Consistentiegrenzen - Atterberg Limits) ⭐ MAJOR TEST

**Purpose:** Define water contents at transitions between soil consistency states

**Data Structure:**
- Liquid Limit (LL): Water content at liquid-plastic boundary
- Plastic Limit (PL): Water content at plastic-semisolid boundary
- Plasticity Index (PI): Calculated as LL - PL
- Determination procedures
- Performance irregularities

**Charts & Visualizations:**

**Primary: Casagrande Plasticity Chart**
- **X-axis**: Liquid Limit (LL) in % (range 0-100+)
- **Y-axis**: Plasticity Index (PI) in % (range 0-60+)
- **A-line**: Empirical boundary PI = 0.73(LL - 20)
  - Above A-line: **Clays (C)**
  - Below A-line: **Silts (M)**
- **Vertical line at LL = 50**: Divides low/high plasticity
  - LL < 50: **Low plasticity (L)**
  - LL ≥ 50: **High plasticity (H)**

**Soil Classification Zones:**
- **CL**: Clay of Low plasticity (lean clay)
- **CH**: Clay of High plasticity (fat clay)
- **ML**: Silt of Low plasticity
- **MH**: Silt of High plasticity (elastic silt)

**Secondary: Flow Curve** (for liquid limit determination)
- **X-axis**: Number of blows (log scale)
- **Y-axis**: Water content (%)
- Linear relationship used to find LL at 25 blows

**Engineering Use:**
- USCS soil classification
- Estimate soil behavior (shrink-swell potential, compressibility)
- Correlations with other properties

---

### 10. Shear Stress During Loading (Triaxial Test) ⭐ MAJOR TEST

**Purpose:** Measure stress-strain behavior and shear strength under controlled conditions

**Data Structure:**
- **Array data** for stress-strain curves
- Single LoadStageType containing:
  - Deformation rate (mm/h)
  - Specimen shape
  - DataArray of stress-strain points
- 2 levels of nesting: Determination → LoadStage → DataArray
- Multiple test types (UU, CU, CD)

**Charts & Visualizations:**

**Primary: [Stress-Strain Curve](https://uta.pressbooks.pub/soilmechanics/chapter/triaxial-test/)**
- **X-axis**: Axial strain (εₐ) in % (range 0-20%)
- **Y-axis**: Deviator stress (σ₁ - σ₃) in kPa
- Multiple curves for different confining pressures (σ₃)
  - Typical: 50, 100, 200, 400 kPa
- Curve shapes indicate behavior:
  - **Peak then drop**: Dense/overconsolidated (strain-softening)
  - **Gradual rise to plateau**: Loose/normally consolidated (strain-hardening)

**Secondary: [Mohr Circle Diagram](https://www.researchgate.net/figure/Mohr-circle-diagram-for-UU-triaxial-test_fig1_252857460)**
- **X-axis**: Normal stress (σ) in kPa
- **Y-axis**: Shear stress (τ) in kPa
- **Mohr circles**: One for each confining pressure
  - Circle diameter = σ₁ - σ₃ (deviator stress at failure)
  - Circle center = (σ₁ + σ₃) / 2
- **Mohr-Coulomb Failure Envelope**: τ = c + σ tan(φ)
  - **Tangent line** to circles gives strength parameters:
  - **c**: Cohesion (y-intercept) in kPa
  - **φ**: Friction angle (slope angle) in degrees

**Tertiary: p-q Plot** (advanced analysis)
- **X-axis**: Mean effective stress p' = (σ₁' + 2σ₃') / 3
- **Y-axis**: Deviator stress q = σ₁' - σ₃'
- Shows critical state line
- Used for advanced constitutive modeling

**Test Variations:**
- **UU (Unconsolidated Undrained)**: Quick, total stress analysis
- **CU (Consolidated Undrained)**: With pore pressure measurement
- **CD (Consolidated Drained)**: Slow test, effective stress analysis

**Engineering Use:**
- Foundation bearing capacity
- Slope stability analysis
- Earth pressure calculations
- Soil constitutive modeling

---

### 11. Shear Stress During Horizontal Deformation (Direct Shear Test)

**Purpose:** Measure shear strength along a predetermined failure plane

**Data Structure:**
- Shear stress vs. displacement arrays
- Normal stress specifications
- Peak and residual strength values
- Volume change data (for drained tests)

**Charts & Visualizations:**

**Primary: Shear Stress vs. Displacement Curve**
- **X-axis**: Horizontal displacement (mm) (range 0-10 mm typical)
- **Y-axis**: Shear stress (τ) in kPa
- Multiple curves for different normal loads (σₙ)
  - Typical: 50, 100, 200 kPa
- Curve behavior:
  - **Dense soils**: Peak τ then drop to residual
  - **Loose soils**: Gradual rise to ultimate τ
- Shows:
  - **Peak strength**: Maximum resistance
  - **Residual strength**: Long-term strength after large displacement

**Secondary: Shear Strength Envelope**
- **X-axis**: Normal stress (σₙ) in kPa
- **Y-axis**: Peak shear strength (τₚₑₐₖ) in kPa
- Plot points from multiple tests at different σₙ
- **Linear fit**: τ = c + σₙ tan(φ)
  - **c**: Cohesion intercept
  - **φ**: Friction angle (slope)
- Separate envelopes for peak and residual strengths

**Tertiary: Volume Change Curve** (drained tests only)
- **X-axis**: Horizontal displacement (mm)
- **Y-axis**: Vertical displacement (mm)
  - Positive: Dilation (expansion)
  - Negative: Contraction (compression)
- Dense sands dilate, loose sands contract

**Engineering Use:**
- Simpler alternative to triaxial test
- Retaining wall design
- Foundation sliding resistance
- Residual strength for landslide analysis

---

### 12. Saturated Permeability (Verzadigde waterdoorlatendheid)

**Purpose:** Measure hydraulic conductivity (water flow rate through saturated soil)

**Data Structure:**
- Permeability values in m/s or cm/s
- Test method specifications (constant head, falling head)
- Temperature corrections
- Hydraulic gradient used

**Charts & Visualizations:**

**Primary: Depth Profile Chart**
- **X-axis**: Permeability (k) in m/s on **logarithmic scale**
  - Range spans 8+ orders of magnitude: 10⁻² to 10⁻¹⁰ m/s
- **Y-axis**: Depth (m)
- Shows dramatic variations with soil type

**Secondary: Classification Diagram**
- Horizontal bars showing permeability ranges by soil type:
  - **Gravel**: 10⁻² to 10⁻⁴ m/s (high permeability)
  - **Clean sand**: 10⁻⁴ to 10⁻⁶ m/s
  - **Silty sand**: 10⁻⁵ to 10⁻⁷ m/s
  - **Silt**: 10⁻⁶ to 10⁻⁸ m/s
  - **Clay**: 10⁻⁸ to 10⁻¹⁰ m/s (very low permeability)
- Color-coded zones for drainage characteristics

**Drainage Classifications:**
- **k > 10⁻⁴ m/s**: Free-draining
- **10⁻⁶ < k < 10⁻⁴ m/s**: Slow drainage
- **k < 10⁻⁶ m/s**: Poor drainage (practically impervious)

**Engineering Use:**
- Groundwater flow modeling
- Dewatering system design
- Consolidation rate calculations
- Seepage analysis for dams/levees
- Landfill liner design

---

## Summary Table

| # | Determination | Primary Chart Type | Data Complexity | Log Scale? | Array Data? |
|---|--------------|-------------------|-----------------|------------|-------------|
| 1 | Water Content | Depth profile | Low | No | No |
| 2 | Organic Matter | Depth profile | Low | No | No |
| 3 | Carbonate Content | Depth profile | Low | No | No |
| 4 | Bulk Density | Depth profile | Low | No | No |
| 5 | Specific Gravity | Bar chart | Low | No | No |
| 6 | **Particle Size** ⭐ | **Grain size curve** | High | **Yes (X)** | **Yes** |
| 7 | Undrained Strength | Depth profile | Low | No | No |
| 8 | **Settlement** ⭐ | **e-log-p curve** | Very High | **Yes (X)** | **Yes (time-series)** |
| 9 | **Atterberg Limits** ⭐ | **Plasticity chart** | Medium | No | No |
| 10 | **Triaxial Test** ⭐ | **Stress-strain + Mohr** | Very High | No | **Yes** |
| 11 | Direct Shear | Stress-displacement | Medium | No | Yes |
| 12 | Permeability | Depth profile | Low | **Yes (X)** | No |

**Legend:**
- ⭐ = Major test with complex, multi-parameter charts
- High/Very High complexity = Multiple nested structures, array data, specialized chart types
- Log Scale = Requires logarithmic axis for proper visualization
- Array Data = Contains time-series or multi-point measurement arrays

---

## Implementation Considerations

### Why BHR-GT-BMA is Complex

1. **Schema Size**: 180+ complex type definitions, 200+ total types
2. **Nested Structures**: 2-3 levels deep with complex parent-child relationships
3. **Array Handling**: Multiple tests use SWE DataArray format (similar to CPT CSV encoding)
4. **Scientific Precision**: Extensive metadata about procedures, methods, irregularities
5. **Unit Management**: Multiple unit systems (kPa, MPa, mm, m, %, g/cm³)
6. **Optional Fields**: Many determinations have 5-10+ optional sub-elements

### Estimated Implementation Effort

- **TypeScript Interfaces**: 100-150 lines (12 determination types + nested structures)
- **Simple Determinations** (1-5, 7): 30-50 lines each = 150-250 lines
- **Medium Determinations** (11, 12): 50-80 lines each = 100-160 lines
- **Complex Determinations** (6, 9): 80-120 lines each = 160-240 lines
- **Very Complex** (8, 10): 150-200 lines each = 300-400 lines
- **Tests**: 200-300 lines
- **Resolver Infrastructure**: 150-200 lines

**Total Estimate: 1,500-2,000 lines of code**

### Critical Features Needed

1. **SWE DataArray Parser**: Handle encoded array data (grain size curves, consolidation data)
2. **Unit Conversion**: Support multiple unit systems with proper conversions
3. **Validation**: Check for required determinations, proper nesting, valid ranges
4. **Metadata Handling**: Capture procedures, methods, irregularities for each test
5. **Array Resolvers**: Parse multi-point measurement data for charts

---

## Chart Generation

While this library focuses on **parsing** BRO XML data, generating the charts listed above would typically be done by:

1. **Frontend Visualization Libraries**:
   - [Chart.js](https://www.chartjs.org/) - General purpose
   - [Plotly.js](https://plotly.com/javascript/) - Scientific charts with log scales
   - [D3.js](https://d3js.org/) - Custom, complex visualizations
   - [Recharts](https://recharts.org/) - React-based charts

2. **Geotechnical-Specific Tools**:
   - Custom renderers for Mohr circles
   - Specialized grain size curve generators
   - Plasticity chart templates with A-line

3. **Data Export**:
   - Export parsed data to CSV for Excel/Google Sheets
   - JSON output for web applications
   - Integration with GIS tools (QGIS, ArcGIS)

---

## References

### Web Resources
- [Grain Size Analysis Guide - Geoengineer.org](https://www.geoengineer.org/education/laboratory-testing/step-by-step-guide-for-grain-size-analysis)
- [Particle Size Distribution Curve - Elementary Engineering](https://elementaryengineeringlibrary.com/civil-engineering/soil-mechanics/particle-size-distribution-curve/)
- [Triaxial Test - Online Lab Manual](https://uta.pressbooks.pub/soilmechanics/chapter/triaxial-test/)
- [Triaxial Shear Test - Elementary Engineering](https://elementaryengineeringlibrary.com/civil-engineering/soil-mechanics/triaxial-shear-test/)
- [Mohr Circle Diagram - ResearchGate](https://www.researchgate.net/figure/Mohr-circle-diagram-for-UU-triaxial-test_fig1_252857460)

### BRO Schemas
- [BRO Services - dsbhr-gt/2.1](https://schema.broservices.nl/xsd/dsbhr-gt/2.1/)
- [BRO Common - bhrgtcommon/2.1](https://schema.broservices.nl/xsd/bhrgtcommon/2.1/)
- [BRO Documentation](https://basisregistratieondergrond.nl/)

### Standards Referenced
- **ISO 14688**: Geotechnical investigation and testing (soil classification)
- **ISO 17892**: Laboratory testing of soil (test procedures)
- **ASTM D422**: Particle-Size Analysis of Soils
- **ASTM D2487**: Unified Soil Classification System (USCS)
- **ASTM D4318**: Liquid Limit, Plastic Limit, and Plasticity Index
- **ASTM D2435**: One-Dimensional Consolidation
- **ASTM D2850**: Unconsolidated-Undrained Triaxial
- **NEN 5104**: Dutch soil classification system (geological)
