# test classification

import unittest

from irrexplorer import utils


class TestClassification(unittest.TestCase):

    def test_classification(self):

        a = utils.classifySearchString('10.0.0.1')
        self.assertEquals(type(a), utils.Prefix)

        a = utils.classifySearchString('1.3.4.0/24')
        self.assertEquals(type(a), utils.Prefix)

        a = utils.classifySearchString('AS2603')
        self.assertEquals(type(a), utils.ASNumber)

        a = utils.classifySearchString('AS-NTT')
        self.assertEquals(type(a), utils.ASMacro)

        a = utils.classifySearchString('AS-57344')
        self.assertEquals(type(a), utils.ASMacro)

        a = utils.classifySearchString('AS9498:AS-BHARTI-IN')
        self.assertEquals(type(a), utils.ASMacro)




def main():
    unittest.main()


if __name__ == '__main__':
    main()

