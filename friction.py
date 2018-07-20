
import csv
import os

from PyQt5.QtCore import pyqtSlot
from qgis.gui import QgsFileWidget

import utils
import sous_trames
import classes
import params
import abstract_model
import qgsTreatments

# Friction connector is global so that it can be relinked if model is reloaded.
# Model can be reloaded through CSV and project file
frictionConnector = None
frictionModel = None
frictionFields = ["class_descr","class","code"]

# Signal handlers to update sous-trames and classes in frictionModel
@pyqtSlot()
def catchSTAdded(st_item):
    utils.debug("stAdded " + st_item.dict["name"])
    frictionModel.addSTItem(st_item)
    
@pyqtSlot()
def catchSTRemoved(name):
    frictionModel.removeSTFromName(name)
    
@pyqtSlot()
def catchClassAdded(class_item):
    utils.debug("classAdded " + class_item.dict["name"])
    frictionModel.addClassItem(class_item)
    
@pyqtSlot()
def catchClassRemoved(name):
    frictionModel.removeClassFromName(name)

class FrictionRowItem(abstract_model.DictItem):

    def __init__(self,dict):
        super().__init__(dict)
    
    # Adds an entry by sous-trame (columns in table view)
    def addSTCols(self,defaultVal):
        for st in sous_trames.getSTList():
            self.dict[st] = defaultVal
        self.recompute()
            

class FrictionModel(abstract_model.DictModel):

    def __init__(self):
        self.defaultVal = 100
        self.classes = []
        self.sous_trames = []
        self.fields = ["class_descr","class","code"]
        super().__init__(self,self.fields)
        
    def classExists(self,cls_name):
        for fr in self.items:
            if fr.dict["class"] == cls_name:
                return True
        return False
        
    def getRowByClass(self,cls_name):
        for i in self.items:
            if i.dict["class"] == cls_name:
                return i
        return None
        
    def addClassItem(self,cls_item):
        new_row = {"class_descr" : cls_item.dict["descr"],
                   "class" : cls_item.dict["name"],
                   "code" : cls_item.dict["code"]}
        self.addSTCols(new_row)
        row_item = FrictionRowItem(new_row)
        if not self.classExists(cls_item.dict["name"]):
            #self.rows.append(new_row)
            if cls_item not in self.classes:
                self.classes.append(cls_item)
            self.addItem(row_item)
            self.layoutChanged.emit()
        
    def removeClassFromName(self,name):
        self.classes = [cls_item for cls_item in self.classes if cls_item.dict["name"] != name]
        for i in range(0,len(self.items)):
            if self.items[i].dict["class"] == name:
                del self.items[i]
                self.layoutChanged.emit()
                return
        
    def addSTCols(self,row):
        utils.debug("addSTCols")
        for st in sous_trames.getSTList():
            row[st] = self.defaultVal
            
    def addSTItem(self,st_item):
        utils.debug("addSTItem")
        st_name = st_item.dict["name"]
        if st_name not in self.fields:
            # for r in self.rows:
                # r[st_name] = self.defaultVal
            for i in self.items:
                i.dict[st_name] = self.defaultVal
                i.recompute()
            self.fields.append(st_name)
            frictionFields.append(st_name)
            self.sous_trames.append(st_item)
            self.layoutChanged.emit()
        
    def removeSTFromName(self,st_name):
        utils.debug("removeSTFromName " + st_name)
        self.sous_trames = [st_item for st_item in self.sous_trames if st_item.dict["name"] != st_name]
        self.removeField(st_name)
        frictionFields.remove(st_name)
        self.layoutChanged.emit()
        
    def reloadClasses(self):
        utils.debug("reloadClasses")
        classes_to_delete = []
        for item in self.items:
            cls_name = item.dict["class"]
            cls_item = classes.getClassByName(cls_name)
            if not cls_item:
                classes_to_delete.append(cls_name)
                utils.debug("Removing class " + cls_name)
            else:
                utils.debug("Class " + cls_name + " indeed exists")
        self.items = [fr for fr in self.items if fr.dict["class"] not in classes_to_delete]
        self.layoutChanged.emit()
        for cls_item in classes.classModel.items:
            utils.debug("cls_item : " + str(cls_item.dict))
            cls_name = cls_item.dict["name"]
            cls_code = cls_item.dict["code"]
            cls_descr = cls_item.dict["descr"]
            row_item = self.getRowByClass(cls_name)
            if row_item:
                utils.debug("row_item : " + str(row_item.dict))
                utils.debug("Class " + cls_name + " already exists")
                if row_item.dict["code"] != cls_code:
                    utils.debug("Reassigning code '" + str(cls_code) + "' instead of '"
                                + str(row_item.dict["code"]) + " to class " + cls_name)
                    row_item.dict["code"] = cls_code
                    self.layoutChanged.emit()
                if row_item.dict["class_descr"] != cls_descr:
                    utils.debug("Reassigning descr '" + str(cls_descr) + "' instead of '"
                                + str(row_item.dict["class_descr"]) + " to class " + cls_name)
                    row_item.dict["class_descr"] = cls_descr
                    self.layoutChanged.emit()
            else:
                utils.debug("Reloading class " + cls_name)
                self.addClassItem(cls_item)
                self.layoutChanged.emit()
        
    def createRulesFiles(self):
        utils.debug("createRulesFiles")
        for st_item in self.sous_trames:
            st_name = st_item.dict["name"]
            utils.debug("createRulesFiles " + st_name)
            st_rules_fname = st_item.getRulesPath()
            with open(st_rules_fname,"w") as f:
                for i in self.items:
                    in_class = i.dict["code"]
                    out_class = i.dict[st_name]
                    f.write(str(in_class) + " = " + str(out_class) + "\n")
                
    def applyReclassProcessing(self):
        utils.debug("applyReclass")
        self.createRulesFiles()
        for st_item in self.sous_trames:
            st_name = st_item.dict["name"]
            utils.debug("applyReclass " + st_name)
            st_rules_fname = st_item.getRulesPath()
            utils.checkFileExists(st_rules_fname)
            st_merged_fname = st_item.getMergedPath()
            utils.checkFileExists(st_merged_fname)
            st_friction_fname = st_item.getFrictionPath()
            qgsTreatments.applyReclassProcessing(st_merged_fname,st_friction_fname,st_rules_fname,st_name)
        
    def applyReclassGdal(self):
        utils.debug("friction.applyReclassGdal")
        for st_item in self.sous_trames:
            st_merged_fname = st_item.getMergedPath()
            utils.checkFileExists(st_merged_fname)
            st_friction_fname = st_item.getFrictionPath()
            if os.path.isfile(st_friction_fname):
                os.remove(st_friction_fname)
                aux_name = st_friction_fname + ".aux.xml"
                if os.path.isfile(aux_name):
                    os.remove(aux_name)
            reclass_dict = {}
            for r in self.items:
                st_name = st_item.dict["name"]
                class_code = r.dict['code']
                coeff = r.dict[st_name]
                if not utils.is_integer(coeff):
                    class_name = r.dict['class']
                    utils.user_error("Friction coefficient for class " + class_name
                                     + " and st " + st_name 
                                     + " is not an integer : '" + str(coeff) + "'")
                reclass_dict[r.dict['code']] = r.dict[st_item.dict["name"]]
            utils.debug("Reclass dict : " + str(reclass_dict))
            #utils.debug("applyReclassGdal")
            qgsTreatments.applyReclassGdalFromDict(st_merged_fname,st_friction_fname,reclass_dict)
        
    def applyItems(self):
        #self.applyReclass()
        utils.debug("applyItems")
        self.applyReclassGdal()
        
    def saveCSV(self,fname):
        with open(fname,"w", newline='') as f:
            writer = csv.DictWriter(f,fieldnames=self.fields,delimiter=';')
            writer.writeheader()
            for i in self.items:
                utils.debug("writing row " + str(i.dict))
                writer.writerow(i.dict)
                
    @classmethod
    def fromCSV(cls,fname):
        model = cls()
        model.classes = classes.classModel.items
        with open(fname,"r") as f:
            reader = csv.DictReader(f,fieldnames=frictionFields,delimiter=';')
            header = reader.fieldnames
            model.fields = header
            model.sous_trames = []
            for st in header[3:]:
                st_item = sous_trames.getSTByName(st)
                if not st_item:
                    utils.debug(str(frictionFields))
                    utils.debug(str(st))
                    utils.user_error("Sous-trame '" + st + "' does not exist")
                model.sous_trames.append(st_item)
            first_line = next(reader)
            for row in reader:
                item = FrictionRowItem(row)
                model.addItem(item)
        return model
    
        
    def fromXMLRoot(self,root):
        #model = cls()
        eraseFlag = True
        if eraseFlag:
            self.classes = classes.classModel.items
            self.sous_trames = sous_trames.stModel.items
            self.items = []
        for fr in root:
            item = FrictionRowItem(fr.attrib)
            self.addItem(item)
        self.layoutChanged.emit()
        #return model
           
class FrictionConnector(abstract_model.AbstractConnector):
    
    def __init__(self,dlg):
        global frictionModel
        self.dlg = dlg
        frictionModel = FrictionModel()
        super().__init__(frictionModel,self.dlg.frictionView,None,None)
        
    def initGui(self):
        self.dlg.frictionCsvFile.setStorageMode(QgsFileWidget.SaveFile)
        self.dlg.frictionCsvFile.setFilter("*.csv")
        self.dlg.frictionLoadFile.setStorageMode(QgsFileWidget.GetFile)
        self.dlg.frictionLoadFile.setFilter("*.csv")
        
    @pyqtSlot()
    def internCatchGroupAdded(grp):
        utils.debug("groupAdded2 " + grp)
        
    def printCatch(self):
        utils.debug("frictionRun catched")
        
    def connectComponents(self):
        sous_trames.stModel.stAdded.connect(catchSTAdded)
        sous_trames.stModel.stRemoved.connect(catchSTRemoved)
        classes.classModel.classAdded.connect(catchClassAdded)
        classes.classModel.classRemoved.connect(catchClassRemoved)
        super().connectComponents()
        self.dlg.frictionLoadClass.clicked.connect(self.model.reloadClasses)
        self.dlg.frictionRun.clicked.connect(self.model.applyItems)
        #self.dlg.frictionRun.clicked.connect(self.printCatch)
        # self.dlg.frictionSave.clicked.connect(self.saveCSV)
        # self.dlg.frictionLoad.clicked.connect(self.loadCSV)
        self.dlg.frictionCsvFile.fileChanged.connect(self.saveCSV)
        self.dlg.frictionLoadFile.fileChanged.connect(self.loadCSV)
        #sous_trames.stModel.groupAdded.connect(self.internCatchGroupAdded)
        
    def loadCSV(self,fname):
        global frictionModel, frictionFields
        #fname = self.dlg.frictionLoadFile.filePath()
        utils.checkFileExists(fname)
        new_model = self.model.fromCSV(fname)
        self.model = new_model
        frictionModel = new_model
        frictionFields = new_model.fields
        #self.view.setModel(self.model)
        self.connectComponents()
        self.model.layoutChanged.emit()
        frictionModel.layoutChanged.emit()
        
    def saveCSV(self,fname):
        #fname = self.dlg.frictionCsvFile.filePath()
        self.model.saveCSV(fname)
     
            
