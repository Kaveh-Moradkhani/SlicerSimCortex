import os
import qt
import ctk
import slicer
from slicer.ScriptedLoadableModule import *


class SimCortex(ScriptedLoadableModule):
    """SimCortex Slicer extension module."""

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "SimCortex"
        self.parent.categories = ["Surface Models"]
        self.parent.dependencies = []
        self.parent.contributors = ["Kaveh Moradkhani, Sylvain Bouix"]
        self.parent.helpText = """
SimCortex performs cortical surface reconstruction from native T1w MRI.

This Slicer module is a frontend. The deep learning backend runs in an
external SimCortex Python environment, not inside Slicer's bundled Python.

Pretrained assets should be downloaded separately, for example from the
official SimCortex Zenodo record, then selected as one assets directory.
"""
        self.parent.acknowledgementText = """
This module uses SimCortex for cortical white and pial surface reconstruction.
"""


class SimCortexWidget(ScriptedLoadableModuleWidget):
    """User interface for SimCortex."""

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        self.logic = SimCortexLogic()
        self.pipelineProcess = None
        self.currentRunInfo = None

        # -------------------------
        # Input section
        # -------------------------
        inputCollapsibleButton = ctk.ctkCollapsibleButton()
        inputCollapsibleButton.text = "Input"
        self.layout.addWidget(inputCollapsibleButton)

        inputFormLayout = qt.QFormLayout(inputCollapsibleButton)

        self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
        self.inputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.inputVolumeSelector.selectNodeUponCreation = False
        self.inputVolumeSelector.addEnabled = False
        self.inputVolumeSelector.removeEnabled = False
        self.inputVolumeSelector.noneEnabled = True
        self.inputVolumeSelector.showHidden = False
        self.inputVolumeSelector.showChildNodeTypes = False
        self.inputVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.inputVolumeSelector.setToolTip("Select the native T1w MRI volume.")
        inputFormLayout.addRow("Input T1w volume: ", self.inputVolumeSelector)

        self.subjectLineEdit = qt.QLineEdit()
        self.subjectLineEdit.text = "sub-001"
        self.subjectLineEdit.setToolTip("Subject ID used by SimCortex, for example sub-001.")
        inputFormLayout.addRow("Subject ID: ", self.subjectLineEdit)

        self.sessionLineEdit = qt.QLineEdit()
        self.sessionLineEdit.text = "ses-01"
        self.sessionLineEdit.setToolTip("Session ID used by SimCortex, for example ses-01.")
        inputFormLayout.addRow("Session ID: ", self.sessionLineEdit)

        # -------------------------
        # Backend settings section
        # -------------------------
        backendCollapsibleButton = ctk.ctkCollapsibleButton()
        backendCollapsibleButton.text = "Backend settings"
        self.layout.addWidget(backendCollapsibleButton)

        backendFormLayout = qt.QFormLayout(backendCollapsibleButton)

        self.pythonExecutableLineEdit = self.createPathSelector(
            backendFormLayout,
            "SimCortex Python: ",
            "/path/to/simcortex-env/bin/python",
            self.onBrowsePythonExecutable,
        )

        self.projectRootLineEdit = self.createPathSelector(
            backendFormLayout,
            "SimCortex project root: ",
            "/path/to/SimCortex",
            self.onBrowseProjectRoot,
        )

        self.assetsRootLineEdit = self.createPathSelector(
            backendFormLayout,
            "Pretrained assets directory: ",
            "/path/to/SimCortexV2_pretrained_weights",
            self.onBrowseAssetsRoot,
        )

        self.outputRootLineEdit = self.createPathSelector(
            backendFormLayout,
            "Output root: ",
            "/path/to/output_root",
            self.onBrowseOutputRoot,
        )

        self.deviceComboBox = qt.QComboBox()
        self.deviceComboBox.addItems(["cuda:0", "cuda:1", "cpu"])
        self.deviceComboBox.setToolTip("Device used by the external SimCortex backend.")
        backendFormLayout.addRow("Device: ", self.deviceComboBox)

        self.exportNativeCheckBox = qt.QCheckBox()
        self.exportNativeCheckBox.checked = True
        self.exportNativeCheckBox.setToolTip(
            "Export final surfaces back to native scanner space for Slicer visualization."
        )
        backendFormLayout.addRow("Export native surfaces: ", self.exportNativeCheckBox)

        # -------------------------
        # Assets explanation
        # -------------------------
        assetsInfoCollapsibleButton = ctk.ctkCollapsibleButton()
        assetsInfoCollapsibleButton.text = "Expected pretrained assets"
        assetsInfoCollapsibleButton.collapsed = True
        self.layout.addWidget(assetsInfoCollapsibleButton)

        assetsInfoLayout = qt.QVBoxLayout(assetsInfoCollapsibleButton)

        self.assetsInfoLabel = qt.QLabel()
        self.assetsInfoLabel.setWordWrap(True)
        self.assetsInfoLabel.text = (
            "Select the folder that contains the fixed SimCortex pretrained assets. "
            "Expected files:\n\n"
            "MNI152_T1_1mm.nii.gz\n"
            "seg/seg_best_dice.pt\n"
            "deform/deform_best_model.pth\n\n"
            "If you select the outer unzipped Zenodo folder, the module will also check "
            "for a child folder named SimCortexV2_pretrained_weights."
        )
        assetsInfoLayout.addWidget(self.assetsInfoLabel)

        # -------------------------
        # Run section
        # -------------------------
        runCollapsibleButton = ctk.ctkCollapsibleButton()
        runCollapsibleButton.text = "Run"
        self.layout.addWidget(runCollapsibleButton)

        runLayout = qt.QVBoxLayout(runCollapsibleButton)

        self.validateBackendButton = qt.QPushButton("Validate backend environment")
        self.validateBackendButton.toolTip = (
            "Check the external SimCortex Python environment and required dependencies."
        )
        runLayout.addWidget(self.validateBackendButton)

        self.applyButton = qt.QPushButton("Apply")
        self.applyButton.toolTip = "Run SimCortex using the external backend environment."
        self.applyButton.enabled = True
        runLayout.addWidget(self.applyButton)

        self.cancelButton = qt.QPushButton("Cancel")
        self.cancelButton.toolTip = "Cancel the running SimCortex backend process."
        self.cancelButton.enabled = False
        runLayout.addWidget(self.cancelButton)

        self.logTextEdit = qt.QTextEdit()
        self.logTextEdit.readOnly = True
        self.logTextEdit.setMinimumHeight(190)
        runLayout.addWidget(self.logTextEdit)

        self.validateBackendButton.connect("clicked(bool)", self.onValidateBackendButton)
        self.applyButton.connect("clicked(bool)", self.onApplyButton)
        self.cancelButton.connect("clicked(bool)", self.onCancelButton)

        self.layout.addStretch(1)

        self.log("SimCortex module loaded.")
        self.log("Phase 2.6 UI is active.")
        self.log("Backend validation is available.")
        self.log("Full pipeline execution is available via Apply.")

    # -------------------------
    # UI helpers
    # -------------------------
    def createPathSelector(self, formLayout, label, placeholder, browseCallback):
        rowWidget = qt.QWidget()
        rowLayout = qt.QHBoxLayout(rowWidget)
        rowLayout.setContentsMargins(0, 0, 0, 0)

        lineEdit = qt.QLineEdit()
        lineEdit.setPlaceholderText(placeholder)
        rowLayout.addWidget(lineEdit)

        browseButton = qt.QPushButton("Browse")
        browseButton.setMaximumWidth(80)
        browseButton.connect("clicked(bool)", browseCallback)
        rowLayout.addWidget(browseButton)

        formLayout.addRow(label, rowWidget)
        return lineEdit

    def normalizeDialogResult(self, result):
        if isinstance(result, tuple) or isinstance(result, list):
            if len(result) == 0:
                return ""
            return result[0]
        return result

    def browseFile(self, title, lineEdit, fileFilter="All files (*)"):
        currentPath = lineEdit.text.strip()
        startDir = os.path.dirname(currentPath) if currentPath else os.path.expanduser("~")
        selected = qt.QFileDialog.getOpenFileName(
            slicer.util.mainWindow(), title, startDir, fileFilter
        )
        selected = self.normalizeDialogResult(selected)
        if selected:
            lineEdit.text = selected

    def browseDirectory(self, title, lineEdit):
        currentPath = lineEdit.text.strip()
        startDir = currentPath if currentPath else os.path.expanduser("~")
        selected = qt.QFileDialog.getExistingDirectory(
            slicer.util.mainWindow(), title, startDir
        )
        selected = self.normalizeDialogResult(selected)
        if selected:
            lineEdit.text = selected

    def qByteArrayToString(self, byteArray):
        try:
            return bytes(byteArray).decode("utf-8", errors="replace")
        except Exception:
            try:
                data = byteArray.data()
                if isinstance(data, bytes):
                    return data.decode("utf-8", errors="replace")
                return str(data)
            except Exception:
                return str(byteArray)

    # -------------------------
    # Browse callbacks
    # -------------------------
    def onBrowsePythonExecutable(self, checked=False):
        self.browseFile(
            "Select SimCortex Python executable",
            self.pythonExecutableLineEdit,
            "Python executable (*)",
        )

    def onBrowseProjectRoot(self, checked=False):
        self.browseDirectory(
            "Select SimCortex project root",
            self.projectRootLineEdit,
        )

    def onBrowseAssetsRoot(self, checked=False):
        self.browseDirectory(
            "Select pretrained assets directory",
            self.assetsRootLineEdit,
        )

    def onBrowseOutputRoot(self, checked=False):
        self.browseDirectory(
            "Select output root folder",
            self.outputRootLineEdit,
        )

    # -------------------------
    # Parameter collection
    # -------------------------
    def collectParameters(self):
        return {
            "inputVolume": self.inputVolumeSelector.currentNode(),
            "subject": self.subjectLineEdit.text.strip(),
            "session": self.sessionLineEdit.text.strip(),
            "pythonExecutable": self.pythonExecutableLineEdit.text.strip(),
            "projectRoot": self.projectRootLineEdit.text.strip(),
            "assetsRoot": self.assetsRootLineEdit.text.strip(),
            "outputRoot": self.outputRootLineEdit.text.strip(),
            "device": self.deviceComboBox.currentText,
            "exportNative": self.exportNativeCheckBox.checked,
        }

    # -------------------------
    # Main actions
    # -------------------------
    def log(self, message):
        self.logTextEdit.append(message)
        slicer.app.processEvents()

    def onValidateBackendButton(self, checked=False):
        params = self.collectParameters()

        ok, errorMessage = self.logic.validateBackendParameters(params)
        if not ok:
            slicer.util.errorDisplay(errorMessage)
            self.log("Backend validation failed before launch: " + errorMessage)
            return

        assets = self.logic.getAssetsPaths(params["assetsRoot"])

        self.log("")
        self.log("Starting backend environment validation...")
        self.log("Python: " + params["pythonExecutable"])
        self.log("Project root: " + params["projectRoot"])
        self.log("Assets root: " + assets["assetsRoot"])
        self.log("Device: " + params["device"])

        ok, output = self.logic.validateBackendEnvironment(
            pythonExecutable=params["pythonExecutable"],
            projectRoot=params["projectRoot"],
            assetsRoot=assets["assetsRoot"],
            device=params["device"],
        )

        self.log(output.strip())

        if ok:
            self.log("Backend environment validation PASSED.")
        else:
            slicer.util.errorDisplay("Backend environment validation failed. See log box for details.")
            self.log("Backend environment validation FAILED.")

    def setRunning(self, running):
        self.applyButton.enabled = not running
        self.validateBackendButton.enabled = not running
        self.cancelButton.enabled = running

    def onCancelButton(self, checked=False):
        if self.pipelineProcess is None:
            return

        self.log("Cancel requested. Terminating backend process...")
        self.pipelineProcess.terminate()

        if not self.pipelineProcess.waitForFinished(5000):
            self.log("Backend did not terminate quickly. Killing process...")
            self.pipelineProcess.kill()

    def onApplyButton(self, checked=False):
        if self.pipelineProcess is not None:
            slicer.util.errorDisplay("A SimCortex backend process is already running.")
            return

        params = self.collectParameters()

        ok, errorMessage = self.logic.validateParameters(params)
        if not ok:
            slicer.util.errorDisplay(errorMessage)
            self.log("Validation failed: " + errorMessage)
            return

        assets = self.logic.getAssetsPaths(params["assetsRoot"])

        try:
            runInfo = self.logic.preparePipelineRun(params, assets)
        except Exception as exc:
            slicer.util.errorDisplay("Failed to prepare SimCortex run: " + str(exc))
            self.log("Failed to prepare SimCortex run: " + str(exc))
            return

        self.currentRunInfo = runInfo

        self.log("")
        self.log("Starting SimCortex pipeline...")
        self.log("Saved input T1w: " + runInfo["t1wPath"])
        self.log("Output root: " + params["outputRoot"])
        self.log("Work root: " + runInfo["workRoot"])
        self.log("Command:")
        self.log(runInfo["commandString"])

        process = qt.QProcess()
        process.setProcessChannelMode(qt.QProcess.SeparateChannels)
        process.setWorkingDirectory(params["projectRoot"])
        process.setProcessEnvironment(
            self.logic.createExternalProcessEnvironment(params["pythonExecutable"])
        )

        process.connect("readyReadStandardOutput()", self.onPipelineReadyReadStandardOutput)
        process.connect("readyReadStandardError()", self.onPipelineReadyReadStandardError)
        process.connect("finished(int, QProcess::ExitStatus)", self.onPipelineFinished)

        self.pipelineProcess = process
        self.setRunning(True)

        process.start(params["pythonExecutable"], runInfo["args"])

        if not process.waitForStarted(10000):
            self.setRunning(False)
            self.pipelineProcess = None
            slicer.util.errorDisplay("Failed to start SimCortex backend process.")
            self.log("Failed to start backend process.")

    def onPipelineReadyReadStandardOutput(self):
        if self.pipelineProcess is None:
            return
        text = self.qByteArrayToString(self.pipelineProcess.readAllStandardOutput())
        if text:
            self.log(text.rstrip())

    def onPipelineReadyReadStandardError(self):
        if self.pipelineProcess is None:
            return
        text = self.qByteArrayToString(self.pipelineProcess.readAllStandardError())
        if text:
            self.log("STDERR: " + text.rstrip())

    def onPipelineFinished(self, exitCode, exitStatus):
        self.setRunning(False)

        runInfo = self.currentRunInfo
        self.pipelineProcess = None
        self.currentRunInfo = None

        self.log("")
        self.log("SimCortex backend process finished.")
        self.log("Exit code: " + str(exitCode))

        if exitCode == 0:
            self.log("Pipeline completed successfully.")
            if runInfo:
                self.log("Expected final surface directory:")
                self.log(runInfo["finalSurfaceDir"])
                self.log("Surface loading will be implemented in Phase 4.")
        else:
            slicer.util.errorDisplay("SimCortex backend failed. See log box for details.")
            self.log("Pipeline failed.")


class SimCortexLogic(ScriptedLoadableModuleLogic):
    """Logic for SimCortex module."""

    def getAssetsPaths(self, selectedAssetsRoot):
        """
        Resolve the SimCortex pretrained assets folder.

        Supports either:
        1. Direct selection of SimCortexV2_pretrained_weights/
        2. Selection of the outer unzipped Zenodo folder that contains
           SimCortexV2_pretrained_weights/
        """
        selectedAssetsRoot = os.path.abspath(selectedAssetsRoot)

        candidateRoots = [
            selectedAssetsRoot,
            os.path.join(selectedAssetsRoot, "SimCortexV2_pretrained_weights"),
        ]

        for root in candidateRoots:
            mniTemplate = os.path.join(root, "MNI152_T1_1mm.nii.gz")
            segCheckpoint = os.path.join(root, "seg", "seg_best_dice.pt")
            deformCheckpoint = os.path.join(root, "deform", "deform_best_model.pth")

            if (
                os.path.isfile(mniTemplate)
                and os.path.isfile(segCheckpoint)
                and os.path.isfile(deformCheckpoint)
            ):
                return {
                    "assetsRoot": root,
                    "mniTemplate": mniTemplate,
                    "segCheckpoint": segCheckpoint,
                    "deformCheckpoint": deformCheckpoint,
                }

        return {
            "assetsRoot": selectedAssetsRoot,
            "mniTemplate": os.path.join(selectedAssetsRoot, "MNI152_T1_1mm.nii.gz"),
            "segCheckpoint": os.path.join(selectedAssetsRoot, "seg", "seg_best_dice.pt"),
            "deformCheckpoint": os.path.join(selectedAssetsRoot, "deform", "deform_best_model.pth"),
        }

    def validateBackendParameters(self, params):
        requiredPaths = [
            ("SimCortex Python executable", params["pythonExecutable"]),
            ("SimCortex project root", params["projectRoot"]),
            ("Pretrained assets directory", params["assetsRoot"]),
        ]

        for label, path in requiredPaths:
            if not path:
                return False, "Please set: " + label

        if not os.path.isfile(params["pythonExecutable"]):
            return False, "SimCortex Python executable does not exist."

        if not os.path.isdir(params["projectRoot"]):
            return False, "SimCortex project root does not exist."

        if not os.path.isdir(params["assetsRoot"]):
            return False, "Pretrained assets directory does not exist."

        assets = self.getAssetsPaths(params["assetsRoot"])

        if not os.path.isfile(assets["mniTemplate"]):
            return False, (
                "MNI template was not found. Expected:\n"
                + assets["mniTemplate"]
                + "\n\nPlease select the folder containing MNI152_T1_1mm.nii.gz, "
                + "or the outer Zenodo folder containing SimCortexV2_pretrained_weights."
            )

        if not os.path.isfile(assets["segCheckpoint"]):
            return False, (
                "Segmentation checkpoint was not found. Expected:\n"
                + assets["segCheckpoint"]
            )

        if not os.path.isfile(assets["deformCheckpoint"]):
            return False, (
                "Deform checkpoint was not found. Expected:\n"
                + assets["deformCheckpoint"]
            )

        return True, ""

    def validateParameters(self, params):
        ok, message = self.validateBackendParameters(params)
        if not ok:
            return ok, message

        if params["inputVolume"] is None:
            return False, "Please select an input T1w volume."

        if not params["subject"]:
            return False, "Please enter a subject ID, for example sub-001."

        if not params["session"]:
            return False, "Please enter a session ID, for example ses-01."

        if not params["outputRoot"]:
            return False, "Please set: Output root"

        if not os.path.isdir(params["outputRoot"]):
            return False, "Output root folder does not exist."

        return True, ""

    def createExternalProcessEnvironment(self, pythonExecutable):
        """
        Create a clean environment for running external SimCortex Python.

        This avoids leaking Slicer's PYTHONHOME/PYTHONPATH into the conda
        environment, which previously caused Python 3.10 to accidentally use
        Slicer's Python 3.9 libraries.
        """
        systemEnv = qt.QProcessEnvironment.systemEnvironment()

        env = qt.QProcessEnvironment()
        for key in [
            "HOME",
            "USER",
            "LOGNAME",
            "SHELL",
            "PATH",
            "LANG",
            "LC_ALL",
            "CUDA_VISIBLE_DEVICES",
            "LD_LIBRARY_PATH",
        ]:
            value = systemEnv.value(key)
            if value:
                env.insert(key, value)

        pythonDir = os.path.dirname(pythonExecutable)
        condaPrefix = os.path.dirname(pythonDir)

        env.insert("CONDA_PREFIX", condaPrefix)
        env.insert("PATH", pythonDir + os.pathsep + env.value("PATH"))

        return env

    def preparePipelineRun(self, params, assets):
        subject = self.normalizeSubject(params["subject"])
        session = self.normalizeSession(params["session"])

        outputRoot = os.path.abspath(params["outputRoot"])
        workRoot = os.path.join(outputRoot, "work")
        inputDir = os.path.join(outputRoot, "_slicer_inputs", subject, session, "anat")
        os.makedirs(inputDir, exist_ok=True)

        t1wPath = os.path.join(inputDir, f"{subject}_{session}_T1w.nii.gz")

        ok = slicer.util.saveNode(params["inputVolume"], t1wPath)
        if not ok:
            raise RuntimeError("Could not save selected input volume as NIfTI: " + t1wPath)

        scriptPath = os.path.join(params["projectRoot"], "scripts", "run_pipeline.py")
        if not os.path.isfile(scriptPath):
            raise FileNotFoundError("run_pipeline.py was not found: " + scriptPath)

        args = [
            "-E",
            scriptPath,
            "single",
            "--out-root", outputRoot,
            "--work-root", workRoot,
            "--project-root", os.path.abspath(params["projectRoot"]),
            "--mni", assets["mniTemplate"],
            "--seg-ckpt", assets["segCheckpoint"],
            "--deform-ckpt", assets["deformCheckpoint"],
            "--device", params["device"],
            "--space", "MNI152",
            "--transform-type", "Affine",
            "--overwrite",
            "--initsurf-workers", "1",
            "--t1w", t1wPath,
            "--subject", subject,
            "--session", session,
        ]

        if params["exportNative"]:
            args.append("--export-native")

        finalSurfaceDir = os.path.join(outputRoot, subject, session, "surfaces")
        commandString = " ".join([params["pythonExecutable"]] + args)

        return {
            "args": args,
            "commandString": commandString,
            "t1wPath": t1wPath,
            "workRoot": workRoot,
            "subject": subject,
            "session": session,
            "finalSurfaceDir": finalSurfaceDir,
        }

    def normalizeSubject(self, subject):
        subject = str(subject).strip()
        if not subject:
            return "sub-001"
        return subject if subject.startswith("sub-") else "sub-" + subject

    def normalizeSession(self, session):
        session = str(session).strip()
        if not session:
            return "ses-01"
        return session if session.startswith("ses-") else "ses-" + session

    def validateBackendEnvironment(self, pythonExecutable, projectRoot, assetsRoot, device):
        validationCode = r'''
import importlib
import os
import sys
import traceback

project_root = sys.argv[1]
assets_root = sys.argv[2]
device = sys.argv[3]

src_root = os.path.join(project_root, "src")
if os.path.isdir(src_root):
    sys.path.insert(0, src_root)
sys.path.insert(0, project_root)

print("Python executable:", sys.executable)
print("Python version:", sys.version.replace("\n", " "))
print("Project root:", project_root)
print("Assets root:", assets_root)
print("Requested device:", device)
print("")

required_assets = [
    os.path.join(assets_root, "MNI152_T1_1mm.nii.gz"),
    os.path.join(assets_root, "seg", "seg_best_dice.pt"),
    os.path.join(assets_root, "deform", "deform_best_model.pth"),
]

for path in required_assets:
    print("Checking asset:", path)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)

print("")
print("Import checks:")

checks = [
    ("simcortex", "simcortex"),
    ("torch", "torch"),
    ("monai", "monai"),
    ("pytorch3d", "pytorch3d"),
    ("ants", "ants"),
    ("trimesh", "trimesh"),
    ("hydra", "hydra"),
]

for label, module_name in checks:
    module = importlib.import_module(module_name)
    version = getattr(module, "__version__", "unknown")
    print(f"  {label}: OK, version={version}")

print("")
import torch
print("Torch CUDA available:", torch.cuda.is_available())
print("Torch CUDA device count:", torch.cuda.device_count())

if device.startswith("cuda"):
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA device was requested, but torch.cuda.is_available() is False.")

    try:
        device_index = int(device.split(":")[1])
    except Exception:
        raise RuntimeError("CUDA device must look like cuda:0 or cuda:1.")

    if device_index >= torch.cuda.device_count():
        raise RuntimeError(
            f"Requested {device}, but only {torch.cuda.device_count()} CUDA device(s) are visible."
        )

    print("Selected CUDA device name:", torch.cuda.get_device_name(device_index))

print("")
print("Backend validation completed successfully.")
'''

        process = qt.QProcess()
        process.setProcessChannelMode(qt.QProcess.SeparateChannels)

        # Use Slicer's original startup environment, not the modified runtime
        # environment. This avoids leaking Slicer's Python 3.9 paths into the
        # external SimCortex Python/conda environment.
        startupEnv = slicer.util.startupEnvironment()

        env = qt.QProcessEnvironment()

        for key, value in startupEnv.items():
            env.insert(key, value)

        # Explicitly remove Python variables that can contaminate the external
        # interpreter. We will set a clean PYTHONPATH below.
        for key in ["PYTHONHOME", "PYTHONPATH"]:
            if env.contains(key):
                env.remove(key)

        srcRoot = os.path.join(projectRoot, "src")
        env.insert("PYTHONPATH", os.pathsep.join([srcRoot, projectRoot]))

        process.setProcessEnvironment(env)

        args = ["-E", "-c", validationCode, projectRoot, assetsRoot, device]
        process.start(pythonExecutable, args)

        finished = process.waitForFinished(120000)

        stdoutText = self._qByteArrayToString(process.readAllStandardOutput())
        stderrText = self._qByteArrayToString(process.readAllStandardError())

        if not finished:
            process.kill()
            return False, "Backend validation timed out after 120 seconds.\n\n" + stdoutText + "\n" + stderrText

        exitCode = process.exitCode()

        combinedOutput = stdoutText
        if stderrText.strip():
            combinedOutput += "\nSTDERR:\n" + stderrText

        return exitCode == 0, combinedOutput

    def _qByteArrayToString(self, byteArray):
        try:
            return bytes(byteArray).decode("utf-8", errors="replace")
        except Exception:
            try:
                data = byteArray.data()
                if isinstance(data, bytes):
                    return data.decode("utf-8", errors="replace")
                return str(data)
            except Exception:
                return str(byteArray)


class SimCortexTest(ScriptedLoadableModuleTest):
    """Basic test placeholder."""

    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_SimCortexLoad()

    def test_SimCortexLoad(self):
        self.delayDisplay("SimCortex module loaded successfully.")
