# state file generated using paraview version 6.0.0
import paraview
paraview.compatibility.major = 6
paraview.compatibility.minor = 0

#### import the simple module from the paraview
from paraview.simple import *
#### disable automatic camera reset on 'Show'
paraview.simple._DisableFirstRenderCameraReset()

# ----------------------------------------------------------------
# setup views used in the visualization
# ----------------------------------------------------------------

# get the material library
materialLibrary1 = GetMaterialLibrary()

# Create a new 'Render View'
renderView1 = CreateView('RenderView')
renderView1.Set(
    ViewSize=[869, 780],
    CenterOfRotation=[125.0, 125.0, 50.0],
    CameraPosition=[-76.57953257896715, -477.7259064296778, 219.46052685120003],
    CameraFocalPoint=[150.70819169801194, 168.24565415233238, 32.677518164554265],
    CameraViewUp=[0.09846399994280208, 0.24429532589550243, 0.964688879619162],
    CameraFocalDisk=1.0,
    CameraParallelScale=183.71173070873834,
    OSPRayMaterialLibrary=materialLibrary1,
)

SetActiveView(None)

# ----------------------------------------------------------------
# setup view layouts
# ----------------------------------------------------------------

# create new layout object 'Layout #1'
layout1 = CreateLayout(name='Layout #1')
layout1.AssignView(0, renderView1)
layout1.SetSize(869, 780)

# ----------------------------------------------------------------
# restore active view
SetActiveView(renderView1)
# ----------------------------------------------------------------

# ----------------------------------------------------------------
# setup the data processing pipelines
# ----------------------------------------------------------------

# create a new 'XML Image Data Reader'
fluvial_channelsvti = XMLImageDataReader(registrationName='fluvial_channels.vti', FileName=['C:/Users/joost/ReposWindows/bedrock-experiments/channels/paraview/fluvial_channels.vti'])
fluvial_channelsvti.Set(
    CellArrayStatus=['facies'],
    TimeArray='None',
)

# create a new 'Threshold'
threshold12 = Threshold(registrationName='Threshold1-2', Input=fluvial_channelsvti)
threshold12.Set(
    Scalars=['CELLS', 'facies'],
    LowerThreshold=0.5,
    UpperThreshold=2.5,
)

# create a new 'Extract Surface'
extractSurface_Sand = ExtractSurface(registrationName='ExtractSurface_Sand', Input=threshold12)

# create a new 'Threshold'
threshold0 = Threshold(registrationName='Threshold0', Input=fluvial_channelsvti)
threshold0.Set(
    Scalars=['CELLS', 'facies'],
    UpperThreshold=0.5,
)

# create a new 'Threshold'
threshold34 = Threshold(registrationName='Threshold3-4', Input=fluvial_channelsvti)
threshold34.Set(
    Scalars=['CELLS', 'facies'],
    LowerThreshold=2.5,
    UpperThreshold=4.5,
)

# create a new 'Extract Surface'
extractSurface_Silt = ExtractSurface(registrationName='ExtractSurface_Silt', Input=threshold34)

# create a new 'Extract Surface'
extractSurface_FloodPlane = ExtractSurface(registrationName='ExtractSurface_FloodPlane', Input=threshold0)

# ----------------------------------------------------------------
# setup the visualization in view 'renderView1'
# ----------------------------------------------------------------

# show data from extractSurface_FloodPlane
extractSurface_FloodPlaneDisplay = Show(extractSurface_FloodPlane, renderView1, 'GeometryRepresentation')

# get color transfer function/color map for 'facies'
faciesLUT = GetColorTransferFunction('facies')
faciesLUT.Set(
    RGBPoints=GenerateRGBPoints(
        range_min=0.0,
        range_max=4.0,
    ),
    ScalarRangeInitialized=1.0,
)

# trace defaults for the display properties.
extractSurface_FloodPlaneDisplay.Set(
    Representation='Surface',
    ColorArrayName=['CELLS', 'facies'],
    LookupTable=faciesLUT,
)

# show data from extractSurface_Sand
extractSurface_SandDisplay = Show(extractSurface_Sand, renderView1, 'GeometryRepresentation')

# trace defaults for the display properties.
extractSurface_SandDisplay.Set(
    Representation='Surface',
    ColorArrayName=['CELLS', 'facies'],
    LookupTable=faciesLUT,
)

# show data from extractSurface_Silt
extractSurface_SiltDisplay = Show(extractSurface_Silt, renderView1, 'GeometryRepresentation')

# trace defaults for the display properties.
extractSurface_SiltDisplay.Set(
    Representation='Surface',
    ColorArrayName=['CELLS', 'facies'],
    LookupTable=faciesLUT,
)

# setup the color legend parameters for each legend in this view

# get color legend/bar for faciesLUT in view renderView1
faciesLUTColorBar = GetScalarBar(faciesLUT, renderView1)
faciesLUTColorBar.Set(
    Title='facies',
    ComponentTitle='',
)

# set color bar visibility
faciesLUTColorBar.Visibility = 1

# show color legend
extractSurface_FloodPlaneDisplay.SetScalarBarVisibility(renderView1, True)

# show color legend
extractSurface_SandDisplay.SetScalarBarVisibility(renderView1, True)

# show color legend
extractSurface_SiltDisplay.SetScalarBarVisibility(renderView1, True)

# ----------------------------------------------------------------
# setup color maps and opacity maps used in the visualization
# note: the Get..() functions create a new object, if needed
# ----------------------------------------------------------------

# get opacity transfer function/opacity map for 'facies'
faciesPWF = GetOpacityTransferFunction('facies')
faciesPWF.Set(
    Points=[0.0, 0.0, 0.5, 0.0, 4.0, 1.0, 0.5, 0.0],
    ScalarRangeInitialized=1,
)

# ----------------------------------------------------------------
# setup animation scene, tracks and keyframes
# note: the Get..() functions create a new object, if needed
# ----------------------------------------------------------------

# get the time-keeper
timeKeeper1 = GetTimeKeeper()

# initialize the timekeeper

# get time animation track
timeAnimationCue1 = GetTimeTrack()

# initialize the animation track

# get animation scene
animationScene1 = GetAnimationScene()

# initialize the animation scene
animationScene1.Set(
    ViewModules=renderView1,
    Cues=timeAnimationCue1,
    AnimationTime=0.0,
)

# initialize the animation scene

# ----------------------------------------------------------------
# restore active source
SetActiveSource(fluvial_channelsvti)
# ----------------------------------------------------------------


##--------------------------------------------
## You may need to add some code at the end of this python script depending on your usage, eg:
#
## Render all views to see them appears
# RenderAllViews()
#
## Interact with the view, usefull when running from pvpython
# Interact()
#
## Save a screenshot of the active view
# SaveScreenshot("path/to/screenshot.png")
#
## Save a screenshot of a layout (multiple splitted view)
# SaveScreenshot("path/to/screenshot.png", GetLayout())
#
## Save all "Extractors" from the pipeline browser
# SaveExtracts()
#
## Save a animation of the current active view
# SaveAnimation()
#
## Please refer to the documentation of paraview.simple
## https://www.paraview.org/paraview-docs/latest/python/paraview.simple.html
##--------------------------------------------