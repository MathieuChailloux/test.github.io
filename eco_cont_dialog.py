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

import os
import sys

from PyQt5 import uic
from PyQt5 import QtWidgets
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import processing
from qgis.core import *
from qgis.gui import *
from qgis.gui import QgsFileWidget

from .utils import *
from .qgsUtils import *
import params
import sous_trames
import groups
from .selection import SelectionConnector
from .fusion import FusionConnector
import friction
from .ponderation import PonderationConnector
from .cost import CostConnector
from .config_parsing import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'eco_cont_dialog_base.ui'))
    
class EcologicalContinuityDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(EcologicalContinuityDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        #metagroupConnector = Metagroups(self)
        #self.groupConnector = Groups(self,metagroupConnector.metaclassModel)
        #rasterizationConnector = Rasterization(self)
        #self.tabs=[Groups(self),
        #            Metagroups(self),
        #            VectorSelections(self),
        #            Rasterization(self)]
        #self.tabs = [self.groupConnector,metagroupConnector,rasterizationConnector]
        self.setupUi(self)
        #self.connectComponents()
        
    # Initialize plugin tabs.
    # One tab <=> one connector.
    def initTabs(self):
        paramsConnector = params.ParamsConnector(self)
        params.params = paramsConnector.model
        stConnector = sous_trames.STConnector(self)
        sous_trames.stModel = stConnector.model
        groupsConnector = groups.GroupConnector(self)
        groups.groupsModel = groupsConnector.model
        classConnector = classes.ClassConnector(self)
        classes.classModel = classConnector.model
        selectionConnector = SelectionConnector(self)
        fusionConnector = FusionConnector(self)
        frictionConnector = friction.FrictionConnector(self)
        friction.frictionModel = frictionConnector.model
        ponderationConnector = PonderationConnector(self)
        costConnector = CostConnector(self)
        self.connectors = {"Params" : paramsConnector,
                           "ST" : stConnector,
                           "Group" : groupsConnector,
                           "Class" : classConnector,
                           "Selection" : selectionConnector,
                           "Fusion" : fusionConnector,
                           "Friction" : frictionConnector,
                           "Ponderation" : ponderationConnector,
                           "Cost" : costConnector}
        self.recomputeModels()
        
    # Initialize Graphic elements for each tab
    # TODO : resize
    def initGui(self):
        self.geometry = self.geometry()
        self.x = self.x()
        self.y = self.y()
        self.width = self.width()
        self.height = self.height()
        step_x = self.width * 0.1
        step_y = self.height * 0.1
        new_w = self.width * 0.8
        new_h = self.height * 0.8
        #self.tabWidget.setGeometry(self.x + step_x, self.y + step_y, new_w, new_h)
        for k, tab in self.connectors.items():
            tab.initGui()
        
    # Connect view and model components for each tab
    def connectComponents(self):
        for k, tab in self.connectors.items():
            tab.connectComponents()
        # Main tab connectors
        self.saveModelPath.fileChanged.connect(self.saveModelAs)
        self.saveProjectButton.clicked.connect(self.saveModel)
        self.loadModelPath.fileChanged.connect(self.loadModel)
        self.saveModelPath.setStorageMode(QgsFileWidget.SaveFile)
        self.loadModelPath.setStorageMode(QgsFileWidget.GetFile)
        
    def onResize(self,event):
        new_size = event.size()
        
    # Recompute self.models in case they have been reloaded
    def recomputeModels(self):
        self.models = {"ParamsModel" : params.params,
                        "STModel" : sous_trames.stModel,
                        "GroupModel" : groups.groupsModel,
                        "ClassModel" : classes.classModel,
                        "SelectionModel" : self.connectors["Selection"].model,
                        "FusionModel" : self.connectors["Fusion"].model,
                        "FrictionModel" : friction.frictionModel,
                        "CostModel" : self.connectors["Cost"].model}
        
    # Return XML string describing project
    def toXML(self):
        xmlStr = "<ModelConfig>\n"
        for k, m in self.models.items():
            xmlStr += m.toXML() + "\n"
        xmlStr += "</ModelConfig>\n"
        debug("Final xml : \n" + xmlStr)
        return xmlStr

    # Save project to 'fname'
    def saveModelAs(self,fname):
        self.recomputeModels()
        xmlStr = self.toXML()
        params.params.projectFile = fname
        writeFile(fname,xmlStr)
        
    # Save project to projectFile if existing
    def saveModel(self):
        fname = params.params.projectFile
        checkFileExists(fname,"Project ")
        self.saveModelAs(fname)
        
    # Load project from 'fname' if existing
    def loadModel(self,fname):
        debug("loadModel")
        checkFileExists(fname)
        setConfigModels(self.models)
        params.params.projectFile = fname
        parseConfig(fname)