# -*- coding: utf-8 -*-
"""
import sys
import time
import enum
import os
import json
import git

# TEST LIST
# - [x] Test file just created
# - [x] Test file newer, comment don't exists
# - [x] Test file newer, comment exists
# - [x] Test file older, comment don't exists
# - [x] Test file older, not confirm
# - [x] Test file older, confirm
# - [x] comment exists but no @test
# - [x] comment has other elements
# - [x] not git project

FIX_LENGTH = 24

CONFIRM = "CONFIRM"
OUTDATED = "OUTDATED"

_PROGRAM = None


class TestComments(object):
    def __init__(self, filePath: str) -> None:
        self._filePath = filePath
        self._exists = False
        self._confirmed = False

        self._testCommentIndex = -1
        self._currComments = [] # ("comment-type", "comment-text")

        self._InitComments()

    def _InitComments(self) -> None:
        with open(self._filePath, "r") as file:
            lineIndex = 0
            for line in file:
                if (lineIndex == 0 and not line.startswith("/**")):
                    return
                self._exists = True
                if (line.startswith("/**")):
                    self._currComments.append(("header", line))
                elif ("@test" in line):
                    self._currComments.append(("test", line))
                    self._testCommentIndex = lineIndex
                    if (CONFIRM in line or OUTDATED in line):
                        self._confirmed = CONFIRM in line
                    else:
                        _PROGRAM.AddLog("Test", "E", "Invalid state of test", self._filePath)
                elif ("*/" in line):
                    self._currComments.append(("footer", line))
                    break
                else:
                    self._currComments.append(("other", line))
                lineIndex += 1

    @property
    def exists(self) -> bool:
        return self._exists

    @property
    def testStateExists(self) -> bool:
        return self._testCommentIndex >= 0

    @property
    def confirmed(self) -> bool:
        return self._confirmed

    def SetComments(self, confirm: bool) -> bool:
        """
        :return: modified
        """
        if (self.exists and self.confirmed == confirm): return False

        currState = OUTDATED if confirm else CONFIRM
        destState = CONFIRM if confirm else OUTDATED

        # Get Comment Content
        commentContent = ""
        if (self.exists):
            if (self.testStateExists):
                self._currComments[self._testCommentIndex] = (
                    "test",
                    self._currComments[self._testCommentIndex][1].replace(currState, destState)
                )
            else:
                self._currComments.insert(1, ("test", f" * @test\t: {destState}\n"))
            commentContent = "".join((commentData[1] for commentData in self._currComments)) + "\n"
        else:
            commentContent = self._GenerateNewComments(destState)

        # Get Main Content
        mainContent = ""
        with open(self._filePath, "r") as file:
            if (self.exists): # skip beginning comments
                for i in range(len(self._currComments)):
                    file.readline()
            mainContent = file.read()

        with open(self._filePath, "w") as file:
            file.write(commentContent)
            file.write(mainContent)

        self._exists = True
        self._confirmed = confirm
        return True

    # ---------------- Utils ---------------- #

    @staticmethod
    def _GenerateNewComments(state: str) -> str:
        header = "/**-------------------------------------------------- *"
        test = " * @test\t: {}".format(state)
        footer = " * -------------------------------------------------- */"
        return f"{header}\n{test}\n{footer}\n"


class Program(object):

    # ---------------- Life ---------------- #

    def __init__(self) -> None:
        global _PROGRAM

        # Config
        self.testFileSuffix = "Test"
        self.projectDir = "."
        self.targetDirList = ["src"]
        self.testDir = "tests"
        self.ignoreFileList = []
        self.ignoreFolderList_InTest = ["obj", "bin"]
        # Runtime
        self.checkState = 0 # 0:OK, 1:WARNING, 2:MODIFIED
        self._repo = None
        self._logs = {}

        self._Init()

        _PROGRAM = self

    def _Init(self):
        with open(os.path.join(self.projectDir, "check-test.json")) as file:
            checkTestConfig = json.load(file)
            self.testFileSuffix = checkTestConfig.get("self.testFileSuffix", self.testFileSuffix)
            self.targetDirList = checkTestConfig.get("targetFolders", self.targetDirList)
            self.testDir = checkTestConfig.get("testFolder", self.testDir)
            self.ignoreFileList = checkTestConfig.get("ignoreTestFiles", self.ignoreFileList)
            self.ignoreFolderList_InTest = checkTestConfig.get(
                "ignoreFoldersInTest", self.ignoreFolderList_InTest
            )

        markList = []
        for i in range(0, len(self.ignoreFileList)):
            if (not os.path.exists(self.ignoreFileList[i])):
                print("! Invalid Config - ignoreTestFiles: {}".format(self.ignoreFileList[i]))
                markList.insert(0, i)
        for i in markList:
            self.ignoreFileList.pop(i)

        # git repo
        try:
            self._repo = git.Repo(".")
        except git.exc.InvalidGitRepositoryError as e:
            print("! Not a git project, unable to get file's real modified time.")
            self._repo = None

    # ---------------- Main ---------------- #

    @staticmethod
    def Main():
        program = Program()
        program._CheckTestStructure()

        if (program.HasLog("Target")):
            print("\n================Target================")
            program.PrintLog("Target")
        if (program.HasLog("Test")):
            print("\n=================Test=================")
            program.PrintLog("Test")

        return program.checkState

    def _CheckTestStructure(self) -> int:
        # Check Target Dir
        for targetDir in self.targetDirList:
            for root, dirs, files in os.walk(targetDir):
                for file_ in files:
                    filePath = os.path.join(root, file_)
                    if (not self._NeedCheck(filePath)): continue
                    if (self._HasTestFile(filePath)):
                        self.checkState = max(self.checkState, self._CheckExistingTest(filePath))
                    else:
                        self.checkState = max(self.checkState, 1)
                        self.AddLog("Target", "W", "Lack of test", filePath)

        # Check Test Dir
        for targetDir in self.targetDirList:
            for root, dirs, files in os.walk(os.path.join(self.testDir, targetDir)):
                for file_ in files:
                    filePath = os.path.join(root, file_)
                    if (not self._NeedCheckTest(filePath)): continue
                    if (not self._HasTargetFile(filePath)):
                        self.checkState = max(self.checkState, 1)
                        self.AddLog("Test", "W", "Redundant test", filePath)

    def _CheckExistingTest(self, targetFilePath: str) -> int:
        testFilePath = self._GetTestFilePath(targetFilePath).replace(os.sep, "/")
        comment = TestComments(testFilePath)

        # LMT = Last Modified Time
        targetFileLMT = os.path.getmtime(targetFilePath)
        testFileLMT = os.path.getmtime(testFilePath)

        if (self._repo):
            if (not self._repo.git.diff("HEAD", targetFilePath)):
                targetLastCommit = next(self._repo.iter_commits(paths=targetFilePath, max_count=1))
                targetFileLMT = targetLastCommit.committed_date
            if (not self._repo.git.diff("HEAD", testFilePath)):
                testLastCommit = next(self._repo.iter_commits(paths=testFilePath, max_count=1))
                testFileLMT = testLastCommit.committed_date

        if (targetFileLMT > testFileLMT):
            if (not comment.exists):
                comment.SetComments(confirm=False)
                self.AddLog("Test", "M", "Outdated test. Create comment for", testFilePath)
                return 2
            elif (comment.confirmed):
                comment.SetComments(confirm=False)
                self.AddLog("Test", "M", "Outdated test", testFilePath)
                return 2
            else:
                self.AddLog("Test", "W", "Outdated test", testFilePath)
                return 1
        else:
            if (not comment.exists or not comment.testStateExists):
                comment.SetComments(confirm=True)
                self.AddLog("Test", "M", "Create comment for", testFilePath)
                return 2
            elif (not comment.confirmed):
                self.AddLog("Test", "W", "Unconfirmed test", testFilePath)
                return 1
        return 0

    # ---------------- Log ---------------- #

    def AddLog(self, class_: str, level: str, content: str, filePath: str):
        if (level not in ["W", "E", "M"]):
            print("[ERROR] Invalid log level: {}".format(level))
            return
        level = "!" if level == "W" else "*" if level == "E" else "+"
        if (class_ not in self._logs):
            self._logs[class_] = []
        self._logs[class_].append(
            "{} {}: {}".format(level, content.ljust(FIX_LENGTH), filePath.replace(os.sep, '/'))
        )

    def HasLog(self, class_: str) -> bool:
        return class_ in self._logs

    def PrintLog(self, class_: str):
        if (class_ not in self._logs):
            print("No log for {}".format(class_))
            return
        for log in self._logs[class_]:
            print(log)

    # ---------------- Utils ---------------- #

    def _NeedCheck(self, targetFilePath: str) -> bool:
        if (not targetFilePath.endswith(".cs")): return False
        for ignoreFile in self.ignoreFileList:
            if (os.path.samefile(ignoreFile, targetFilePath)): return False
        return True

    def _NeedCheckTest(self, testFilePath: str) -> bool:
        if (not testFilePath.endswith(self.testFileSuffix + ".cs")): return False
        for ignoreDir in self.ignoreFolderList_InTest:
            if (testFilePath.startswith(os.path.join(self.testDir, ignoreDir))):
                return False
        return True

    def _GetTestFilePath(self, targetFilePath: str) -> str:
        # NOTE Here it is assumed that filePath ends with .cs
        tempPath = "".join([targetFilePath[:-3], self.testFileSuffix, ".cs"])
        return os.path.join(self.testDir, tempPath)

    def _GetTargetFilePath(self, testFilePath: str) -> str:
        # NOTE Here it is assumed that filePath ends with Test.cs
        tempPath = "".join([testFilePath[:-(len(self.testFileSuffix) + 3)], ".cs"])
        return os.path.relpath(tempPath, self.testDir)

    def _HasTestFile(self, targetFilePath: str) -> bool:
        testFilePath = self._GetTestFilePath(targetFilePath)
        return os.path.exists(testFilePath)

    def _HasTargetFile(self, testFilePath: str) -> bool:
        targetFilePath = self._GetTargetFilePath(testFilePath)
        return os.path.exists(targetFilePath)


sys.exit(Program.Main())
