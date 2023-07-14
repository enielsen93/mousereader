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
    import warnings
    for MUID in MUIDs:
        geometry_MUID = "'%s'" % MUID if not "'" in MUID else MUID
        # MUIDLine = [a for a in geometryDataLines if geometry_MUID in erfTxtFilter[a]][0]
        try:
            MUIDLine = [a for a in geometryDataLines if geometry_MUID in erfTxtFilter[a]][0]
        except Exception as e:
            if dataType == "MaxLevel_Ranked":
                warnings.warn(("Could not find %s in ERFfile. \n%s\n%s" % (MUID, e.message, erfTxtFilter)))
            elif dataType == "MaxFlow_Ranked":
                    warnings.warn(Exception("Could not find %s in ERFfile. Try Project Check Tool.\n" % (MUID+1)))
            else:
                warnings.warn(("Could not find %s in ERFfile.\n" % (MUID)))
                # raise (Exception("Could not find %s in ERFfile.\n" % (MUID)))
            MUIDLine = None

        if MUIDLine is None:
            dataTables.append(None)
        else:
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
        if self.MUIDs == ["ALL"]:
            self.MUIDs = []
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
                        if "<%s>" % MUID in line_uni and datatype in line_uni and not MUID_i in self.MUIDs_order:
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
            pass
            # os.remove(csv_file)
            # os.remove("M11.IN")
            # os.remove("M11.OUT")
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
    files = [r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Lisbjerg\Model\LIS_011\LIS_011_5177_2000-09-13Base.PRF"]

    import matplotlib.pyplot as plt

    readERF(u'C:\\Users\\ELNN\\OneDrive - Ramboll\\Documents\\Aarhus Vand\\Lisbjerg\\Model\\LIS_011\\LIS_011_5177_1979_2018Base_Samlet.erf',
        'Total_Discharge_Ranked',
        ["'Bassin_Boliggade_8', 'Node_293'", u"'R829', 'R829_1'", u"'Bassin_Boldbane', 'C43C704R'",
         u"'R832', 'R832_1'", u"'B830', 'CU41'", u"'R829', 'B829_Overl\xf8b1'", u"'Node_183', 'Node_293'",
         u"'C42671Z', 'B787'", u"'C42331R', 'B787'", u"'C42687Z', 'B787'", u"'C42681R', 'B787'", u"'C42381R', '0'",
         u"'C42381Z', '0'", u"'C42091R', 'B787'", u"'C42382R', '0'", u"'C49109R', 'Node_343'", u"'C49109B', 'Node_343'",
         u"'C42383R', '0'", u"'R830', 'B830_Overl\xf8b1'", u"'Bassin_B01b', 'Groeft_10_3-3'", u"'C43240R', 'Node_343'",
         u"'C43241R', 'Node_343'", u"'R830', 'R830_1'", u"'C42410R', 'B787'", u"'C42400R', 'B787'", u"'B828_1', 'B828'",
         u"'Bassin_B10', 'Bassin_Blaaplads'", u"'C42721R', 'B787'", u"'C42720R', 'B787'", u"'C42711Z', 'B787'",
         u"'C42710R', 'B787'", u"'C42642R', 'B787'", u"'C42641R', 'B787'", u"'C42640R', 'B787'", u"'C42420R', 'B787'",
         u"'Node_186', 'Node_294'", u"'B858', 'B859'", u"'Node_188', 'Node_294'", u"'C42700R', 'B787'",
         u"'C42701R', 'B787'", u"'C42691Z', 'B787'", u"'C42690R', 'B787'", u"'C42702R', 'B787'", u"'C42705Z', 'B787'",
         u"'C42707Z', 'B787'", u"'C42296R', 'Node_345'", u"'Node_349', 'Node_234'", u"'C48093R', 'Node_349'",
         u"'C42685Z', 'B787'", u"'Node_212', 'Node_345'", u"'C42298R', 'Node_236'", u"'C42297R', 'Node_345'",
         u"'R828', 'B828_Overl\xf8b1'", u"'Bassin_B04', 'Groeft_11-1'", u"'Bassin_B05', 'Node_332'",
         u"'Bassin_B06', 'Node_334'", u"'C42723R', 'B787'", u"'Bassin_B01', 'Groeft_10_3-2'",
         u"'Bassin_B03', 'Node_145'", u"'Node_221', '0'", u"'Node_230', '0'", u"'Node_163', 'Node_299'",
         u"'Bygaden137', 'Node_298'", u"'C42430R', 'B787'", u"'Bassin_B09', 'Node_143'", u"'C42441R', 'B787'",
         u"'Bassin_Lisbjerg_Parkvej', 'B786'", u"'NREP_node_09', 'NREP_node_10'", u"'NREP_node_11', 'NREP_node_12'",
         u"'NREP_node_06', 'NREP_node_05'", u"'NREP_node_07', 'NREP_node_08'", u"'NREP_node_01', 'NREP_node_02'",
         u"'NREP_node_04', 'NREP_node_03'", u"'C42501R', 'Bassin_Lisbjerg_Parkvej'", u"'B828', 'Node_219'",
         u"'Bassin_*1', 'Groeft_10_3-2'", u"'B859', 'CU46_1'", u"'B786', 'C42300R'", u"'Bygaden122', 'Node_297'",
         u"'Bygaden125', 'Node_295'", u"'Bygaden129', 'Node_296'", u"'C42280R', 'B830'", u"'Node_175', 'B858'",
         u"'C42290R', 'Node_236'", u"'Node_172', 'Node_305'", u"'C42683R', 'B787'",
         u"'Node_288', 'Bassin_LisbjergBuen'", u"'B859', 'C43C593R'", u"'Node_294', 'Node_376'",
         u"'Node_63', 'Node_64'", u"'NREP_node_16', 'NREP_node_15'", u"'NREP_node_14', 'NREP_node_13'",
         u"'C48091R', 'Node_343'", u"'C48092R', 'Node_343'", u"'C42273R', 'Node_345'", u"'C42682R', 'B787'",
         u"'B829', 'CU46_3'", u"'Node_212', 'Node_213'", u"'C43C453R', '0'", u"'Node_217', 'Node_345'",
         u"'Node_211', 'Node_345'", u"'Bassin_Boliggade_3', 'Node_274'", u"'Bassin_Boliggade_2', 'Node_286'",
         u"'Bassin_Boliggade_5', 'NREP_node_02'", u"'Bassin_Boliggade_4', 'Node_326'",
         u"'Bassin_ford1', 'NREP_node_01'", u"'Bassin_Boliggade_6', 'NREP_node_01'", u"'B832', '0'",
         u"'Node_185', 'Node_293'", u"'Bassin_ford3', 'Node_288'", u"'Node_187', 'Node_294'", u"'Node_190', 'Node_376'",
         u"'Node_191', 'Node_376'", u"'Node_169', 'Node_302'", u"'Node_168', 'Node_301'", u"'Node_171', 'Node_304'",
         u"'Node_170', 'Node_303'", u"'R779', 'C42020R'", u"'R786', 'Node_130'", u"'B787', 'Bassin_Lisbjerg_Parkvej'",
         u"'C43260R', 'Node_343'", u"'C42500R', 'Bassin_Lisbjerg_Parkvej'", u"'C43250R', 'Node_343'",
         u"'Klimabassin_4', 'Node_376'", u"'Bassin_Boliggade4b', 'Node_339'", u"'Bygaden125', 'Node_289'",
         u"'Bassin_ford10', 'Klimabassin_R2'", u"'Node_143', 'Bassin_Blaaplads'", u"'Bassin_ford8_9', '0'",
         u"'Node_331', 'Node_338'", u"'Bygaden122', 'Node_289'", u"'Bygaden129', 'Node_289'",
         u"'Node_69', 'Groeft_01-3-r\xf8r'", u"'Bassin_ford8_8', '0'", u"'C43C640R', 'B858'", u"'C43C641R', 'B858'",
         u"'CU41', 'Node_345'", u"'Bassin_Blaaplads', 'Bassin_Boldbane'", u"'B828_1', 'C43220R'",
         u"'Bassin_BX4', 'Node_376'", u"'Bassin_BX5', 'Bassin_Lisbjerg_Parkvej'", u"'Bassin_BX2', 'Node_293'",
         u"'Bassin_BX3', 'B858'", u"'Bygaden61', 'Node_290'", u"'Bygaden198', 'Node_308'", u"'Bygaden262', 'Node_308'",
         u"'C42026R', 'Node_308'", u"'Klimabassin_R1', 'Klimabassin_R2'", u"'R828', 'R828_1'", u"'C42027R', 'Node_308'",
         u"'C43190R', 'Node_343'", u"'C49108R', 'Node_343'", u"'C42722R', 'B787'",
         u"'Bassin_Ringgaarden', 'Klimabassin_R2'", u"'Bassin_B07', 'Groeft_11-3'", u"'Bassin_B19a', '0'",
         u"'Bassin_ford8_7', '0'", u"'Bassin_ford8_6', '0'", u"'Bassin_B17a', '0'", u"'R832', 'R832_1'",
         u"'Bassin_ford8_4', '0'", u"'Bassin_ford8_3', '0'", u"'Bassin_B15', '0'", u"'C49104R', 'Node_345'",
         u"'C49111R', 'Node_234'", u"'C48095R', 'Node_234'", u"'C49105R', 'Node_345'",
         u"'C42490R', 'Bassin_Lisbjerg_Parkvej'", u"'C42480R', 'Bassin_Lisbjerg_Parkvej'",
         u"'Bassin_ford5', 'Node_284'", u"'C4250ZR', 'Bassin_Lisbjerg_Parkvej'", u"'C49106R', 'Node_343'",
         u"'C49107R', 'Node_343'", u"'B788', 'Bassin_Lisbjerg_Parkvej'", u"'Bassin_ford6', 'Node_273'",
         u"'B858', 'C43C620R'", u"'Bassin_ford7', 'Node_280'", u"'Bassin_ford4', 'Node_335'",
         u"'Bassin_Fremtidigt_areal', 'Bassin_Boldbane'", u"'C42440R', 'B787'", u"'Bassin_B14', '0'",
         u"'Bassin_B11a', '0'", u"'Bassin_B16a', '0'", u"'Bassin_CH', '0'", u"'0000001', 'Fiktiv_overloeb'",
         u"'Bassin_ford8_10', '0'", u"'B779', 'B830'", u"'Bassin_ford2', 'Node_281'",
         u"'Bassin_NREP_3', 'Groeft_01-4-r\xf8r'", u"'Bassin_NREP_2', 'NREP_node_11'",
         u"'Bassin_NREP_1', 'NREP_node_01'", u"'Bassin_AL2bolig', 'Bassin_Blaaplads'", u"'Node_311', '0'",
         u"'Node_310', '0'", u"'Bassin_B11b', '0'", u"'Bassin_B08', 'C43C453R'", u"'Bassin_B12a', '0'",
         u"'Bassin_ford8_2', '0'", u"'Bassin_ford8_1', '0'", u"'Bassin_B12b', '0'", u"'C43002R', 'Node_338'",
         u"'Bassin_B02_1', 'Node_317'", u"'Bassin_B02_2', 'Node_323'", u"'Klimabassin_R2', 'Node_376'",
         u"'Bassin_B19b', '0'", u"'Bassin_B22', '0'", u"'Bassin_B23', '0'", u"'Bassin_B20', '0'",
         u"'Bassin_VK111', '0'", u"'Bassin_VK113', '0'", u"'Bassin_VK112', '0'", u"'Bassin_B06_1', 'Node_319'",
         u"'Bassin_B16b', '0'", u"'Bassin_B17b', '0'"])

    # plt.figure()
    # MUIDs = ['Link_Bassin_B12', 'Link_423', 'Link_424', 'Link_425', 'Link_Bassin_*2', 'Link_Bassin_B14', 'Link_Bassin_B11', 'Link_Bassin_B11a', 'Link_Bassin_ford8']
    # mouse_result_links = MouseResult(files[0], MUIDs, "Link_Q")
    # # for MUID in MUIDs:
    # #     val = mouse_result.query(MUID)
    # plt.step(mouse_result_links.dataframe.index, np.sum(mouse_result_links.dataframe.values,axis=1)*1e3, color = 'b', label=u"Regulerede afløb")
    #
    # weirs = ['Weir_304', 'Weir_332', 'Weir_303', 'Weir_299', 'Weir_293', 'Weir_333', 'Weir_295', 'Weir_296', 'Weir_297']
    # mouse_result_weirs = MouseResult(files[0], weirs, "Weir_Q")
    # # for MUID in weirs:
    # # val = mouse_result.query(MUID)
    # plt.step(mouse_result_weirs.dataframe.index, np.sum(mouse_result_weirs.dataframe.values,axis=1)*1e3, color = 'k', label=u"Overløb")
    # # dataTables = readERF(r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Lisbjerg\Model\LIS_011\LIS_011_5177_1979_2018Base_Samlet.erf", "MaxLevel_Ranked", ['B828'])
    # plt.legend()
    # plt.ylabel(u"Vandføring [L/s]")
    # plt.tight_layout()
    # plt.show()
    # import scipy.integrate
    # import matplotlib.dates
    # plt.figure()
    # plt.step(mouse_result_links.dataframe.index[1:], scipy.integrate.cumtrapz(np.sum(mouse_result_links.dataframe.values, axis=1), [matplotlib.dates.date2num(date)*24*60*60 for date in mouse_result_links.dataframe.index]), label=u"Regulerede afløb",)
    # plt.step(mouse_result_weirs.dataframe.index[1:],
    #               scipy.integrate.cumtrapz(np.sum(mouse_result_weirs.dataframe.values, axis=1),
    #                                        [matplotlib.dates.date2num(date) * 24 * 60 * 60 for date in
    #                                         mouse_result_weirs.dataframe.index]), label=u"Overløb")
    # plt.ylabel(u"Akkumuleret vandføring [m³]")
    # plt.legend()
    # plt.tight_layout()
    #
    # plt.show()
    # print("break")