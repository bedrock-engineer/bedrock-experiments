# BRO/XML

IMBRO/XML is a standardized data exchange format specifically designed for the transfer of information related to soil investigations and geotechnical data. It stands for "Informatie Model Bodem en Ondergrond".

IMBRO/XML builds upon and incorporates several existing standards like GML (Geography Markup Language) and NEN standards - Dutch national standards for geotechnical investigations, particularly NEN-EN-ISO 14688 (soil identification) and NEN-EN-ISO 14689 (rock identification).
IMBRO/XML essentially adapts and extends these standards to create a specialized format that meets the specific requirements of the Dutch Key Register of the Subsurface (BRO). It provides a more detailed and structured approach for geotechnical data exchange than what was previously available in the broader standards.
## Conceptual Model

The BRO (Basisregistratie Ondergrond - Base Registration of the Subsurface) organizes geotechnical data around three interconnected concepts:

1. **Onderzoek (Investigation)** - The investigative activity or process sequence
   - When was the investigation performed?
   - Who conducted it?
   - What methods were used?

2. **Resultaat (Result)** - The findings/data derived from the investigation
   - What was measured or observed?
   - What are the values and measurements?
   - What is the quality and reliability?

3. **Object van Onderzoek** - The subsurface portion being examined
   - Where is the investigation located?
   - What depth interval was investigated?
   - What soil/rock layers were encountered?

**Key Principle:** What makes each investigation unique is not just the result or object examined, but that the investigation occurred at a **specific moment in time**. This temporal dimension allows users to assess whether findings are suitable for their intended purpose.

**Lifecycle:** BRO registration spans from investigation commission through registration completion in the BRO system, excluding procurement details while capturing organizational context.

---

# CPT (Cone Penetration Test) Structure

```
  dispatchDataResponse (xmlns="http://www.broservices.nl/xsd/dscpt/1.1")
  ├── brocom:responseType
  ├── brocom:requestReference
  ├── brocom:dispatchTime
  └── dispatchDocument
      └── CPT_O (gml:id)
          ├── brocom:broId (e.g., "CPT000000198149")
          ├── brocom:deliveryAccountableParty (KVK number - 8 digits)
          ├── brocom:qualityRegime (codeSpace: urn:bro:QualityRegime)
          │   └── Values: IMBRO, IMBRO/A
          ├── deliveryContext (codeSpace: urn:bro:cpt:DeliveryContext)
          │   └── Values: publiekeTaak, kwaliteitsbeheersing, etc.
          ├── surveyPurpose (codeSpace: urn:bro:cpt:SurveyPurpose)
          │   └── Values: infrastructuurLand, infrastructuurWater, bouwwerk, etc.
          ├── researchReportDate
          │   └── brocom:date (ISO 8601: YYYY-MM-DD)
          ├── cptStandard (codeSpace: urn:bro:cpt:CPTStandard)
          │   └── Values: ISO22476D1, NEN5140, NEN3680
          ├── additionalInvestigationPerformed (codeSpace: urn:bro:IndicationYesNo)
          │   └── Values: ja, nee
          │
          ├── standardizedLocation
          │   ├── brocom:location (srsName: typically "urn:ogc:def:crs:EPSG::4258", gml:id)
          │   │   └── gml:pos (lat lon coordinates)
          │   └── brocom:coordinateTransformation (codeSpace: urn:bro:CoordinateTransformation)
          │       └── Values: RDNAPTRANS2008, RDNAPTRANS2018
          │
          ├── deliveredLocation
          │   ├── cptcommon:location (srsName: typically "urn:ogc:def:crs:EPSG::28992", gml:id)
          │   │   └── gml:pos (x, y RD coordinates)
          │   ├── cptcommon:horizontalPositioningDate
          │   │   └── brocom:voidReason (codeSpace: urn:bro:VoidReason) [optional]
          │   │       └── Values: onbekend, geenWaarde, nietBepaalbaar
          │   └── cptcommon:horizontalPositioningMethod (codeSpace: urn:bro:HorizontalPositioningMethod)
          │       └── Values: GNSS, tachymetrie, onbekend, etc.
          │
          ├── deliveredVerticalPosition
          │   ├── cptcommon:localVerticalReferencePoint (codeSpace: urn:bro:cpt:LocalVerticalReferencePoint)
          │   │   └── Values: maaiveld, bodemoppervlak, NAP, etc.
          │   ├── cptcommon:offset (uom="m")
          │   ├── cptcommon:verticalDatum (codeSpace: urn:bro:VerticalDatum)
          │   │   └── Values: NAP, MSL, LAT
          │   ├── cptcommon:verticalPositioningDate
          │   └── cptcommon:verticalPositioningMethod (codeSpace: urn:bro:VerticalPositioningMethod)
          │       └── Values: waterpassing, GNSS, onbekend, etc.
          │
          ├── conePenetrometerSurvey (gml:id)
          │   ├── sampling:sampledFeature
          │   ├── cptcommon:dissipationTestPerformed (codeSpace: urn:bro:IndicationYesNo)
          │   │   └── Values: ja, nee
          │   ├── cptcommon:finalProcessingDate (ISO 8601: YYYY-MM-DD)
          │   ├── cptcommon:cptMethod (codeSpace: urn:bro:cpt:CPTMethod)
          │   │   └── Values: elektrischContinu, elektrischDiscontinu, mechanisch
          │   ├── cptcommon:qualityClass (codeSpace: urn:bro:cpt:QualityClass)
          │   │   └── Values: klasse1, klasse2, klasse3, klasse4
          │   ├── cptcommon:stopCriterion (codeSpace: urn:bro:cpt:StopCriterion)
          │   │   └── Values: einddiepte, obstakel, mechanischeBeschadiging, etc.
          │   │
          │   ├── cptcommon:trajectory
          │   │   ├── cptcommon:predrilledDepth (uom="m")
          │   │   └── cptcommon:finalDepth (uom="m")
          │   │
          │   ├── cptcommon:conePenetrometer
          │   │   ├── cptcommon:description
          │   │   ├── cptcommon:conePenetrometerType
          │   │   ├── cptcommon:coneSurfaceArea (uom="mm2")
          │   │   ├── cptcommon:coneSurfaceQuotient
          │   │   ├── cptcommon:coneToFrictionSleeveDistance (uom="mm")
          │   │   ├── cptcommon:frictionSleeveSurfaceArea (uom="mm2")
          │   │   ├── cptcommon:frictionSleeveSurfaceQuotient
          │   │   └── cptcommon:zeroLoadMeasurement
          │   │       ├── cptcommon:coneResistanceBefore (uom="MPa")
          │   │       ├── cptcommon:coneResistanceAfter (uom="MPa")
          │   │       ├── cptcommon:inclinationEWBefore (uom="deg")
          │   │       ├── cptcommon:inclinationEWAfter (uom="deg")
          │   │       ├── cptcommon:inclinationNSBefore (uom="deg")
          │   │       ├── cptcommon:inclinationNSAfter (uom="deg")
          │   │       ├── cptcommon:inclinationResultantBefore (uom="deg")
          │   │       ├── cptcommon:inclinationResultantAfter (uom="deg")
          │   │       ├── cptcommon:localFrictionBefore (uom="MPa")
          │   │       ├── cptcommon:localFrictionAfter (uom="MPa")
          │   │       ├── cptcommon:porePressureU1Before (uom="MPa") [optional]
          │   │       ├── cptcommon:porePressureU1After (uom="MPa") [optional]
          │   │       ├── cptcommon:porePressureU2Before (uom="MPa")
          │   │       ├── cptcommon:porePressureU2After (uom="MPa")
          │   │       ├── cptcommon:porePressureU3Before (uom="MPa") [optional]
          │   │       └── cptcommon:porePressureU3After (uom="MPa") [optional]
          │   │
          │   ├── cptcommon:conePenetrationTest (gml:id)
          │   │   ├── om:phenomenonTime (xlink:type)
          │   │   │   └── gml:TimeInstant (gml:id)
          │   │   │       └── gml:timePosition
          │   │   ├── om:resultTime (xlink:type)
          │   │   │   └── gml:TimeInstant (gml:id)
          │   │   │       └── gml:timePosition
          │   │   ├── om:procedure
          │   │   ├── om:observedProperty
          │   │   ├── om:featureOfInterest
          │   │   └── cptcommon:cptResult
          │   │       ├── swe:elementCount
          │   │       ├── swe:elementType (name, xlink:type, xlink:href)
          │   │       ├── swe:encoding
          │   │       │   └── swe:TextEncoding (decimalSeparator, tokenSeparator, blockSeparator)
          │   │       └── cptcommon:values (CSV format: semicolon-separated rows, comma-separated columns)
          │   │
          │   ├── cptcommon:procedure
          │   │   ├── cptcommon:interruptionProcessingPerformed
          │   │   ├── cptcommon:expertCorrectionPerformed
          │   │   └── cptcommon:signalProcessingPerformed
          │   │
          │   └── cptcommon:parameters (boolean flags for available measurements)
          │       ├── cptcommon:penetrationLength (ja/nee)
          │       ├── cptcommon:depth (ja/nee)
          │       ├── cptcommon:elapsedTime (ja/nee)
          │       ├── cptcommon:coneResistance (ja/nee)
          │       ├── cptcommon:correctedConeResistance (ja/nee)
          │       ├── cptcommon:netConeResistance (ja/nee)
          │       ├── cptcommon:magneticFieldStrengthX (ja/nee)
          │       ├── cptcommon:magneticFieldStrengthY (ja/nee)
          │       ├── cptcommon:magneticFieldStrengthZ (ja/nee)
          │       ├── cptcommon:magneticFieldStrengthTotal (ja/nee)
          │       ├── cptcommon:electricalConductivity (ja/nee)
          │       ├── cptcommon:inclinationEW (ja/nee)
          │       ├── cptcommon:inclinationNS (ja/nee)
          │       ├── cptcommon:inclinationX (ja/nee)
          │       ├── cptcommon:inclinationY (ja/nee)
          │       ├── cptcommon:inclinationResultant (ja/nee)
          │       ├── cptcommon:magneticInclination (ja/nee)
          │       ├── cptcommon:magneticDeclination (ja/nee)
          │       ├── cptcommon:localFriction (ja/nee)
          │       ├── cptcommon:poreRatio (ja/nee)
          │       ├── cptcommon:temperature (ja/nee)
          │       ├── cptcommon:porePressureU1 (ja/nee)
          │       ├── cptcommon:porePressureU2 (ja/nee)
          │       ├── cptcommon:porePressureU3 (ja/nee)
          │       └── cptcommon:frictionRatio (ja/nee)
          │
          └── registrationHistory
              └── brocom:RegistrationHistory
                  ├── brocom:objectRegistrationTime (ISO 8601 datetime)
                  ├── brocom:registrationStatus (codeSpace: urn:bro:RegistrationStatus)
                  │   └── Values: volledigBeschikbaar, inOnderzoek, geregistreerd
                  ├── brocom:registrationCompletionTime (ISO 8601 datetime) [optional]
                  ├── brocom:corrected (codeSpace: urn:bro:IndicationYesNo)
                  │   └── Values: ja, nee
                  ├── brocom:underReview (codeSpace: urn:bro:IndicationYesNo)
                  │   └── Values: ja, nee
                  ├── brocom:deregistered (codeSpace: urn:bro:IndicationYesNo)
                  │   └── Values: ja, nee, onbekend
                  └── brocom:reregistered (codeSpace: urn:bro:IndicationYesNo)
                      └── Values: ja, nee
```

  Key Relationships:

  1. Location Data: Three location types are related:
    - standardizedLocation (EPSG:4258 - WGS84)
    - deliveredLocation (EPSG:28992 - RD/Amersfoort)
    - deliveredVerticalPosition (vertical reference point + NAP offset)
  2. Equipment Calibration: zeroLoadMeasurement contains before/after readings for all sensors
  3. Measurement Data: The cptcommon:values element contains CSV-encoded measurement data, with:
    - cptcommon:parameters defining which columns are present (ja=yes, nee=no)
    - swe:TextEncoding defining the CSV format (; = row separator, , = column separator, . = decimal)
  4. Namespaces: The structure uses multiple XML namespaces:
    - brocom - Common BRO elements
    - cptcommon - CPT-specific elements
    - dscpt - CPT dispatch schema
    - gml - Geography Markup Language
    - swe - Sensor Web Enablement
    - om - Observations & Measurements

---

# BHR-GT (Geotechnical Borehole) Structure

```
  dispatchDataResponse (xmlns="http://www.broservices.nl/xsd/dsbhr-gt/2.1")
  ├── brocom:responseType
  ├── brocom:dispatchTime
  └── brocom:dispatchDocument
      └── BHR_GT_CompleteReport
          ├── brocom:broId (e.g., "BHR000000123456")
          ├── brocom:deliveryAccountableParty (KVK number - 8 digits)
          ├── brocom:qualityRegime (codeSpace: urn:bro:QualityRegime)
          │   └── Values: IMBRO, IMBRO/A
          │
          ├── dsbhrgt:reportHistory
          │   └── dsbhrgt:reportStartDate
          │       └── brocom:date (ISO 8601: YYYY-MM-DD)
          │
          ├── dsbhrgt:deliveredLocation
          │   ├── bhrgtcom:location (srsName: typically "urn:ogc:def:crs:EPSG::28992", gml:id)
          │   │   └── gml:pos (x, y RD coordinates)
          │   ├── bhrgtcom:horizontalPositioningDate
          │   └── bhrgtcom:horizontalPositioningMethod (codeSpace: urn:bro:HorizontalPositioningMethod)
          │       └── Values: GNSS, tachymetrie, onbekend, etc.
          │
          ├── dsbhrgt:standardizedLocation
          │   ├── brocom:location (srsName: typically "urn:ogc:def:crs:EPSG::4258", gml:id)
          │   │   └── gml:pos (lat, lon WGS84 coordinates)
          │   └── brocom:coordinateTransformation (codeSpace: urn:bro:CoordinateTransformation)
          │       └── Values: RDNAPTRANS2008, RDNAPTRANS2018
          │
          ├── dsbhrgt:deliveredVerticalPosition
          │   ├── bhrgtcom:offset (uom="m")
          │   ├── bhrgtcom:verticalDatum (codeSpace: urn:bro:VerticalDatum)
          │   │   └── Values: NAP, MSL, LAT
          │   ├── bhrgtcom:localVerticalReferencePoint (codeSpace: urn:bro:bhrgt:LocalVerticalReferencePoint)
          │   │   └── Values: maaiveld, bodemoppervlak, etc.
          │   ├── bhrgtcom:verticalPositioningDate
          │   └── bhrgtcom:verticalPositioningMethod (codeSpace: urn:bro:VerticalPositioningMethod)
          │       └── Values: waterpassing, GNSS, onbekend, etc.
          │
          ├── dsbhrgt:boring
          │   └── bhrgtcom:Boring
          │       ├── bhrgtcom:boringStartDate (ISO 8601: YYYY-MM-DD)
          │       ├── bhrgtcom:boringEndDate (ISO 8601: YYYY-MM-DD)
          │       ├── bhrgtcom:boringOperator (organization/chamberOfCommerceNumber)
          │       ├── bhrgtcom:rockReached (codeSpace: urn:bro:IndicationYesNo)
          │       │   └── Values: ja, nee
          │       ├── bhrgtcom:finalDepthBoring (uom="m")
          │       ├── bhrgtcom:finalDepthSampling (uom="m")
          │       ├── bhrgtcom:groundwaterLevel (uom="m") [optional]
          │       ├── bhrgtcom:boreholeCompleted (codeSpace: urn:bro:IndicationYesNo)
          │       │   └── Values: ja, nee
          │       ├── bhrgtcom:boredInterval [multiple]
          │       └── bhrgtcom:sampledInterval [multiple]
          │
          ├── dsbhrgt:boreholeSampleDescription (BHR-GT-BMB)
          │   └── bhrgtcom:BoreholeSampleDescription
          │       ├── bhrgtcom:descriptionReportDate (ISO 8601: YYYY-MM-DD)
          │       ├── bhrgtcom:descriptionProcedure (codeSpace: urn:bro:bhrgt:DescriptionProcedure)
          │       │   └── Values: ISO14688d1v2019c2020, NEN5104, etc.
          │       ├── bhrgtcom:descriptionOperator (organization/chamberOfCommerceNumber)
          │       └── bhrgtcom:descriptiveBoreholeLog
          │           └── bhrgtcom:DescriptiveBoreholeLog
          │               ├── bhrgtcom:descriptionQuality (codeSpace: urn:bro:bhrgt:DescriptionQuality)
          │               │   └── Values: klasse1ongeroerd, klasse2geroerd, etc.
          │               ├── bhrgtcom:continuouslySampled (codeSpace: urn:bro:IndicationYesNo)
          │               │   └── Values: ja, nee
          │               └── bhrgtcom:layer [multiple]
          │                   ├── bhrgtcom:upperBoundary (uom="m")
          │                   ├── bhrgtcom:lowerBoundary (uom="m")
          │                   ├── bhrgtcom:upperBoundaryDetermination (codeSpace: urn:bro:bhrgt:BoundaryDetermination)
          │                   ├── bhrgtcom:lowerBoundaryDetermination (codeSpace: urn:bro:bhrgt:BoundaryDetermination)
          │                   ├── bhrgtcom:anthropogenic (codeSpace: urn:bro:IndicationYesNo) [optional]
          │                   │   └── Values: ja, nee
          │                   └── bhrgtcom:soil
          │                       ├── bhrgtcom:geotechnicalSoilName (codeSpace: urn:bro:bhrgt:GeotechnicalSoilName)
          │                       │   └── Values: zwakZandigeKlei, sterkZandigeKlei, etc.
          │                       ├── bhrgtcom:colour (codeSpace: urn:bro:bhrgt:Colour) [optional]
          │                       │   └── Values: donkerbruin, lichtgrijs, geelbruin, etc.
          │                       ├── bhrgtcom:dispersedInhomogeneity (codeSpace: urn:bro:IndicationYesNo) [optional]
          │                       ├── bhrgtcom:organicMatterContentClass (codeSpace: urn:bro:bhrgt:OrganicMatterContentClass) [optional]
          │                       │   └── Values: zwakHumeus, matigHumeus, sterkHumeus, etc.
          │                       └── bhrgtcom:sandMedianClass (codeSpace: urn:bro:bhrgt:SandMedianClass) [optional]
          │                           └── Values: uitermateFijn, zeerFijn, matigFijn, middelgrof, etc.
          │
          ├── dsbhrgt:boreholeSampleAnalysis (BHR-GT-BMA) ❌ NOT SUPPORTED
          │   └── bhrgtcom:BoreholeSampleAnalysis
          │       ├── bhrgtcom:analysisReportDate (ISO 8601: YYYY-MM-DD)
          │       ├── bhrgtcom:analysisProcedure (codeSpace: urn:bro:bhrgt:AnalysisProcedure)
          │       │   └── Values: NEN5104, ISO/TS17892, etc.
          │       ├── bhrgtcom:analysisOperator (organization/chamberOfCommerceNumber) [optional]
          │       └── bhrgtcom:investigatedInterval [multiple]
          │           ├── bhrgtcom:beginDepth (uom="m")
          │           ├── bhrgtcom:endDepth (uom="m")
          │           ├── bhrgtcom:sampleQuality (codeSpace: urn:bro:bhrgt:SampleQuality)
          │           │   └── Values: klasse1, klasse2, klasse3, klasse4
          │           ├── bhrgtcom:analysisType (codeSpace: urn:bro:bhrgt:AnalysisType)
          │           │   └── Values: watergehalte, korrelgrootte, schuifsterkte, etc.
          │           ├── Boolean flags (codeSpace: urn:bro:IndicationYesNo):
          │           │   ├── bhrgtcom:waterContentDetermined (ja/nee)
          │           │   ├── bhrgtcom:organicMatterContentDetermined (ja/nee)
          │           │   ├── bhrgtcom:carbonateContentDetermined (ja/nee)
          │           │   ├── bhrgtcom:volumetricMassDensityDetermined (ja/nee)
          │           │   └── bhrgtcom:volumetricMassDensitySolidsDetermined (ja/nee)
          │           │
          │           └── Determination types [all optional]:
          │               ├── 1. bhrgtcom:waterContent
          │               │   ├── bhrgtcom:determinationDate
          │               │   ├── bhrgtcom:determinationProcedure
          │               │   └── bhrgtcom:waterContentValue (percentage)
          │               │
          │               ├── 2. bhrgtcom:organicMatterContent
          │               │   ├── bhrgtcom:determinationDate
          │               │   ├── bhrgtcom:determinationProcedure
          │               │   └── bhrgtcom:organicMatterContentValue (percentage)
          │               │
          │               ├── 3. bhrgtcom:carbonateContent
          │               │   ├── bhrgtcom:determinationDate
          │               │   ├── bhrgtcom:determinationProcedure
          │               │   └── bhrgtcom:carbonateContentValue (percentage)
          │               │
          │               ├── 4. bhrgtcom:volumetricMassDensity
          │               │   ├── bhrgtcom:determinationDate
          │               │   ├── bhrgtcom:determinationProcedure
          │               │   └── bhrgtcom:volumetricMassDensityValue (g/cm³)
          │               │
          │               ├── 5. bhrgtcom:volumetricMassDensitySolids
          │               │   ├── bhrgtcom:determinationDate
          │               │   ├── bhrgtcom:determinationProcedure
          │               │   └── bhrgtcom:volumetricMassDensitySolidsValue (g/cm³)
          │               │
          │               ├── 6. bhrgtcom:particleSizeDistribution
          │               │   ├── bhrgtcom:determinationDate
          │               │   ├── bhrgtcom:determinationProcedure
          │               │   ├── bhrgtcom:fractionDistributionOption
          │               │   └── bhrgtcom:grainSizeCurve (multiple measurement points)
          │               │
          │               ├── 7. bhrgtcom:maximumUndrainedShearStrength
          │               │   ├── bhrgtcom:determinationDate
          │               │   ├── bhrgtcom:determinationProcedure
          │               │   └── bhrgtcom:shearStrengthValue (kPa)
          │               │
          │               ├── 8. bhrgtcom:settlementCharacteristics
          │               │   ├── bhrgtcom:determinationDate
          │               │   ├── bhrgtcom:determinationProcedure
          │               │   ├── bhrgtcom:consolidationCurve
          │               │   └── bhrgtcom:compressionIndex
          │               │
          │               ├── 9. bhrgtcom:consistencyLimits
          │               │   ├── bhrgtcom:determinationDate
          │               │   ├── bhrgtcom:determinationProcedure
          │               │   ├── bhrgtcom:liquidLimit (percentage)
          │               │   ├── bhrgtcom:plasticLimit (percentage)
          │               │   └── bhrgtcom:plasticityIndex (calculated)
          │               │
          │               ├── 10. bhrgtcom:shearStressDuringLoading [up to 3 variants]
          │               │   ├── bhrgtcom:determinationDate
          │               │   ├── bhrgtcom:determinationProcedure
          │               │   ├── bhrgtcom:testType
          │               │   └── bhrgtcom:stressStrainCurve (multiple points)
          │               │
          │               ├── 11. bhrgtcom:shearStressDuringHorizontalDeformation
          │               │   ├── bhrgtcom:determinationDate
          │               │   ├── bhrgtcom:determinationProcedure
          │               │   └── bhrgtcom:shearStrengthParameters
          │               │
          │               └── 12. bhrgtcom:saturatedPermeability
          │                   ├── bhrgtcom:determinationDate
          │                   ├── bhrgtcom:determinationProcedure
          │                   └── bhrgtcom:permeabilityValue (m/s)
          │
          └── dsbhrgt:registrationHistory
              └── brocom:RegistrationHistory
                  ├── brocom:objectRegistrationTime (ISO 8601 datetime)
                  ├── brocom:registrationStatus (codeSpace: urn:bro:RegistrationStatus)
                  │   └── Values: volledigBeschikbaar, inOnderzoek, geregistreerd
                  ├── brocom:registrationCompletionTime (ISO 8601 datetime) [optional]
                  ├── brocom:corrected (codeSpace: urn:bro:IndicationYesNo)
                  │   └── Values: ja, nee
                  ├── brocom:underReview (codeSpace: urn:bro:IndicationYesNo)
                  │   └── Values: ja, nee
                  ├── brocom:deregistered (codeSpace: urn:bro:IndicationYesNo)
                  │   └── Values: ja, nee, onbekend
                  └── brocom:reregistered (codeSpace: urn:bro:IndicationYesNo)
                      └── Values: ja, nee
```

  BHR-GT Key Components:

  1. **BHR-GT-BMB (boreholeSampleDescription)** - DESCRIPTIVE ✅ Currently Supported
     - Visual/textural soil description created during boring
     - Soil type classification (geotechnicalSoilName)
     - Basic properties (color, texture, organic matter presence)
     - Layer boundaries with depth ranges

  2. **BHR-GT-BMA (boreholeSampleAnalysis)** - ANALYTICAL ❌ Not Currently Supported
     - Laboratory measurements on extracted samples
     - 12 determination types (water content, particle size, shear strength, etc.)
     - Quantitative measurements with units
     - Detailed test procedures and quality indicators
     - Critical for foundation design and geotechnical engineering

  3. Location & Position:
     - Same structure as CPT (delivered, standardized, vertical position)

  4. Boring Process:
     - Timeline (start/end dates)
     - Completion status
     - Rock encounter flag
     - Multiple bored/sampled intervals

  5. Namespaces:
     - brocom - Common BRO elements
     - bhrgtcom - Geotechnical borehole common elements
     - dsbhrgt - BHR-GT dispatch schema
     - gml - Geography Markup Language

---

# BHR-G (Geological Borehole) Structure

```
  dispatchDataResponse (xmlns="http://www.broservices.nl/xsd/dsbhrg/3.1")
  ├── brocom:responseType
  ├── brocom:dispatchTime
  └── brocom:dispatchDocument
      └── BHR_G_CompleteReport
          ├── brocom:broId (e.g., "BHR000000123456")
          ├── brocom:deliveryAccountableParty (KVK number - 8 digits)
          ├── brocom:qualityRegime (codeSpace: urn:bro:QualityRegime)
          │   └── Values: IMBRO, IMBRO/A
          │
          ├── researchReportDate
          │   └── brocom:date (ISO 8601: YYYY-MM-DD)
          │
          ├── deliveredLocation
          │   └── bhrgcom:location (srsName: typically "urn:ogc:def:crs:EPSG::28992", gml:id)
          │       └── gml:pos (x, y RD coordinates)
          │
          ├── standardizedLocation
          │   └── brocom:location (srsName: typically "urn:ogc:def:crs:EPSG::4258", gml:id)
          │       └── gml:pos (lat, lon WGS84 coordinates)
          │
          ├── deliveredVerticalPosition
          │   ├── bhrgcom:offset (uom="m")
          │   ├── bhrgcom:verticalDatum (codeSpace: urn:bro:bhrgcommon:VerticalDatum)
          │   │   └── Values: NAP, MSL, LAT
          │   └── bhrgcom:localVerticalReferencePoint (codeSpace: urn:bro:bhrgcommon:LocalVerticalReferencePoint)
          │       └── Values: maaiveld, bodemoppervlak, etc.
          │
          ├── boring
          │   └── bhrgcom:Boring
          │       ├── bhrgcom:rockReached (codeSpace: urn:bro:IndicationYesNo)
          │       │   └── Values: ja, nee
          │       ├── bhrgcom:finalDepthBoring (uom="m")
          │       ├── bhrgcom:finalDepthSampling (uom="m")
          │       └── bhrgcom:boreholeCompleted (codeSpace: urn:bro:bhrgcommon:BoreholeCompleted)
          │           └── Values: ja, nee, onbekend
          │
          └── boreholeSampleDescription ✅ SUPPORTED
              └── bhrgcom:BoreholeSampleDescription
                  ├── bhrgcom:descriptionProcedure (codeSpace: urn:bro:bhrgcommon:DescriptionProcedure)
                  │   └── Values: NEN5104
                  └── bhrgcom:descriptiveBoreholeLog
                      └── bhrgcom:DescriptiveBoreholeLog
                          └── bhrgcom:layer [multiple]
                              ├── bhrgcom:upperBoundary (uom="m")
                              ├── bhrgcom:lowerBoundary (uom="m")
                              ├── bhrgcom:anthropogenic (codeSpace: urn:bro:bhrgcommon:Anthropogenic) [optional]
                              │   └── Values: ja, nee
                              ├── bhrgcom:rooted (codeSpace: urn:bro:bhrgcommon:Rooted) [optional]
                              │   └── Values: ja, nee
                              └── bhrgcom:soil
                                  ├── bhrgcom:soilNameNEN5104 (codeSpace: urn:bro:bhrgcommon:SoilNameNEN5104)
                                  │   └── Values: klei, zand, veen, leem, etc.
                                  ├── bhrgcom:colour (codeSpace: urn:bro:bhrgcommon:Colour) [optional]
                                  │   └── Values: bruin, grijs, geelbruin, blauwgrijs, etc.
                                  ├── bhrgcom:organicMatterContentClassNEN5104 (codeSpace: urn:bro:bhrgcommon:OrganicMatterContentClassNEN5104) [optional]
                                  │   └── Values: zwakHumeusH1, matigHumeusH2, sterkHumeusH3, etc.
                                  ├── bhrgcom:gravelContentClass (codeSpace: urn:bro:bhrgcommon:GravelContentClass) [optional]
                                  │   └── Values: zwakGrindigG1, matigGrindigG2, sterkGrindigG3, etc.
                                  ├── bhrgcom:carbonateContentClass (codeSpace: urn:bro:bhrgcommon:CarbonateContentClass) [optional]
                                  │   └── Values: kalkhoudendCa1, kalkrijkCa2, kalkloosNoCa, etc.
                                  └── bhrgcom:sandMedianClass (codeSpace: urn:bro:bhrgcommon:SandMedianClass) [optional]
                                      └── Values: uitermateFijn, zeerFijn, matigFijn, fijn, middelgrof, grof, etc.
```

  BHR-G Key Components:

  1. **Geological Classification (NEN5104)**
     - Uses Dutch geological soil naming system (NEN5104)
     - Different from geotechnical classification (ISO14688)
     - Focuses on geological origin and composition

  2. **Additional Geological Properties**
     - anthropogenic: whether soil is human-influenced
     - rooted: presence of plant roots
     - carbonateContent: limestone/chalk content
     - gravelContentClass: gravel fraction classification

  3. **Simpler Structure**
     - No analytical component (BMA) like BHR-GT
     - Focus on description only
     - Typically used for geological mapping and research

  4. **Namespaces:**
     - brocom - Common BRO elements
     - bhrgcom - Geological borehole common elements (v3.1)
     - dsbhrg - BHR-G dispatch schema
     - gml - Geography Markup Language