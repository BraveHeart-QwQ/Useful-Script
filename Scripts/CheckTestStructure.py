import sys
import os
import json

_DEFAULT_SOURCE_DIR = "src"
_DEFAULT_TEST_DIR = "tests"


def _CheckTestStructure(srcDir=_DEFAULT_SOURCE_DIR, testDir=_DEFAULT_TEST_DIR) -> bool:
    projectDir = os.path.abspath(".")
    with open(os.path.join(projectDir, 'ignore-tests.json')) as file_:
        ignoreList = json.load(file_)['ignoreTest']

    rightStructure = True
    srcDir = os.path.join(projectDir, srcDir)
    testDir = os.path.join(projectDir, testDir)

    print("==========SOURCE==========")
    for root, dirs, files in os.walk(srcDir):
        for file_ in files:
            if (not file_.endswith('.cs')): continue

            filenameWithoutExt = os.path.splitext(file_)[0]
            testFilename = filenameWithoutExt + "Test.cs"
            projectFile = os.path.join(root, file_)
            relaPath = os.path.relpath(projectFile, projectDir)
            relaDir = os.path.relpath(root, srcDir)
            testFile = os.path.join(testDir, relaDir, testFilename)

            if not os.path.exists(testFile) and projectFile not in ignoreList:
                rightStructure = False
                print(f'Missing tests: {relaPath}')

    print("==========TESTS==========")
    for root, dirs, files in os.walk(testDir):
        for file_ in files:
            if (not file_.endswith(".cs")): continue

            testFile = os.path.join(root, file_)
            relaPath = os.path.relpath(testFile, projectDir)
            relaDir = os.path.relpath(root, testDir)

            if (not file_.endswith("Test.cs")):
                print(f"Not test file: {relaPath}")
                continue

            projectFilename = file_[:-7] + ".cs"
            projectFile = os.path.join(srcDir, relaDir, projectFilename)

            if not os.path.exists(projectFile):
                rightStructure = False
                print(f'Redundant test: {relaPath}')

    return rightStructure


def Main():
    argv = sys.argv[1:]
    if (len(argv) == 0):
        _CheckTestStructure()
    elif (len(argv) == 2):
        _CheckTestStructure(argv[0], argv[1])
    else:
        raise ValueError('Invalid number of arguments: {}'.format(len(argv)))


Main()
