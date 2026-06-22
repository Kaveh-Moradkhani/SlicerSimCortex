# SimCortex for 3D Slicer

SimCortex is a 3D Slicer extension for cortical surface reconstruction from a native T1-weighted MRI. It runs the SimCortex pipeline in Docker and automatically loads the reconstructed cortical surfaces back into Slicer.

The extension reconstructs four surfaces:

- left white surface
- left pial surface
- right white surface
- right pial surface

On the first run, SimCortex downloads the Docker image and pretrained model assets automatically. After that, you only need to select an input MRI, choose an output folder, and click **Run SimCortex**.

## Requirements

You need:

- 3D Slicer
- Docker
- an NVIDIA GPU with Docker GPU support
- a native T1-weighted MRI volume loaded in Slicer

You do **not** need to install PyTorch, MONAI, PyTorch3D, ANTsPy, or the SimCortex Python environment manually. These are included in the Docker image.

The extension uses this public Docker image:

```text
kavehmoradkhani/simcortex:0.2.4
```

## Quick start

Open 3D Slicer.  
Load a native T1-weighted MRI volume.  
Open the SimCortex module.  
Select the T1w volume as input.  
Choose an output folder.  
Select the GPU device, for example cuda:0.  
Click Run SimCortex.  

The first run may take longer because the Docker image and pretrained model assets are downloaded. Later runs reuse these files.

## Input

Use the original native T1w MRI as input.  
Do not select a SimCortex-preprocessed MNI-space image. The extension expects the original native MRI and handles preprocessing internally.

## Output

When the pipeline finishes, the generated surfaces are loaded into Slicer automatically.

The final surface files are also saved in:

<output-folder>/<subject>/<session>/surfaces/

Native-space output files look like this:

sub-001_ses-01_space-native_desc-deform_hemi-L_white.surf.ply  
sub-001_ses-01_space-native_desc-deform_hemi-L_pial.surf.ply  
sub-001_ses-01_space-native_desc-deform_hemi-R_white.surf.ply  
sub-001_ses-01_space-native_desc-deform_hemi-R_pial.surf.ply  

## First run

The first run does two setup steps automatically:

Downloads the SimCortex Docker image from Docker Hub.  
Downloads the pretrained model assets from Zenodo.  

The pretrained model assets are available here:

https://zenodo.org/records/20767921

DOI:  
10.5281/zenodo.20767921

The assets are cached in:

~/.slicersimcortex/assets/

You normally do not need to edit this path.

## Troubleshooting

### Docker is not installed or not running

SimCortex uses Docker to run the backend. If Docker is missing or not running, the extension cannot start the pipeline.  
Install Docker and make sure it is running before using SimCortex.

### CUDA is not available inside Docker

If the Docker image starts but the GPU is not visible, check that NVIDIA Docker GPU support is installed and working.

A useful terminal test is:

docker run --rm --gpus all nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04 nvidia-smi

### The first run is slow

This is expected. The Docker image is downloaded only once. The pretrained model assets are also downloaded only once.

### Docker cannot access the output folder

Choose an output folder in your home directory if Docker cannot access a network or project folder.

For example:

~/simcortex_output

## For developers

The extension is a lightweight Slicer frontend. By default, the SimCortex backend runs inside Docker.

The Docker image contains the Python environment and SimCortex pipeline code. The pretrained model assets are downloaded separately and mounted into the container at runtime.

A local Python backend is kept only for development and debugging.
