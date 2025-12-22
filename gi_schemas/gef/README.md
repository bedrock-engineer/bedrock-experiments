# GEF Specification Data (JSON Format)

This directory contains GEF (Geotechnical Exchange Format) CPT and BORE specification data from the offical spec PDF's exported to JSON format.
GEF-DISS (Dissipation Test) and GEF-SIEVE (Soil Sieve Analysis) are not documented.

## Directory Structure

## Common Specification Files

Located in `common/` - Used by both BORE and CPT formats:

### Location & Coordinate Systems

- **coordinate-systems.json** - Coordinate reference systems (XYID codes)

  - Dutch National Grid (RD), Belgian Lambert 72, German Gauss-Krüger
  - UTM zones, WGS 84, State Plane, local systems
  - Includes EPSG codes and Proj4 definitions where applicable

- **height-systems.json** - Height/elevation reference systems (ZID codes)
  - NAP (Netherlands), TAW/Ostend (Belgium), Normalnull (Germany)
  - Local systems, LLWS (Low Low Water Spring)
  - Includes EPSG codes

### Determination Methods

- **place-determination-codes.json** - Horizontal position determination methods

  - Measured: Surveying, GPS, Differential GPS (various accuracies)
  - Estimated: Topographic maps, detail maps (various scales)

- **height-determination-codes.json** - Vertical position determination methods
  - Measured: Surveying, Differential GPS
  - Estimated: Contour maps, topographic maps, AHN (Netherlands)

## GEF-CPT Specification Files

Located in `cpt/` - Cone Penetration Test data:

### Core Specification

- **column-quantities.json** - Data column quantity numbers (1-36, 128-129)
  - Primary measurements (depth, cone resistance, friction)
  - Pore pressure (u1, u2, u3)
  - Inclination measurements
  - Calculated values (corrected resistance, pore ratio)
  - Soil properties, magnetic field measurements

- **measurement-variables.json** - Numeric test parameters
  - Equipment specifications (cone area, friction sleeve)
  - Test configuration (type, capabilities)
  - Site conditions (groundwater, pre-excavation)
  - Calibration data (zero measurements)

- **measurement-text-variables.json** - Text metadata fields
  - Project information (client, location)
  - Equipment details (cone type, serial number)
  - Standards and coordinate systems
  - Processing methods, remarks, calculation formulas

### Dutch Extensions (BRO + VOTB)

Netherlands-specific fields for regulatory and industry standards, also called [GEF 1.1.3](https://www.cptdata.nl/downloads/gef113Releasenotes.pdf).

- **dutch-extensions-text-variables.json**

  - BRO (Basis Registratie Ondergrond) - Regulatory submission fields
  - VOTB (Vereniging Ondernemers Technisch Bodemonderzoek) - Industry fields

- **dutch-extensions-numeric-variables.json**
  - BRO data fields (measurements, magnetic field, inclination)
  - VOTB equipment and calibration data

### Belgian Extensions (DOV)

Belgium-specific fields for Databank Ondergrond Vlaanderen:

- **belgian-extensions-text-variables.json**

  - Test execution details
  - Calibration information
  - Equipment specifications
  - Remarks and deviations

- **belgian-extensions-numeric-variables.json**
  - Calibration measurements
  - Equipment characteristics
  - Guide tubes, borings, retractions, stops

## GEF-BORE Specification Files

Located in `bore/` - Borehole/drilling data:

### Soil Classification (NEN 5104)

- **table-2.15-nen5104-soil-codes.json** - Standard soil types per NEN 5104
- **table-2.16-non-standard-soil-codes.json** - Non-standard soil classifications
- **table-2.17-additional-soil-codes.json** - Additional materials (rocks, anthropogenic)
- **soil-type-names.json** - Main soil type names (G, K, L, V, Z)

### Soil Properties

- **table-2.19-secondary-colors.json** - Secondary color codes (TBL, TBR, etc.)
- **table-2.20-main-colors.json** - Main color codes and intensity
- **table-2.21-sand-median-classes.json** - Sand grain size classifications
- **table-2.22-sand-spread.json** - Sand grain size distribution
- **table-2.23-grain-shape.json** - Grain angularity/roundness
- **table-2.24-gravel-median-classes.json** - Gravel size classifications
- **table-2.25-gravel-fractions.json** - Gravel content quantities
- **table-2.26-peat-amorphosity.json** - Peat decomposition levels
- **table-2.27-peat-types.json** - Peat species/origin types

### Soil Consistency & Compaction

- **table-2.28-consistency.json** - Consistency for clay, loam, and peat
- **table-2.29-sand-compaction.json** - Sand compaction levels
- **table-2.30-rock-hardness.json** - Rock hardness classifications

### Soil Characteristics

- **table-2.31-shell-content.json** - Shell material quantities
- **table-2.32-calcium-content.json** - Calcium/lime content
- **table-2.33-glauconite-content.json** - Glauconite mineral content
- **table-2.34-anthropogenic-admixtures.json** - Man-made inclusions
- **table-2.35-layering.json** - Stratification patterns

### Geological Context

- **table-2.36-geological-interpretation.json** - Geological interpretations
- **table-2.37-stratigraphic-units.json** - Dutch stratigraphic formations

### Drilling & Sampling

- **drilling-method-codes.json** - Drilling methods per NEN 5104
- **specimen-codes.json** - Sample types and sampling methods
- **table-2.18-bore-layer-quantity.json** - Layer data column numbers

### Metadata Variables

- **measurement-variables.json** - Numeric measurement fields
- **measurement-text-variables.json** - Text metadata fields

## References

- **GEF-BORE specification**: Dutch standard for borehole data exchange
- **GEF-CPT specification**: Dutch standard for CPT data exchange
- **NEN 5104**: Dutch standard for soil classification
- **NEN 5140**: Dutch standard for cone penetration testing
