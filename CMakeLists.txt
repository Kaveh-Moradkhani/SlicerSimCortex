cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(SlicerSimCortex)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/Kaveh-Moradkhani/SlicerSimCortex")
set(EXTENSION_CATEGORY "Surface Models")
set(EXTENSION_CONTRIBUTORS "Kaveh Moradkhani, Sylvain Bouix")
set(EXTENSION_DESCRIPTION "3D Slicer frontend for SimCortex cortical white and pial surface reconstruction from native T1w MRI using an external deep learning backend.")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/Kaveh-Moradkhani/SlicerSimCortex/main/SlicerSimCortex.png")
set(EXTENSION_SCREENSHOTURLS "")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(SimCortex)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
