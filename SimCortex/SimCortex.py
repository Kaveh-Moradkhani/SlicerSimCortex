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
f
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

        self.nativeInputWarningLabel = qt.QLabel()
        self.nativeInputWarningLabel.setWordWrap(True)
        self.nativeInputWarningLabel.text = (
            "Important: select the original native T1w MRI as input. "
        )
        inputFormLayout.addRow("", self.nativeInputWarningLabel)

        # -------------------------
        # Public settings section
        # -------------------------
        settingsCollapsibleButton = ctk.ctkCollapsibleButton()
        settingsCollapsibleButton.text = "Settings"
        self.layout.addWidget(settingsCollapsibleButton)

        settingsFormLayout = qt.QFormLayout(settingsCollapsibleButton)

        self.modelAssetsInfoLabel = qt.QLabel()
        self.modelAssetsInfoLabel.setWordWrap(True)
        self.modelAssetsInfoLabel.text = (
            "Downloaded automatically on first run."
        )
        settingsFormLayout.addRow("Model assets: ", self.modelAssetsInfoLabel)

        self.outputRootLineEdit = self.createPathSelector(
            settingsFormLayout,
            "Output folder: ",
            "/path/to/output_root",
            self.onBrowseOutputRoot,
        )

        self.deviceComboBox = qt.QComboBox()
        self.deviceComboBox.addItems(["cuda:0", "cuda:1", "cpu"])
        self.deviceComboBox.setToolTip("GPU/CPU device used by SimCortex.")
        settingsFormLayout.addRow("Device: ", self.deviceComboBox)

        self.saveSettingsButton = qt.QPushButton("Save settings")
        self.saveSettingsButton.setToolTip(
            "Save model/assets folder, output folder, and device selection."
        )
        settingsFormLayout.addRow("", self.saveSettingsButton)

        # -------------------------
        # Advanced backend section
        # -------------------------
        advancedCollapsibleButton = ctk.ctkCollapsibleButton()
        advancedCollapsibleButton.text = "Advanced Docker/backend settings"
        advancedCollapsibleButton.collapsed = True
        self.layout.addWidget(advancedCollapsibleButton)

        advancedFormLayout = qt.QFormLayout(advancedCollapsibleButton)

        self.backendModeComboBox = qt.QComboBox()
        self.backendModeComboBox.addItems(["Docker", "Local Python"])
        self.backendModeComboBox.setToolTip(
            "Docker is recommended for public use. Local Python is only for development/debugging."
        )
        advancedFormLayout.addRow("Backend mode: ", self.backendModeComboBox)

        self.dockerImageLineEdit = qt.QLineEdit()
        self.dockerImageLineEdit.text = "kavehmoradkhani/simcortex:0.2.4"
        self.dockerImageLineEdit.setToolTip(
            "Public SimCortex Docker image used by the Docker backend."
        )
        advancedFormLayout.addRow("Docker image: ", self.dockerImageLineEdit)

        self.pythonExecutableLineEdit = self.createPathSelector(
            advancedFormLayout,
            "SimCortex Python: ",
            "/path/to/simcortex-env/bin/python",
            self.onBrowsePythonExecutable,
        )

        self.projectRootLineEdit = self.createPathSelector(
            advancedFormLayout,
            "SimCortex project root: ",
            "/path/to/SimCortex",
            self.onBrowseProjectRoot,
        )

        self.assetsRootLineEdit = self.createPathSelector(
            advancedFormLayout,
            "Pretrained assets directory: ",
            "",
            self.onBrowseAssetsRoot,
        )

        self.exportNativeCheckBox = qt.QCheckBox()
        self.exportNativeCheckBox.checked = True
        self.exportNativeCheckBox.setToolTip(
            "Export final surfaces back to native scanner space for Slicer visualization. Recommended: enabled."
        )
        advancedFormLayout.addRow("Export native surfaces: ", self.exportNativeCheckBox)
        advancedCollapsibleButton.collapsed = True
        advancedCollapsibleButton.hide()

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
        assetsInfoCollapsibleButton.collapsed = True
        assetsInfoCollapsibleButton.hide()

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
        self.validateBackendButton.hide()

        self.applyButton = qt.QPushButton("Run SimCortex")
        self.applyButton.toolTip = "Run SimCortex on the selected native T1w MRI."
        self.applyButton.enabled = True
        runLayout.addWidget(self.applyButton)

        self.cancelButton = qt.QPushButton("Cancel")
        self.cancelButton.toolTip = "Cancel the running SimCortex backend process."
        self.cancelButton.enabled = False
        runLayout.addWidget(self.cancelButton)

        self.clearLogButton = qt.QPushButton("Clear log")
        self.clearLogButton.toolTip = "Clear the SimCortex log display."
        runLayout.addWidget(self.clearLogButton)

        self.progressBar = qt.QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        self.progressBar.setFormat("Idle")
        self.progressBar.setToolTip("Approximate SimCortex pipeline progress based on stage log messages.")
        runLayout.addWidget(self.progressBar)

        self.logTextEdit = qt.QTextEdit()
        self.logTextEdit.readOnly = True
        self.logTextEdit.setMinimumHeight(190)
        runLayout.addWidget(self.logTextEdit)

        self.validateBackendButton.connect("clicked(bool)", self.onValidateBackendButton)
        self.applyButton.connect("clicked(bool)", self.onApplyButton)
        self.cancelButton.connect("clicked(bool)", self.onCancelButton)
        self.clearLogButton.connect("clicked(bool)", self.onClearLogButton)
        self.saveSettingsButton.connect("clicked(bool)", self.onSaveSettingsButton)
        self.backendModeComboBox.connect("currentIndexChanged(int)", self.onBackendModeChanged)

        self.layout.addStretch(1)

        self.loadSettings()
        self.updateBackendModeUi()

        self.log("SimCortex module loaded.")
        self.log("SimCortex extension is ready.")
        self.log("Docker backend is the recommended public mode.")
        self.log("Select a native T1w MRI, pretrained assets, output folder, then click Run SimCortex.")

    def onBackendModeChanged(self, index):
        self.updateBackendModeUi()

    def updateBackendModeUi(self):
        isDocker = self.backendModeComboBox.currentText == "Docker"

        self.dockerImageLineEdit.enabled = isDocker

        self.pythonExecutableLineEdit.enabled = not isDocker
        self.projectRootLineEdit.enabled = not isDocker

        modeText = "Docker" if isDocker else "Local Python"
        self.validateBackendButton.text = "Validate " + modeText + " backend"
        self.applyButton.toolTip = "Run SimCortex using the " + modeText + " backend."

    # -------------------------
    # UI helpers
    # -------------------------
    def createPathSelector(self, formLayout, label, placeholder, browseCallback):
        rowWidget = qt.QWidget()
        rowLayout = qt.QHBoxLayout(rowWidget)
        rowLayout.setContentsMargins(0, 0, 0, 0)

        lineEdit = qt.QLineEdit()
        lineEdit.setPlaceholderText(placeholder)
        lineEdit.setToolTip(placeholder)
        lineEdit.setMinimumWidth(260)
        lineEdit.connect("textChanged(QString)", lambda text, w=lineEdit: w.setToolTip(text))
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
    # Persistent settings
    # -------------------------
    def settingsPrefix(self):
        return "SimCortex/"

    def onSaveSettingsButton(self, checked=False):
        self.saveSettings()
        self.log("Settings saved.")

    def saveSettings(self):
        settings = qt.QSettings()
        prefix = self.settingsPrefix()

        settings.setValue(prefix + "backendMode", self.backendModeComboBox.currentText)
        settings.setValue(prefix + "dockerImage", self.dockerImageLineEdit.text.strip())
        settings.setValue(prefix + "pythonExecutable", self.pythonExecutableLineEdit.text.strip())
        settings.setValue(prefix + "projectRoot", self.projectRootLineEdit.text.strip())
        settings.setValue(prefix + "assetsRoot", self.assetsRootLineEdit.text.strip())
        settings.setValue(prefix + "outputRoot", self.outputRootLineEdit.text.strip())
        settings.setValue(prefix + "device", self.deviceComboBox.currentText)
        settings.setValue(prefix + "exportNative", "true" if self.exportNativeCheckBox.checked else "false")

    def loadSettings(self):
        settings = qt.QSettings()
        prefix = self.settingsPrefix()

        backendMode = settings.value(prefix + "backendMode", "")
        dockerImage = settings.value(prefix + "dockerImage", "")
        pythonExecutable = settings.value(prefix + "pythonExecutable", "")
        projectRoot = settings.value(prefix + "projectRoot", "")
        assetsRoot = settings.value(prefix + "assetsRoot", "")
        outputRoot = settings.value(prefix + "outputRoot", "")
        device = settings.value(prefix + "device", "")
        exportNative = settings.value(prefix + "exportNative", "")

        # Public release uses Docker by default. Local Python remains only for internal development.
        index = self.backendModeComboBox.findText("Docker")
        if index >= 0:
            self.backendModeComboBox.setCurrentIndex(index)
        defaultDockerImage = "kavehmoradkhani/simcortex:0.2.4"
        if dockerImage:
            dockerImageText = str(dockerImage).strip()
            if dockerImageText in ["simcortex:0.2.3", "simcortex:0.2.4"]:
                dockerImageText = defaultDockerImage
            self.dockerImageLineEdit.text = dockerImageText
        else:
            self.dockerImageLineEdit.text = defaultDockerImage

        if pythonExecutable:
            self.pythonExecutableLineEdit.text = str(pythonExecutable)
        if projectRoot:
            self.projectRootLineEdit.text = str(projectRoot)
        if assetsRoot:
            self.assetsRootLineEdit.text = str(assetsRoot)
        if outputRoot:
            self.outputRootLineEdit.text = str(outputRoot)

        if device:
            index = self.deviceComboBox.findText(str(device))
            if index >= 0:
                self.deviceComboBox.setCurrentIndex(index)

        if exportNative != "":
            self.exportNativeCheckBox.checked = str(exportNative).lower() in ["true", "1", "yes"]


    # -------------------------
    # Parameter collection
    # -------------------------
    def collectParameters(self):
        return {
            "inputVolume": self.inputVolumeSelector.currentNode(),
            "subject": self.subjectLineEdit.text.strip(),
            "session": self.sessionLineEdit.text.strip(),
            "backendMode": self.backendModeComboBox.currentText,
            "dockerImage": self.dockerImageLineEdit.text.strip(),
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
    def onClearLogButton(self, checked=False):
        self.logTextEdit.clear()

    def log(self, message):
        self.logTextEdit.append(str(message))
        self.logTextEdit.ensureCursorVisible()
        slicer.app.processEvents()

    def setProgress(self, value, label):
        value = max(0, min(100, int(value)))
        self.progressBar.setValue(value)
        self.progressBar.setFormat(f"{value}% - {label}")
        slicer.app.processEvents()

    def updateProgressFromText(self, text):
        if not text:
            return

        progressRules = [
            ("Unable to find image", 2, "Preparing Docker image"),
            ("Pulling from", 5, "Downloading SimCortex Docker image"),
            ("Downloading", 10, "Downloading SimCortex Docker image"),
            ("Extracting", 25, "Installing SimCortex Docker image"),
            ("Pull complete", 35, "Docker image layer ready"),
            ("Digest:", 40, "Docker image ready"),
            ("Status: Downloaded newer image", 40, "Docker image ready"),
            ("Status: Image is up to date", 40, "Docker image ready"),
            ("[preproc] started", 45, "Preprocessing"),
            ("[preproc] finished", 55, "Preprocessing complete"),
            ("[segmentation] started", 60, "Segmentation"),
            ("[segmentation] finished", 70, "Segmentation complete"),
            ("[initsurf] started", 75, "Initial surface generation"),
            ("[initsurf] finished", 85, "Initial surfaces complete"),
            ("[deform] started", 88, "Surface deformation"),
            ("[deform] finished", 94, "Surface deformation complete"),
            ("[collect] Copied", 96, "Collecting surfaces"),
            ("[export-native] Manifest written", 98, "Exporting native surfaces"),
            ("[export-native] Exported", 99, "Native export complete"),
            ("Pipeline finished successfully", 99, "Pipeline complete"),
        ]

        for token, value, label in progressRules:
            if token in text:
                self.setProgress(value, label)

    def onValidateBackendButton(self, checked=False):
        try:
            self._onValidateBackendButtonImpl(checked)
        except Exception as exc:
            import traceback
            self.log("Validation crashed with an internal error:")
            self.log(traceback.format_exc())

    def _onValidateBackendButtonImpl(self, checked=False):
        params = self.collectParameters()

        if params["backendMode"] == "Docker":
            ok, errorMessage = self.logic.validateDockerParameters(params)
            if not ok:
                self.log("Docker backend validation failed:")
                self.log(errorMessage)
                return

            assets = self.logic.getAssetsPaths(params["assetsRoot"])

            self.log("Validating Docker backend...")
            self.log("Docker image: " + params["dockerImage"])
            self.log("Assets root: " + assets["assetsRoot"])
            self.log("Device: " + params["device"])

            ok, output = self.logic.validateDockerEnvironment(
                dockerImage=params["dockerImage"],
                device=params["device"],
            )

            self.log(output.strip())

            if ok:
                self.log("Docker backend validation succeeded.")
                self.saveSettings()
            else:
                self.log("Docker backend validation failed.")
            return

        ok, errorMessage = self.logic.validateBackendParameters(params)
        if not ok:
            self.log("Backend validation failed:")
            self.log(errorMessage)
            return

        assets = self.logic.getAssetsPaths(params["assetsRoot"])

        self.log("Validating local Python backend environment...")
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
            self.log("Local Python backend validation succeeded.")
            self.saveSettings()
        else:
            self.log("Local Python backend validation failed.")

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

        ok, errorMessage = self.logic.validateBasicRunParameters(params)
        if not ok:
            slicer.util.errorDisplay(errorMessage)
            self.log("Validation failed: " + errorMessage)
            return

        if params["backendMode"] == "Docker" and not self.logic.dockerImageExists(params["dockerImage"]):
            self.startDockerImagePull(params["dockerImage"])
            return

        if params["backendMode"] == "Docker" and not self.logic.assetsAreValid(params["assetsRoot"]):
            ok = self.downloadPretrainedAssetsForRun()
            if not ok:
                return
            params = self.collectParameters()

        ok, errorMessage = self.logic.validateParameters(params)
        if not ok:
            slicer.util.errorDisplay(errorMessage)
            self.log("Validation failed: " + errorMessage)
            return

        assets = self.logic.getAssetsPaths(params["assetsRoot"])
        self.saveSettings()

        try:
            runInfo = self.logic.preparePipelineRun(params, assets)
        except Exception as exc:
            slicer.util.errorDisplay("Failed to prepare SimCortex run: " + str(exc))
            self.log("Failed to prepare SimCortex run: " + str(exc))
            return

        self.currentRunInfo = runInfo
        self.setProgress(0, "Starting")

        self.log("")
        self.log("Starting SimCortex pipeline...")
        self.log("Saved input T1w: " + runInfo["t1wPath"])
        self.log("Output root: " + params["outputRoot"])
        self.log("Work root: " + runInfo["workRoot"])
        self.log("Command:")
        self.log(runInfo["commandString"])

        process = qt.QProcess()
        process.setProcessChannelMode(qt.QProcess.SeparateChannels)

        workingDirectory = runInfo.get("workingDirectory", "")
        if workingDirectory:
            process.setWorkingDirectory(workingDirectory)

        if runInfo.get("backendMode") == "Docker":
            process.setProcessEnvironment(qt.QProcessEnvironment.systemEnvironment())
        else:
            process.setProcessEnvironment(
                self.logic.createExternalProcessEnvironment(params["pythonExecutable"])
            )

        process.connect("readyReadStandardOutput()", self.onPipelineReadyReadStandardOutput)
        process.connect("readyReadStandardError()", self.onPipelineReadyReadStandardError)
        process.connect("finished(int, QProcess::ExitStatus)", self.onPipelineFinished)

        self.pipelineProcess = process
        self.setRunning(True)

        process.start(runInfo["program"], runInfo["args"])

        if not process.waitForStarted(10000):
            self.setRunning(False)
            self.pipelineProcess = None
            slicer.util.errorDisplay("Failed to start SimCortex backend process.")
            self.log("Failed to start backend process.")

    def downloadPretrainedAssetsForRun(self):
        self.log("")
        self.log("SimCortex pretrained model/assets were not found.")
        self.log("Downloading pretrained assets from Zenodo:")
        self.log("https://zenodo.org/records/20767921")
        self.log("This is required only once.")
        self.setProgress(40, "Preparing pretrained assets")

        try:
            assetsRoot = self.logic.downloadPretrainedAssets(
                logCallback=self.log,
                progressCallback=self.setProgress,
            )
        except Exception as exc:
            self.setProgress(0, "Pretrained assets download failed")
            slicer.util.errorDisplay(
                "Failed to download or prepare SimCortex pretrained assets. "
                "See the log box for details."
            )
            self.log("Pretrained assets setup failed: " + str(exc))
            return False

        self.assetsRootLineEdit.text = assetsRoot
        self.saveSettings()

        self.setProgress(44, "Pretrained assets ready")
        self.log("Pretrained assets are ready:")
        self.log(assetsRoot)
        return True

    def startDockerImagePull(self, dockerImage):
        self.log("")
        self.log("SimCortex Docker image is not installed locally.")
        self.log("Downloading SimCortex Docker image:")
        self.log(dockerImage)
        self.log("This can take several minutes on the first run.")
        self.setProgress(0, "Preparing Docker image")

        process = qt.QProcess()
        process.setProcessChannelMode(qt.QProcess.SeparateChannels)
        process.setProcessEnvironment(qt.QProcessEnvironment.systemEnvironment())

        process.connect("readyReadStandardOutput()", self.onPipelineReadyReadStandardOutput)
        process.connect("readyReadStandardError()", self.onPipelineReadyReadStandardError)
        process.connect("finished(int, QProcess::ExitStatus)", self.onDockerImagePullFinished)

        self.pipelineProcess = process
        self.setRunning(True)

        process.start("docker", ["pull", dockerImage])

        if not process.waitForStarted(10000):
            self.setRunning(False)
            self.pipelineProcess = None
            slicer.util.errorDisplay("Failed to start Docker image download.")
            self.log("Failed to start Docker image download. Make sure Docker is installed and running.")

    def onDockerImagePullFinished(self, exitCode, exitStatus):
        self.setRunning(False)

        if self.pipelineProcess is not None:
            remainingStdout = self.qByteArrayToString(self.pipelineProcess.readAllStandardOutput())
            remainingStderr = self.qByteArrayToString(self.pipelineProcess.readAllStandardError())
            if remainingStdout:
                self.updateProgressFromText(remainingStdout)
                self.log(remainingStdout.rstrip())
            if remainingStderr:
                self.updateProgressFromText(remainingStderr)
                self.log("STDERR: " + remainingStderr.rstrip())

        self.pipelineProcess = None

        self.log("")
        self.log("Docker image download finished.")
        self.log("Exit code: " + str(exitCode))

        if exitCode != 0:
            self.setProgress(0, "Docker image download failed")
            slicer.util.errorDisplay(
                "Failed to download the SimCortex Docker image. "
                "Make sure Docker is installed, running, and has network access."
            )
            return

        self.setProgress(40, "Docker image ready")
        self.log("Docker image is ready. Starting SimCortex pipeline now.")

        # Continue with the same Run workflow. The image now exists locally,
        # so onApplyButton will proceed directly to pipeline execution.
        self.onApplyButton()

    def onPipelineReadyReadStandardOutput(self):
        if self.pipelineProcess is None:
            return
        text = self.qByteArrayToString(self.pipelineProcess.readAllStandardOutput())
        if text:
            self.updateProgressFromText(text)
            self.log(text.rstrip())

    def onPipelineReadyReadStandardError(self):
        if self.pipelineProcess is None:
            return
        text = self.qByteArrayToString(self.pipelineProcess.readAllStandardError())
        if text:
            self.updateProgressFromText(text)
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
            self.setProgress(99, "Pipeline complete")
            self.log("Pipeline completed successfully.")
            if runInfo:
                self.log("Expected final surface directory:")
                self.log(runInfo["finalSurfaceDir"])
                self.loadGeneratedSurfaces(runInfo)
        else:
            self.setProgress(0, "Failed")
            slicer.util.errorDisplay("SimCortex backend failed. See log box for details.")
            self.log("Pipeline failed.")


    def loadGeneratedSurfaces(self, runInfo):
        surfaceFiles = self.logic.getExpectedSurfaceFiles(runInfo)

        missing = [item["path"] for item in surfaceFiles if not os.path.isfile(item["path"])]
        if missing:
            self.log("Surface loading skipped because some expected files are missing:")
            for path in missing:
                self.log("  missing: " + path)
            slicer.util.errorDisplay("Some expected SimCortex output surfaces were not found. See log box.")
            return

        self.log("Loading generated surfaces into Slicer...")

        loadedNodes = []
        for item in surfaceFiles:
            # SimCortex exported surfaces are in RAS-mm coordinates.
            # Use vtkMRMLModelStorageNode directly so the coordinate system
            # is explicitly set, equivalent to ticking RAS in the manual loader.
            self.log("  loading RAS: " + os.path.basename(item["path"]))
            success, modelNode = self.loadModelAsRAS(item["path"], item["nodeName"])

            if not success or modelNode is None:
                self.log("  FAILED: " + item["path"])
                continue

            self.applySurfaceDisplay(modelNode, item)
            loadedNodes.append(modelNode)
            self.log("  loaded: " + item["nodeName"])

        if loadedNodes:
            self.setProgress(100, "Surfaces loaded")
            self.log("Loaded " + str(len(loadedNodes)) + " SimCortex surface model(s).")
            slicer.util.resetSliceViews()
            try:
                slicer.app.layoutManager().threeDWidget(0).threeDView().resetFocalPoint()
            except Exception:
                pass
        else:
            slicer.util.errorDisplay("No SimCortex surfaces could be loaded.")
            self.log("No surfaces were loaded.")

    def loadModelAsRAS(self, filePath, nodeName):
        modelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", nodeName)
        storageNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelStorageNode")
        storageNode.SetFileName(filePath)

        # Slicer stores model coordinates either as RAS or LPS.
        # SimCortex native exports are RAS-mm according to export_manifest.tsv.
        try:
            storageNode.SetCoordinateSystem(slicer.vtkMRMLStorageNode.CoordinateSystemRAS)
        except Exception:
            try:
                storageNode.SetCoordinateSystemToRAS()
            except Exception:
                pass

        success = storageNode.ReadData(modelNode)

        if not success:
            slicer.mrmlScene.RemoveNode(modelNode)
            slicer.mrmlScene.RemoveNode(storageNode)
            return False, None

        modelNode.SetAndObserveStorageNodeID(storageNode.GetID())
        modelNode.CreateDefaultDisplayNodes()
        return True, modelNode

    def applySurfaceDisplay(self, modelNode, item):
        displayNode = modelNode.GetDisplayNode()
        if displayNode is None:
            modelNode.CreateDefaultDisplayNodes()
            displayNode = modelNode.GetDisplayNode()

        if displayNode is None:
            return

        # Basic surface colors:
        # white matter = light gray, pial = warm orange/red.
        if item["surface"] == "white":
            # light blue
            color = (0.55, 0.75, 0.95)
            opacity = 1.0
        else:
            # light red
            color = (0.95, 0.55, 0.55)
            opacity = 0.45

        displayNode.SetColor(color)
        displayNode.SetOpacity(opacity)
        displayNode.SetVisibility(True)
        displayNode.SetSliceIntersectionVisibility(True)
        displayNode.SetBackfaceCulling(False)


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
        if params.get("backendMode") == "Docker":
            ok, message = self.validateDockerParameters(params)
        else:
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

    def getExpectedSurfaceFiles(self, runInfo):
        subject = runInfo["subject"]
        session = runInfo["session"]
        surfaceDir = runInfo["finalSurfaceDir"]
        targetSpace = runInfo.get("targetSpace", "native")

        specs = [
            ("L", "white", "lh_white"),
            ("L", "pial", "lh_pial"),
            ("R", "white", "rh_white"),
            ("R", "pial", "rh_pial"),
        ]

        surfaceFiles = []
        for hemi, surface, shortName in specs:
            filename = (
                f"{subject}_{session}_space-{targetSpace}_desc-deform_"
                f"hemi-{hemi}_{surface}.surf.ply"
            )
            path = os.path.join(surfaceDir, filename)
            nodeName = f"SimCortex_{subject}_{session}_{shortName}_{targetSpace}"

            surfaceFiles.append({
                "path": path,
                "hemi": hemi,
                "surface": surface,
                "shortName": shortName,
                "nodeName": nodeName,
            })

        return surfaceFiles


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
        if params.get("backendMode") == "Docker":
            return self.prepareDockerPipelineRun(params, assets)

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
        targetSpace = "native" if params["exportNative"] else "MNI152"
        commandString = " ".join([params["pythonExecutable"]] + args)

        return {
            "backendMode": "Local Python",
            "program": params["pythonExecutable"],
            "args": args,
            "workingDirectory": params["projectRoot"],
            "commandString": commandString,
            "t1wPath": t1wPath,
            "workRoot": workRoot,
            "subject": subject,
            "session": session,
            "finalSurfaceDir": finalSurfaceDir,
            "targetSpace": targetSpace,
        }

    def prepareDockerPipelineRun(self, params, assets):
        subject = self.normalizeSubject(params["subject"])
        session = self.normalizeSession(params["session"])

        outputRoot = os.path.abspath(params["outputRoot"])
        workRoot = os.path.join(outputRoot, "_work")
        inputRoot = os.path.join(outputRoot, "_slicer_inputs")
        inputDir = os.path.join(inputRoot, subject, session, "anat")
        os.makedirs(inputDir, exist_ok=True)

        t1wPath = os.path.join(inputDir, f"{subject}_{session}_T1w.nii.gz")

        ok = slicer.util.saveNode(params["inputVolume"], t1wPath)
        if not ok:
            raise RuntimeError("Could not save selected input volume as NIfTI: " + t1wPath)

        dockerImage = params["dockerImage"].strip()
        assetsRoot = os.path.abspath(assets["assetsRoot"])

        containerT1wPath = f"/input/{subject}/{session}/anat/{subject}_{session}_T1w.nii.gz"
        containerOutputRoot = "/work"
        containerWorkRoot = "/work/_work"
        containerAssetsRoot = "/assets"

        requestedDevice = params["device"]
        containerDevice = requestedDevice

        dockerArgs = ["run", "--rm"]

        if requestedDevice.startswith("cuda"):
            hostGpuIndex = requestedDevice.split(":")[1] if ":" in requestedDevice else "0"
            dockerArgs.extend(["--gpus", "device=" + hostGpuIndex])
            # Docker exposes the selected host GPU as cuda:0 inside the container.
            containerDevice = "cuda:0"

        dockerArgs.extend(["--shm-size", "8g"])

        try:
            dockerArgs.extend(["--user", f"{os.getuid()}:{os.getgid()}"])
        except Exception:
            pass

        dockerArgs.extend([
            "-e", "HYDRA_FULL_ERROR=1",
            "-w", "/work",
            "-v", inputRoot + ":/input:ro",
            "-v", outputRoot + ":/work",
            "-v", assetsRoot + ":/assets:ro",
            dockerImage,
            "python", "/opt/SimCortex/scripts/run_pipeline.py", "single",
            "--out-root", containerOutputRoot,
            "--work-root", containerWorkRoot,
            "--project-root", "/opt/SimCortex",
            "--mni", os.path.join(containerAssetsRoot, "MNI152_T1_1mm.nii.gz"),
            "--seg-ckpt", os.path.join(containerAssetsRoot, "seg", "seg_best_dice.pt"),
            "--deform-ckpt", os.path.join(containerAssetsRoot, "deform", "deform_best_model.pth"),
            "--device", containerDevice,
            "--space", "MNI152",
            "--transform-type", "Affine",
            "--overwrite",
            "--initsurf-workers", "1",
            "--t1w", containerT1wPath,
            "--subject", subject,
            "--session", session,
        ])

        if params["exportNative"]:
            dockerArgs.append("--export-native")

        finalSurfaceDir = os.path.join(outputRoot, subject, session, "surfaces")
        targetSpace = "native" if params["exportNative"] else "MNI152"

        commandString = "docker " + " ".join(dockerArgs)

        return {
            "backendMode": "Docker",
            "program": "docker",
            "args": dockerArgs,
            "workingDirectory": outputRoot,
            "commandString": commandString,
            "t1wPath": t1wPath,
            "workRoot": workRoot,
            "subject": subject,
            "session": session,
            "finalSurfaceDir": finalSurfaceDir,
            "targetSpace": targetSpace,
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

    def validateDockerParameters(self, params):
        if not params.get("dockerImage", "").strip():
            return False, "Docker image is required."

        if not params.get("assetsRoot", "").strip():
            return False, "Pretrained assets directory is required."

        if not os.path.isdir(params["assetsRoot"]):
            return False, "Pretrained assets directory does not exist:\n" + params["assetsRoot"]

        assets = self.getAssetsPaths(params["assetsRoot"])
        assetsRoot = assets.get("assetsRoot", params["assetsRoot"])

        requiredFiles = [
            ("MNI template", os.path.join(assetsRoot, "MNI152_T1_1mm.nii.gz")),
            ("Segmentation checkpoint", os.path.join(assetsRoot, "seg", "seg_best_dice.pt")),
            ("Deform checkpoint", os.path.join(assetsRoot, "deform", "deform_best_model.pth")),
        ]

        missing = []
        for label, filePath in requiredFiles:
            if not os.path.isfile(filePath):
                missing.append(label + ": " + filePath)

        if missing:
            return (
                False,
                "Missing pretrained asset files:\n"
                + "\n".join(missing)
                + "\n\nSelected assets root:\n"
                + assetsRoot,
            )

        return True, ""

    def runProcessAndCapture(self, program, args, timeoutMs=120000, workingDirectory=None):
        process = qt.QProcess()
        process.setProcessChannelMode(qt.QProcess.SeparateChannels)
        process.setProcessEnvironment(qt.QProcessEnvironment.systemEnvironment())

        if workingDirectory:
            process.setWorkingDirectory(workingDirectory)

        process.start(program, args)

        if not process.waitForStarted(15000):
            return False, "Could not start process:\n" + program

        if not process.waitForFinished(timeoutMs):
            process.kill()
            process.waitForFinished(3000)
            return False, "Process timed out:\n" + program + " " + " ".join(args)

        stdout = self._qByteArrayToString(process.readAllStandardOutput())
        stderr = self._qByteArrayToString(process.readAllStandardError())

        output = ""
        if stdout.strip():
            output += stdout
        if stderr.strip():
            if output:
                output += "\n"
            output += stderr

        if process.exitStatus() != qt.QProcess.NormalExit or process.exitCode() != 0:
            output += "\nExit code: " + str(process.exitCode())
            return False, output

        return True, output

    def validateBasicRunParameters(self, params):
        if params.get("inputVolume") is None:
            return False, "Please select an input T1w volume."

        if not params.get("subject", "").strip():
            return False, "Please enter a subject ID."

        if not params.get("session", "").strip():
            return False, "Please enter a session ID."

        if not params.get("outputRoot", "").strip():
            return False, "Please select an output folder."

        return True, ""

    def assetsAreValid(self, assetsRoot):
        if not assetsRoot or not str(assetsRoot).strip():
            return False

        try:
            assets = self.getAssetsPaths(assetsRoot)
            required = [
                assets["mniTemplate"],
                assets["segCheckpoint"],
                assets["deformCheckpoint"],
            ]
            return all(os.path.isfile(path) for path in required)
        except Exception:
            return False

    def findValidAssetsRoot(self, searchRoot):
        searchRoot = os.path.abspath(os.path.expanduser(searchRoot))
        if self.assetsAreValid(searchRoot):
            return searchRoot

        for root, dirs, files in os.walk(searchRoot):
            if self.assetsAreValid(root):
                return root

        return None

    def downloadPretrainedAssets(self, logCallback=None, progressCallback=None):
        import hashlib
        import urllib.request
        import zipfile

        url = (
            "https://zenodo.org/api/records/20767921/files/"
            "SimCortexV2_pretrained_weights_v0.1.6.zip/content"
        )
        expectedMd5 = "8a512091d39299ab3ec36f8b0013673d"
        filename = "SimCortexV2_pretrained_weights_v0.1.6.zip"

        downloadRoot = os.path.join(
            os.path.expanduser("~"),
            ".slicersimcortex",
            "assets",
        )
        os.makedirs(downloadRoot, exist_ok=True)

        existingAssetsRoot = self.findValidAssetsRoot(downloadRoot)
        if existingAssetsRoot:
            if logCallback:
                logCallback("Pretrained assets already exist in default cache.")
            return existingAssetsRoot

        zipPath = os.path.join(downloadRoot, filename)
        tmpZipPath = zipPath + ".tmp"

        def log(message):
            if logCallback:
                logCallback(message)

        def progress(value, label):
            if progressCallback:
                progressCallback(value, label)

        def md5sum(path):
            h = hashlib.md5()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            return h.hexdigest()

        if not os.path.isfile(zipPath) or md5sum(zipPath) != expectedMd5:
            log("Downloading: " + url)
            progress(40, "Downloading pretrained assets")

            with urllib.request.urlopen(url) as response:
                total = response.headers.get("Content-Length")
                total = int(total) if total else 0
                downloaded = 0

                with open(tmpZipPath, "wb") as out:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        out.write(chunk)
                        downloaded += len(chunk)

                        if total > 0:
                            percent = downloaded / float(total)
                            value = 40 + int(percent * 3)
                            progress(value, "Downloading pretrained assets")

            os.replace(tmpZipPath, zipPath)

        actualMd5 = md5sum(zipPath)
        if actualMd5 != expectedMd5:
            raise RuntimeError(
                "Downloaded pretrained assets failed MD5 check. "
                f"Expected {expectedMd5}, got {actualMd5}."
            )

        log("Pretrained assets archive downloaded and verified.")
        progress(43, "Extracting pretrained assets")

        with zipfile.ZipFile(zipPath, "r") as zf:
            rootAbs = os.path.abspath(downloadRoot)
            for member in zf.namelist():
                target = os.path.abspath(os.path.join(downloadRoot, member))
                if not target.startswith(rootAbs + os.sep) and target != rootAbs:
                    raise RuntimeError("Unsafe path in pretrained assets zip: " + member)
            zf.extractall(downloadRoot)

        assetsRoot = self.findValidAssetsRoot(downloadRoot)
        if not assetsRoot:
            raise RuntimeError(
                "Could not find expected pretrained asset files after extraction."
            )

        return assetsRoot

    def dockerImageExists(self, dockerImage):
        try:
            import subprocess
            result = subprocess.run(
                ["docker", "image", "inspect", dockerImage],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
        except Exception:
            return False

    def validateDockerEnvironment(self, dockerImage, device):
        dockerImage = dockerImage.strip()
        device = device.strip()

        messages = []

        ok, output = self.runProcessAndCapture("docker", ["--version"], timeoutMs=30000)
        messages.append("$ docker --version")
        messages.append(output.strip())
        if not ok:
            messages.append(
                "\nDocker was not found or could not be started. "
                "Install Docker or launch Slicer from an environment where docker is on PATH."
            )
            return False, "\n".join(messages)

        ok, output = self.runProcessAndCapture(
            "docker", ["image", "inspect", dockerImage], timeoutMs=30000
        )
        messages.append("\n$ docker image inspect " + dockerImage)
        if ok:
            messages.append("Docker image found.")
        else:
            messages.append(output.strip())
            messages.append("\nDocker image was not found locally: " + dockerImage)
            return False, "\n".join(messages)

        validationCode = """
import sys
import torch
import monai
import pytorch3d
import ants
import trimesh
import hydra
import simcortex

requested_device = sys.argv[1]

print("Python:", sys.version.replace("\\n", " "))
print("torch:", torch.__version__)
print("monai:", monai.__version__)
print("pytorch3d:", pytorch3d.__version__)
print("ants:", ants.__version__)
print("trimesh:", trimesh.__version__)
print("hydra:", hydra.__version__)
print("Requested device:", requested_device)
print("CUDA available:", torch.cuda.is_available())
print("CUDA device count:", torch.cuda.device_count())

if requested_device.startswith("cuda"):
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested, but torch.cuda.is_available() is False.")
    if torch.cuda.device_count() < 1:
        raise RuntimeError("CUDA was requested, but no CUDA device is visible inside Docker.")
    print("Visible Docker CUDA device 0:", torch.cuda.get_device_name(0))

print("SimCortex Docker backend import OK")
"""

        dockerArgs = ["run", "--rm"]

        if device.startswith("cuda"):
            hostGpuIndex = device.split(":")[1] if ":" in device else "0"
            dockerArgs.extend(["--gpus", "device=" + hostGpuIndex])

        dockerArgs.extend([dockerImage, "python", "-c", validationCode, device])

        ok, output = self.runProcessAndCapture(
            "docker", dockerArgs, timeoutMs=180000, workingDirectory=os.path.expanduser("~")
        )

        messages.append("\n$ docker run validation")
        messages.append(output.strip())

        if not ok:
            return False, "\n".join(messages)

        return True, "\n".join(messages)

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
