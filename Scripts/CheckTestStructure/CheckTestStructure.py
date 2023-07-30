import sys
import os
import json

TEST_FILE_SUFFIX = "Test"
PROJECT_DIR = "."
TARGET_DIR_LIST = ["src"]
TEST_DIR = "tests"
IGNORE_FILE = []
IGNORE_FOLDER_IN_TEST_DIR = ["obj", "bin"]


def _Init():
    global TEST_FILE_SUFFIX, TARGET_DIR_LIST, TEST_DIR, IGNORE_FILE, IGNORE_FOLDER_IN_TEST_DIR
    with open(os.path.join(PROJECT_DIR, "check-test.json")) as file_:
        checkTestConfig = json.load(file_)
        TEST_FILE_SUFFIX = checkTestConfig.get("testFileSuffix", TEST_FILE_SUFFIX)
        TARGET_DIR_LIST = checkTestConfig.get("targetFolders", TARGET_DIR_LIST)
        TEST_DIR = checkTestConfig.get("testFolder", TEST_DIR)
        IGNORE_FILE = checkTestConfig.get("ignoreTestFiles", IGNORE_FILE)
        IGNORE_FOLDER_IN_TEST_DIR = checkTestConfig.get(
            "ignoreFoldersInTest", IGNORE_FOLDER_IN_TEST_DIR
        )


def _NeedCheck(filePath: str) -> bool:
    if (not filePath.endswith(".cs")): return False
    for ignoreFile in IGNORE_FILE:
        if (os.path.samefile(ignoreFile, filePath)): return False
    return True


def _NeedCheckTest(filePath: str) -> bool:
    if (not filePath.endswith(TEST_FILE_SUFFIX + ".cs")): return False
    for ignoreDir in IGNORE_FOLDER_IN_TEST_DIR:
        if (filePath.startswith(os.path.join(TEST_DIR, ignoreDir))):
            return False
    return True


def _HasTestFile(filePath: str) -> bool:
    tempPath = "".join([filePath[:-3], TEST_FILE_SUFFIX, ".cs"]) # NOTE Here assumed that filePath ends with .cs
    testFilePath = os.path.join(TEST_DIR, tempPath)
    return os.path.exists(testFilePath)


def _HasTargetFile(filePath: str) -> bool:
    tempPath = "".join([filePath[:-7], ".cs"]) # NOTE Here assumed that filePath ends with .cs
    targetFilePath = os.path.relpath(tempPath, TEST_DIR)
    return os.path.exists(targetFilePath)


def _CheckTestStructure() -> bool:
    print("==========TARGETS==========")
    for targetDir in TARGET_DIR_LIST:
        for root, dirs, files in os.walk(targetDir):
            for file_ in files:
                filePath = os.path.join(root, file_)
                if (not _NeedCheck(filePath)): continue
                if (not _HasTestFile(filePath)):
                    print(f"Lack of test: {filePath.replace(os.sep, '/')}")

    print("==========TESTS==========")
    for targetDir in TARGET_DIR_LIST:
        for root, dirs, files in os.walk(os.path.join(TEST_DIR, targetDir)):
            for file_ in files:
                filePath = os.path.join(root, file_)
                if (not _NeedCheckTest(filePath)): continue
                if (not _HasTargetFile(filePath)):
                    print(f"Redundant test: {filePath.replace(os.sep, '/')}")


def Main():
    _Init()
    _CheckTestStructure()


Main()
