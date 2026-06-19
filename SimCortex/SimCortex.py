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
        self.parent.contributors = ["Shakila Moradi, Kaveh Lab"]
        self.parent.helpText = """
SimCortex performs cortical surface reconstruction from native T1w MRI.

This Slicer module is a frontend. The deep learning backend runs in an
external SimCortex Python environment, not inside Slicer's bundled Python.
"""
        self.parent.acknowledgementText = """
This module uses SimCortex for cortical white and pial surface reconstruction.
"""


class SimCortexWidget(ScriptedLoadableModuleWidget):
    """User interface for SimCortex."""

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        self.logic = SimCortexLogic()

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
        inputFormLayout.addRow("Subject ID: ", self.subjectLineEdit)

        self.sessionLineEdit = qt.QLineEdit()
        self.sessionLineEdit.text = "ses-01"
        inputFormLayout.addRow("Session ID: ", self.sessionLineEdit)

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

        self.mniTemplateLineEdit = self.createPathSelector(
            backendFormLayout,
            "MNI template: ",
            "/path/to/MNI152_T1_1mm.nii.gz",
            self.onBrowseMniTemplate,
        )

        self.segCheckpointLineEdit = self.createPathSelector(
            backendFormLayout,
            "Seg checkpoint: ",
            "/path/to/seg_best_dice.pt",
            self.onBrowseSegCheckpoint,
        )

        self.deformCheckpointLineEdit = self.createPathSelector(
            backendFormLayout,
            "Deform checkpoint: ",
            "/path/to/deform_best_model.pth",
            self.onBrowseDeformCheckpoint,
        )

        self.outputRootLineEdit = self.createPathSelector(
            backendFormLayout,
            "Output root: ",
            "/path/to/output_root",
            self.onBrowseOutputRoot,
        )

        self.deviceComboBox = qt.QComboBox()
        self.deviceComboBox.addItems(["cuda:0", "cuda:1", "cpu"])
        backendFormLayout.addRow("Device: ", self.deviceComboBox)

        self.exportNativeCheckBox = qt.QCheckBox()
        self.exportNativeCheckBox.checked = True
        self.exportNativeCheckBox.setToolTip(
            "Export final surfaces back to native scanner space for Slicer visualization."
        )
        backendFormLayout.addRow("Export native surfaces: ", self.exportNativeCheckBox)

        runCollapsibleButton = ctk.ctkCollapsibleButton()
        runCollapsibleButton.text = "Run"
        self.layout.addWidget(runCollapsibleButton)

        runLayout = qt.QVBoxLayout(runCollapsibleButton)

        self.applyButton = qt.QPushButton("Apply")
        self.applyButton.toolTip = "Validate settings. Backend execution will be added in Phase 3."
        self.applyButton.enabled = True
        runLayout.addWidget(self.applyButton)

        self.logTextEdit = qt.QTextEdit()
        self.logTextEdit.readOnly = True
        self.logTextEdit.setMinimumHeight(180)
        runLayout.addWidget(self.logTextEdit)

        self.applyButton.connect("clicked(bool)", self.onApplyButton)

        self.layout.addStretch(1)

        self.log("SimCortex module loaded.")
        self.log("Phase 2.4 UI is active. Browse buttons are available.")
        self.log("Backend execution is not implemented yet.")

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

    def onBrowseMniTemplate(self, checked=False):
        self.browseFile(
            "Select MNI template",
            self.mniTemplateLineEdit,
            "NIfTI files (*.nii *.nii.gz);;All files (*)",
        )

    def onBrowseSegCheckpoint(self, checked=False):
        self.browseFile(
            "Select segmentation checkpoint",
            self.segCheckpointLineEdit,
            "PyTorch checkpoint (*.pt *.pth);;All files (*)",
        )

    def onBrowseDeformCheckpoint(self, checked=False):
        self.browseFile(
            "Select deform checkpoint",
            self.deformCheckpointLineEdit,
            "PyTorch checkpoint (*.pt *.pth);;All files (*)",
        )

    def onBrowseOutputRoot(self, checked=False):
        self.browseDirectory(
            "Select output root folder",
            self.outputRootLineEdit,
        )

    def log(self, message):
        self.logTextEdit.append(message)
        slicer.app.processEvents()

    def onApplyButton(self, checked=False):
        params = {
            "inputVolume": self.inputVolumeSelector.currentNode(),
            "subject": self.subjectLineEdit.text.strip(),
            "session": self.sessionLineEdit.text.strip(),
            "pythonExecutable": self.pythonExecutableLineEdit.text.strip(),
            "projectRoot": self.projectRootLineEdit.text.strip(),
            "mniTemplate": self.mniTemplateLineEdit.text.strip(),
            "segCheckpoint": self.segCheckpointLineEdit.text.strip(),
            "deformCheckpoint": self.deformCheckpointLineEdit.text.strip(),
            "outputRoot": self.outputRootLineEdit.text.strip(),
            "device": self.deviceComboBox.currentText,
            "exportNative": self.exportNativeCheckBox.checked,
        }

        ok, errorMessage = self.logic.validateParameters(params)
        if not ok:
            slicer.util.errorDisplay(errorMessage)
            self.log("Validation failed: " + errorMessage)
            return

        self.log("Validation passed.")
        self.log("Backend execution will be implemented in Phase 3.")


class SimCortexLogic(ScriptedLoadableModuleLogic):
    """Logic for SimCortex module."""

    def validateParameters(self, params):
        if params["inputVolume"] is None:
            return False, "Please select an input T1w volume."

        if not params["subject"]:
            return False, "Please enter a subject ID, for example sub-001."

        if not params["session"]:
            return False, "Please enter a session ID, for example ses-01."

        requiredPaths = [
            ("SimCortex Python executable", params["pythonExecutable"]),
            ("SimCortex project root", params["projectRoot"]),
            ("MNI template", params["mniTemplate"]),
            ("Segmentation checkpoint", params["segCheckpoint"]),
            ("Deform checkpoint", params["deformCheckpoint"]),
            ("Output root", params["outputRoot"]),
        ]

        for label, path in requiredPaths:
            if not path:
                return False, f"Please set: {label}"

        if not os.path.isfile(params["pythonExecutable"]):
            return False, "SimCortex Python executable does not exist."

        if not os.path.isdir(params["projectRoot"]):
            return False, "SimCortex project root does not exist."

        if not os.path.isfile(params["mniTemplate"]):
            return False, "MNI template file does not exist."

        if not os.path.isfile(params["segCheckpoint"]):
            return False, "Segmentation checkpoint file does not exist."

        if not os.path.isfile(params["deformCheckpoint"]):
            return False, "Deform checkpoint file does not exist."

        if not os.path.isdir(params["outputRoot"]):
            return False, "Output root folder does not exist."

        return True, ""


class SimCortexTest(ScriptedLoadableModuleTest):
    """Basic test placeholder."""

    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_SimCortexLoad()

    def test_SimCortexLoad(self):
        self.delayDisplay("SimCortex module loaded successfully.")
