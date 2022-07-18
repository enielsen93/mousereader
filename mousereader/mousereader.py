# -*- coding: utf-8 -*-
import numpy as np
import re
import os
from subprocess import call
from shutil import copyfile
import datetime
import codecs

def readERF(erfFile,dataType,MUIDs, ignore = False):
    dataTables = []
    with codecs.open(erfFile,encoding="windows-1252") as f:
            erfTxt = f.read().split("\n")
            
    lines = [i for i,a in enumerate(erfTxt) if dataType in a]
    erfTxtFilter = erfTxt[lines[0]:lines[1]]
    endSectLines = [i for i,a in enumerate(erfTxtFilter) if "EndSect" in a]

    geometryDataLines = [i for i,a in enumerate(erfTxtFilter) if "Geometry_data" in a]
    
    for MUID in MUIDs:
        try:
            MUIDLine = [a for a in geometryDataLines if MUID in erfTxtFilter[a]][0]
        except Exception as e:
            if dataType == "MaxLevel_Ranked":
                raise(Exception("Could not find %s in ERFfile. \n%s\n%s" % (MUID,e.message,erfTxtFilter)))
            elif dataType == "MaxFlow_Ranked":
                if not ignore:
                    raise(Exception("Could not find %s in ERFfile. Try Project Check Tool.\n" % (MUID)))
                else:
                    #arcpy.AddWarning("Could not find %s in ERFfile. Try Project Check Tool.\n" % (MUID))
                    dataTables.append(None)
                    continue
            else:
                raise(Exception("Could not find %s in ERFfile.\n" % (MUID)))
        endSectLine = [a for a in endSectLines if MUIDLine<a][0]
        
        dataTable = {}
        removePaddedSpaces = re.compile("^ *(.+)")
        for line in erfTxtFilter[MUIDLine+1:endSectLine]:
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

def readPRF(filename, MUIDs = [""], datatype = ""): 
    """Reads MOUSE PRF Files.
        filename: PRF file path.
        MUID: MUID of object.
        datatype: Link_Q, Node_WL, Link_WL, Link_V"""
    
    if not type(MUIDs) == list and not type(MUIDs) == tuple:
        MUIDs = [MUIDs]
    
    for year in reversed(range(2010,2025)):
        if os.path.exists(r"C:\Program Files (x86)\DHI\%d\bin\m11extra.exe" % (year)):
            break
            
    m11extraPath = r"C:\Program Files (x86)\DHI\%d\bin\m11extra.exe" % (year)
    prfFile = filename
    
    m11Out = os.path.dirname(prfFile) + "\M11.OUT"
    call([m11extraPath, prfFile])
    
    with open(m11Out,'r') as M11OUTFile:
        txt = M11OUTFile.read()
    # matches = re.findall(r"%s: +<([^>]+)>" % (datatype),txt)
    
    lines = ""
    MUIDs_order = []
    with open(m11Out,'r') as M11OUTFile:
        for linei,line in enumerate(M11OUTFile):
            try:
                for MUID_i, MUID in enumerate(MUIDs):
                    if len(re.findall("%s: +<%s>" % (datatype, MUID),line))>0:
                        line = re.sub("^0","1",line)
                        MUIDs_order.append(MUID_i)
                lines += line
            except Exception as e:
                raise(e)
    with open(m11Out.replace(".OUT",".IN"),'w') as M11INFile:
        M11INFile.write(lines)
        
    csvFile = "%s.csv" % MUID
    os.chdir(os.path.dirname(prfFile))
    call([m11extraPath, prfFile, csvFile, "/NOHEADER"])
    
    with open(csvFile,'r') as csvFileRead:
        csvTxt = csvFileRead.read()
    try:
        os.remove(csvFile)
        os.remove("M11.IN")
        os.remove("M11.OUT")
    except:
        pass

    return csvTxt, list(np.array(MUIDs)[MUIDs_order])

class MouseResult:
    def __init__(self, filename, MUIDs = [""], datatype = ""):
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

        csv_file = "%s.csv" % MUID
        os.chdir(os.path.dirname(prfFile))
        call([m11extraPath, prfFile, csv_file, "/NOHEADER"])

        with open(csv_file, 'r') as csv_file_read:
            self.csv_txt = csv_file_read.read()
        try:
            import pandas as pd
            self.dataframe = pd.read_csv(csv_file, sep=" {2,}", index_col = 0, engine = 'python')
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

def readMJL(filename, job = -1):
    with open(filename,'r') as f:
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
        simStart = simStart[job-1]
        simEnd = simEnd[job-1]
    return [simStart,simEnd]

if __name__ == "__main__":
    files = ["C:\Offline\VOR_Status\VOR_Status_CDS100_CDS100.CRF",
            "C:\Offline\VOR_Status\VOR_Status_CDS20_CDS20.CRF",
            "C:\Offline\VOR_Status\VOR_Status_CDS5_CDS5.CRF",
            "C:\Offline\VOR_Status\VOR_Status_CDS10_CDS10.CRF"]

    import matplotlib.pyplot as plt

    plt.figure()
    for file in files:
        mouse_result = MouseResult(file, r"Vinkel")
        plt.step(mouse_result.dataframe.index, mouse_result.dataframe.values, label = file)
    plt.legend()
    plt.show()
    print("break")