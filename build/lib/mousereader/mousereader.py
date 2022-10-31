# -*- coding: utf-8 -*-
import numpy as np
import re
import os
from subprocess import call
from shutil import copyfile
import datetime
import codecs
import io
import traceback

def readERF(erfFile, dataType, MUIDs, ignore=False):
    dataTables = []
    with codecs.open(erfFile, encoding="windows-1252") as f:
        erfTxt = f.read().split("\n")

    lines = [i for i, a in enumerate(erfTxt) if dataType in a]
    erfTxtFilter = erfTxt[lines[0]:lines[1]]
    endSectLines = [i for i, a in enumerate(erfTxtFilter) if "EndSect" in a]

    geometryDataLines = [i for i, a in enumerate(erfTxtFilter) if "Geometry_data" in a]

    for MUID in MUIDs:
        try:
            MUIDLine = [a for a in geometryDataLines if MUID in erfTxtFilter[a]][0]
        except Exception as e:
            if dataType == "MaxLevel_Ranked":
                raise (Exception("Could not find %s in ERFfile. \n%s\n%s" % (MUID, e.message, erfTxtFilter)))
            elif dataType == "MaxFlow_Ranked":
                if not ignore:
                    raise (Exception("Could not find %s in ERFfile. Try Project Check Tool.\n" % (MUID)))
                else:
                    # arcpy.AddWarning("Could not find %s in ERFfile. Try Project Check Tool.\n" % (MUID))
                    dataTables.append(None)
                    continue
            else:
                raise (Exception("Could not find %s in ERFfile.\n" % (MUID)))
        endSectLine = [a for a in endSectLines if MUIDLine < a][0]

        dataTable = {}
        removePaddedSpaces = re.compile("^ *(.+)")
        for line in erfTxtFilter[MUIDLine + 1:endSectLine]:
            data = line.split(",")
            for col in range(len(data)):
                variable = removePaddedSpaces.findall(data[col])[0]
                try:
                    variable = float(variable)
                except:
                    pass
                if "col%d" % col not in dataTable:
                    dataTable["col%d" % col] = [variable]
                else:
                    dataTable["col%d" % col].append(variable)

        if dataType == "Total_Discharge_Yearly_Chronological":
            yearFilter = re.compile(r"Qyear = (\d+)")
            dataTable["Year"] = [int(yearFilter.findall(a)[0]) for a in dataTable.pop("col0")]
            dataTable["Events"] = dataTable.pop("col1")
            dataTable["Duration"] = dataTable.pop("col2")
            dataTable["Volume"] = dataTable.pop("col3")
        dataTables.append(dataTable)
    if len(MUIDs) == 1:
        dataTables = dataTable
    return dataTables


def readPRF(filename, MUIDs=[""], datatype=""):
    """Reads MOUSE PRF Files.
        filename: PRF file path.
        MUID: MUID of object.
        datatype: Link_Q, Node_WL, Link_WL, Link_V"""

    if not type(MUIDs) == list and not type(MUIDs) == tuple:
        MUIDs = [MUIDs]

    for year in reversed(range(2010, 2025)):
        if os.path.exists(r"C:\Program Files (x86)\DHI\%d\bin\m11extra.exe" % (year)):
            break

    m11extraPath = r"C:\Program Files (x86)\DHI\%d\bin\m11extra.exe" % (year)
    prfFile = filename

    m11Out = os.path.dirname(prfFile) + "\M11.OUT"
    call([m11extraPath, prfFile])

    with open(m11Out, 'r') as M11OUTFile:
        txt = M11OUTFile.read()
    # matches = re.findall(r"%s: +<([^>]+)>" % (datatype),txt)

    lines = ""
    MUIDs_order = []
    with open(m11Out, 'r') as M11OUTFile:
        for linei, line in enumerate(M11OUTFile):
            try:
                for MUID_i, MUID in enumerate(MUIDs):
                    if len(re.findall("%s: +<%s>" % (datatype, MUID), line)) > 0:
                        line = re.sub("^0", "1", line)
                        MUIDs_order.append(MUID_i)
                lines += line
            except Exception as e:
                raise (e)
    with open(m11Out.replace(".OUT", ".IN"), 'w') as M11INFile:
        M11INFile.write(lines)

    csvFile = "%s.csv" % MUID
    os.chdir(os.path.dirname(prfFile))
    call([m11extraPath, prfFile, csvFile, "/NOHEADER"])

    with open(csvFile, 'r') as csvFileRead:
        csvTxt = csvFileRead.read()
    try:
        os.remove(csvFile)
        os.remove("M11.IN")
        os.remove("M11.OUT")
    except:
        pass

    return csvTxt, list(np.array(MUIDs)[MUIDs_order])


class MouseResult:
    def __init__(self, filename, MUIDs=[""], datatype=""):
        """Reads MOUSE PRF Files.
                filename: PRF file path.
                MUID: MUID of object.
                datatype: Link_Q, Node_WL, Link_WL, Link_V"""
        self.MUIDs = MUIDs
        self.filename = filename
        if not type(MUIDs) == list and not type(MUIDs) == tuple:
            MUIDs = [MUIDs]

        for year in reversed(range(2010, 2025)):
            if os.path.exists(r"C:\Program Files (x86)\DHI\%d\bin\m11extra.exe" % (year)):
                break

        m11extraPath = r"C:\Program Files (x86)\DHI\%d\bin\m11extra.exe" % (year)
        prfFile = filename

        m11Out = os.path.dirname(prfFile) + "\M11.OUT"
        call([m11extraPath, prfFile])

        # with io.open(m11Out, 'r', encoding = "cp1252") as M11OUTFile:
        #     txt = unicode(M11OUTFile.read())
        # matches = re.findall(r"%s: +<([^>]+)>" % (datatype),txt)

        lines = u""
        self.MUIDs_order = []
        replace_first_digit = re.compile("^0")
        get_muid = re.compile("<([^>]+)>")
        if MUIDs == ["ALL"]:
            with open(m11Out, 'r') as M11OUTFile:
                i = 0
                for linei, line in enumerate(M11OUTFile):
                    line_uni = unicode(line, encoding='cp1252')
                    if datatype in line_uni:
                        line_uni = replace_first_digit.sub("1", line_uni)
                        self.MUIDs_order.append(i)
                        MUID = get_muid.findall(line)[0]
                        self.MUIDs.append(MUID)
                        i += 1
                    lines += line_uni
        else:
            with open(m11Out, 'r') as M11OUTFile:
                for linei, line in enumerate(M11OUTFile):
                    line_uni = unicode(line, encoding = 'cp1252')
                    for MUID_i, MUID in enumerate(MUIDs):
                        if "<%s>" % MUID in line_uni and datatype in line_uni:
                            line_uni = re.sub("^0", "1", line_uni)
                            self.MUIDs_order.append(MUID_i)
                    lines += line_uni

        with io.open(m11Out.replace(".OUT", ".IN"), 'w', encoding = 'cp1252') as M11INFile:
            M11INFile.write(lines)

        csv_file = "%s.csv" % MUID
        os.chdir(os.path.dirname(prfFile))
        call([m11extraPath, prfFile, csv_file, "/NOHEADER"])

        with open(csv_file, 'r') as csv_file_read:
            self.csv_txt = csv_file_read.read()
        try:
            import pandas as pd
            self.dataframe = pd.read_csv(csv_file, sep=" {2,}", index_col=0, engine='python')
            self.dataframe.index = pd.to_datetime(self.dataframe.index)
        except Exception as e:
            import warnings
            warnings.warn("Pandas not installed")
        try:
            os.remove(csv_file)
            os.remove("M11.IN")
            os.remove("M11.OUT")
        except:
            pass

    def query(self, MUID):
        return self.dataframe.values[:, [self.MUIDs_order[i] for i, ID in enumerate(self.MUIDs) if ID == MUID][0]]


def readMJL(filename, job=-1):
    with open(filename, 'r') as f:
        ltsFileTxt = f.read()

    getSimStart = re.compile(r"Simulation_start = '([^']+)'")
    getSimEnd = re.compile(r"Simulation_end = '([^']+)'")

    simStart = getSimStart.findall(ltsFileTxt)
    simEnd = getSimEnd.findall(ltsFileTxt)
    for i in range(len(simStart)):
        simStart[i] = datetime.datetime.strptime(
            simStart[i],
            "%Y-%m-%d %H:%M:%S")
        simEnd[i] = datetime.datetime.strptime(
            simEnd[i],
            "%Y-%m-%d %H:%M:%S")
    if job != -1:
        simStart = simStart[job - 1]
        simEnd = simEnd[job - 1]
    return [simStart, simEnd]


if __name__ == "__main__":
    files = [r"C:\Users\ELNN\OneDrive - Ramboll\Documents\MOL\MOL_055Base.PRF"]

    import matplotlib.pyplot as plt

    # plt.figure()
    for file in files:
        MUIDs = ['4949F40P1', '0151S01', '0151S02', '0151S03', '0151S04', '0151S05', '0202F10', '0202F13', '0202F18',
                 'FORSLAG05', '0202F22', '0202F23', '0202F24', '0202F25', '0202F26', '0202F27', '0202F29', '0202F30',
                 'FORSLAG36_fiktiv', 'FORSLAG36', 'FORSLAG35_fiktiv', 'SEMI50', '0277R05', '0277R03', 'SEMI55',
                 'SEMI60', 'SEMI65', 'SEMI70', 'SEMI80', 'SEMI85', 'SEMI90', 'SEMI75', '0277S03', '0500P05', '0500P09',
                 '0500P13', '0500P17', '0530F01', '0530F02', '0530F03', '0530F04', '0530F05', '0530F07', '0530F09',
                 '0530F11', '0530F13', '0530F17', '0530F21', '0530F25', '0631F17', '0631F21', '0631F25', '0631F29',
                 '0631F33', '0631F37', '0631R00', '0631R04', '0631R08', '0631R12', '0631S01', '0631S01G', '0631S05',
                 '0631S05G', '0631S09', '0631S13', '0640F18', '0640F22', '0640F26', '0640F28', '0640G01', '0640M05',
                 '0640M09', '0640M13', '0640M17', '0640M21', '0640M25', '0640M29', '0640M33', '0656F06', '0656F08',
                 '0656F35', '0656F36', '0656F38', '0656F39', '0656F40', '0656F42', '0656F43', '0656F44', '0656F46',
                 '0656F49', '0656F51', '0656F55', '0656F59', '0656F63', '0656F67', '0656F71', '0656F73', '0909F01',
                 '0909F03', '0909F05']
        mouse_result = MouseResult(file, MUIDs, "Node_WL")
    val = mouse_result.query('0151S01')
    # plt.step(mouse_result.dataframe.index, mouse_result.dataframe.values, label = file)
    # plt.legend()
    # plt.show()
    print("break")