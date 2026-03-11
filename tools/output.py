import logging
import os
import string
import sys
import time


class create():
    curPath = os.path.abspath(os.path.dirname(__file__))
    rootPath = os.path.split(curPath)[0]
    sys.path.append(rootPath)
    nowDate = time.strftime("%Y_%m_%d")
    nowTime = time.strftime("%H_%M_%S")

    def createTestcases(self, path: string = "edubox"):
        testcases = self.rootPath + r'/testcases/' + path

        return testcases

if __name__ == '__main__':
    pass
