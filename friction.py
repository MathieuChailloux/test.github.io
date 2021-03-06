# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BioDispersal
                                 A QGIS plugin
 Computes ecological continuities based on environments permeability
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2018-04-12
        git sha              : $Format:%H$
        copyright            : (C) 2018 by IRSTEA
        email                : mathieu.chailloux@irstea.fr
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import csv
import os

from PyQt5.QtCore import pyqtSlot, QModelIndex
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QFileDialog
from qgis.gui import QgsFileWidget

import utils
import qgsUtils
import progress
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

# Signal handlers to update subnetworks and classes in frictionModel
@pyqtSlot()
def catchSTAdded(st_item):
    utils.debug("stAdded " + st_item.dict["name"])
    utils.debug("ST addItem50, items = " + str(sous_trames.stModel))
    frictionModel.addSTItem(st_item)
    utils.debug("ST addItem5, items = " + str(sous_trames.stModel))
    
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
        self.defaultVal = None
        self.classes = []
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
            if cls_item not in self.classes:
                self.classes.append(cls_item)
            self.addItem(row_item)
            self.layoutChanged.emit()
        
    def removeClassFromName(self,name):
        utils.debug("removeing class " + str(name) + " from friction")
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
        global friction_fields
        utils.debug("addSTItem")
        st_name = st_item.dict["name"]
        utils.debug("ST addItem51, items = " + str(sous_trames.stModel))
        if st_name not in self.fields:
            for i in self.items:
                if st_name not in i.dict:
                    i.dict[st_name] = self.defaultVal
                    i.recompute()
            self.fields.append(st_name)
            frictionFields.append(st_name)
            self.layoutChanged.emit()
        
    def removeSTFromName(self,st_name):
        utils.debug("removeSTFromName " + str(st_name))
        self.removeField(st_name)
        if st_name in frictionFields:
            frictionFields.remove(st_name)
        self.layoutChanged.emit()

    #def reloadST(self):
        
    def reloadClasses(self):
        utils.debug("reloadClasses")
        classes_to_delete = []
        for item in self.items:
            cls_name = item.dict["class"]
            cls_item = classes.getClassByName(cls_name)
            if not cls_item:
                classes_to_delete.append(cls_name)
                utils.debug("Removing class " + str(cls_name))
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
                utils.debug("Class " + str(cls_name) + " already exists")
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
        for st_item in sous_trames.stModel.items:
            st_name = st_item.dict["name"]
            utils.debug("createRulesFiles " + str(st_name))
            st_rules_fname = st_item.getRulesPath()
            with open(st_rules_fname,"w") as f:
                for i in self.items:
                    in_class = i.dict["code"]
                    out_class = i.dict[st_name]
                    f.write(str(in_class) + " = " + str(out_class) + "\n")
                
    def applyReclassProcessing(self):
        utils.debug("applyReclass")
        self.createRulesFiles()
        for st_item in sous_trames.stModel.items:
            st_name = st_item.dict["name"]
            utils.debug("applyReclass " + str(st_name))
            st_rules_fname = st_item.getRulesPath()
            utils.checkFileExists(st_rules_fname)
            st_merged_fname = st_item.getMergedPath()
            utils.checkFileExists(st_merged_fname)
            st_friction_fname = st_item.getFrictionPath()
            qgsTreatments.applyReclassProcessing(st_merged_fname,st_friction_fname,st_rules_fname,st_name)
        
    def applyReclassGdal(self,indexes):
        utils.debug("friction.applyReclassGdal")
        utils.debug("indexes = " + str(indexes))
        st_list = sous_trames.stModel.items
        nb_steps = len(st_list)
        progress_section = progress.ProgressSection("Friction",nb_steps)
        progress_section.start_section()
        #for st_item in self.sous_trames:
        for st_item in st_list:
            st_merged_fname = st_item.getMergedPath()
            utils.checkFileExists(st_merged_fname)
            st_friction_fname = st_item.getFrictionPath()
            utils.debug("st_friction_fname = " + str(st_friction_fname))
            qgsUtils.removeRaster(st_friction_fname)
            reclass_dict = {}
            for r in self.items:
                st_name = st_item.dict["name"]
                class_code = r.dict['code']
                if st_name not in r.dict:
                    utils.internal_error("Could not find sous-trame '" + str(st_name)
                                         + "' in friction model " + str(r.dict.keys()))
                coeff = r.dict[st_name]
                if not utils.is_integer(coeff):
                    class_name = r.dict['class']
                    utils.warn("Friction coefficient for class " + class_name
                                     + " and st " + str(st_name)
                                     + " is not an integer : '" + str(coeff) + "'")
                else:
                    reclass_dict[r.dict['code']] = r.dict[st_item.dict["name"]]
            utils.debug("Reclass dict : " + str(reclass_dict))
            #utils.debug("applyReclassGdal")
            qgsTreatments.applyReclassGdalFromDict(st_merged_fname,st_friction_fname,
                                                   reclass_dict,load_flag=True)
            progress_section.next_step()
        progress_section.end_section()
        
    def applyItems(self,indexes):
        #self.applyReclass()
        utils.debug("applyItems")
        params.checkInit()
        self.applyReclassGdal(indexes)
        
    def saveCSV(self,fname):
        with open(fname,"w", newline='') as f:
            writer = csv.DictWriter(f,fieldnames=self.fields,delimiter=';')
            writer.writeheader()
            for i in self.items:
                utils.debug("writing row " + str(i.dict))
                writer.writerow(i.dict)
        utils.info("Friction saved to file '" + str(fname) + "'")
                
    @classmethod
    def fromCSV(cls,fname):
        model = cls()
        model.classes = classes.classModel.items
        with open(fname,"r") as f:
            reader = csv.DictReader(f,fieldnames=frictionFields,delimiter=';')
            header = reader.fieldnames
            model.fields = header
            #model.sous_trames = []
            for st in header[3:]:
                st_item = sous_trames.getSTByName(st)
                if not st_item:
                    utils.debug(str(frictionFields))
                    utils.debug(str(st))
                    utils.user_error("Sous-trame '" + st + "' does not exist")
                #model.sous_trames.append(st_item)
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
            #self.sous_trames = sous_trames.stModel.items
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
        pass
    
    @pyqtSlot()
    def internCatchClassAdded(self):
        utils.debug("internClassAdded " )
        
    def connectComponents(self):
        sous_trames.stModel.stAdded.connect(catchSTAdded)
        sous_trames.stModel.stRemoved.connect(catchSTRemoved)
        classes.classModel.classAdded.connect(catchClassAdded)
        classes.classModel.classRemoved.connect(catchClassRemoved)
        super().connectComponents()
        self.dlg.frictionLoadClass.clicked.connect(self.model.reloadClasses)
        self.dlg.frictionRun.clicked.connect(self.applyItems)
        #classes.classModel.classAdded2.connect(self.internCatchClassAdded)
        self.dlg.frictionSave.clicked.connect(self.saveCSVAction)
        self.dlg.frictionLoad.clicked.connect(self.loadCSVAction)
        
    def getSelectedIndexes(self):
        if self.onlySelection:
            indexes = list(set([i.column() for i in self.view.selectedIndexes()]))
        else:
            indexes = range(3,len(self.model.fields))
        return indexes
        
    # def applyItems(self):
        # indexes = self.getSelectedIndexes()
        # utils.debug("applyItems to indexes " + str(indexes))
        # self.model.applyItems(indexes)
        
    def loadCSV(self,fname):
        global frictionModel, frictionFields
        utils.checkFileExists(fname)
        new_model = self.model.fromCSV(fname)
        self.model.items = new_model.items
        self.model.fields = new_model.fields
        frictionModel = self.model
        frictionFields = self.model.fields
        # self.model = new_model
        # frictionModel = new_model
        # frictionFields = new_model.fields
        # utils.debug("frictionFields = " + str(new_model.fields))
        #self.connectComponents()
        #self.model.layoutChanged.emit()
        frictionModel.layoutChanged.emit()
        utils.info("Friction loaded from '" + str(fname))
        
    def loadCSVAction(self):
        utils.debug("loadCSVAction " + str(self))
        fname = params.openFileDialog(parent=self.dlg,
                                      msg="Ouvrir le tableau de friction",
                                      filter="*.csv")
        if fname:
            self.loadCSV(fname)
        
    def saveCSV(self,fname):
        self.model.saveCSV(fname)
     
    def saveCSVAction(self):
        utils.debug("saveCSVAction")
        fname = params.saveFileDialog(parent=self.dlg,
                                      msg="Sauvegarder le tableau de friction sous",
                                      filter="*.csv")
        if fname:
            self.saveCSV(fname)
        
