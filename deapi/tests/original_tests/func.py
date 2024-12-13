import sys
import unittest
import time
from prettytable import PrettyTable


def compare2Value(val1, val2, name):
    if not val1 == val2:
        print(f"{name}: expect {val1} actual {val2}")
        return False
    else:
        return True


def compare2FloatValue(expectVal, actualVal, numPrecision, name):
    if not round(expectVal, numPrecision) == round(actualVal, numPrecision):
        print(
            f"{name}: expect {round(expectVal, numPrecision)} actual {round(actualVal, numPrecision)}"
        )
        return False


def writeLogFile(caseName, scriptName):
    logFilePath = (
        "C:\\direct_electron\\de_sdk\\trunk\\Python\\unitTests\\testResults.log"
    )

    if scriptName == "01_fps.py":
        writeMode = "w"
    else:
        writeMode = "a"

    # Open the log file in write mode
    with open(logFilePath, writeMode) as logFile:

        logFile.write(f"Date: {time.strftime('%m/%d/%Y %H:%M:%S')}\n")
        logFile.write(f"Script Name: {scriptName}\n")
        # Redirect stdout to log file
        sys.stdout = logFile

        # Run the test suite with custom result class
        suite = unittest.TestLoader().loadTestsFromTestCase(caseName)
        runner = unittest.TextTestRunner(resultclass=TestResultWithTable)
        result = runner.run(suite)
        result.printResultsTable()

        logFile.write(
            "-----------------------------------------------------------------\n"
        )


# collect results and print them as a table
class TestResultWithTable(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.results = []

    def addSuccess(self, test):
        self.results.append((test._testMethodName, "PASS"))
        super().addSuccess(test)

    def addFailure(self, test, err):
        self.results.append((test._testMethodName, "FAIL"))
        super().addFailure(test, err)

    def addError(self, test, err):
        self.results.append((test._testMethodName, "ERROR"))
        super().addError(test, err)

    def printResultsTable(self):
        table = PrettyTable()
        table.field_names = ["Test Case", "Result"]
        for result in self.results:
            table.add_row(result)
        print("\nTest Results Summary:")
        print(table)
