# -*- coding: utf-8 -*-
"""
/***************************************************************************
 EcologicalContinuityDialog
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
#from .groups_model import GroupModelTest, GroupItem
from .metagroups import Metagroups
import params
import sous_trames
import groups
#from .groups import Groups, classModel
#from .vector_selection import VectorSelections
from .selection import SelectionConnector
from .fusion import FusionConnector
import friction
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
        
    def initTabs(self):
        global classModel
        #metagroupConnector = Metagroups(self)
        #groupConnector = groups.GroupConnector(self,metagroupConnector.model)
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
        costConnector = CostConnector(self)
        #bufferConnector = BufferConnector(self,groupConnector.model)
        #rasterizationConnector = RasterizationConnector(self)
        self.tabs = [paramsConnector,
                     stConnector,
                     groupsConnector,
                     classConnector,
                     selectionConnector,
                     fusionConnector,
                     frictionConnector,
                     costConnector]
                     #bufferConnector,
                     #rasterizationConnector]
        self.models = {"ParamsModel" : paramsConnector.model,
                        "STModel" : stConnector.model,
                        "GroupModel" : groupsConnector.model,
                        "ClassModel" : classConnector.model,
                        "SelectionModel" : selectionConnector.model,
                        "FusionModel" : fusionConnector.model,
                        "FrictionModel" : frictionConnector.model,
                        "CostModel" : costConnector.model}
        
        
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
        for tab in self.tabs:
            tab.initGui()
        self.groupsTab.hide()
        self.treatmentsFrame.hide()
        
    def connectComponents(self):
        for tab in self.tabs:
            tab.connectComponents()
        #self.buttonAddGroup.clicked.connect(self.addGroup)
        #self.groupVectMapLayer.layerChanged.connect(self.updateGroupVectLayer)
        #self.groupVectRun.clicked.connect(self.selectEntities)
        #self.runButton.clicked.connect(self.runCost)
        # Main tab connectors
        self.saveModelButton.clicked.connect(self.saveModel)
        self.loadModelButton.clicked.connect(self.loadModel)
        self.saveModelPath.setStorageMode(QgsFileWidget.SaveFile)
        self.loadModelPath.setStorageMode(QgsFileWidget.GetFile)
        
    def onResize(self,event):
        new_size = event.size()
        
        
    # def runCost(self):
        # debug("Start runCost")
        # startRaster = self.rasterDepartComboBox.currentLayer()
        # permRaster = self.rasterPermComboBox.currentLayer()
        # dateNow = datetime.datetime.now()
        # debug ("startRaster = " + startRaster.name())
        # parameters = { 'input' : permRaster,
                        # 'start_raster' : startRaster,
                        # 'max_cost' : 5000,
                        # 'output' : 'D:\MChailloux\PNRHL_QGIS\tmpLayer_output.tif',
                        #'start_coordinates' : '0,0',
                        #'stop_coordinates' : '0,0',
                        # 'nearest' : 'D:\MChailloux\PNRHL_QGIS\tmpLayer_nearest.tif',
                        # 'outdir' : 'D:\MChailloux\PNRHL_QGIS\tmpLayer_movements.tif',
                        # 'start_points' :  None,
                        # 'stop_points' : None,
                        # 'null_cost' : None,
                        # 'memory' : 5000,
                        # 'GRASS_REGION_CELLSIZE_PARAMETER' : 50,
                        # 'GRASS_SNAP_TOLERANCE_PARAMETER' : -1,
                        # 'GRASS_MIN_AREA_PARAMETER' : 0,
                        # '-k' : False,
                        # '-n' : False,
                        # '-r' : True,
                        # '-i' : False,
                        # '-b' : False}
        #parameters = {}
        # try:
            # processing.run("grass7:r.cost",parameters)
            # print ("call to r.cost successful")
        # except Exception as e:
            # print ("Failed to call r.cost : " + str(e))
            # raise e
        # finally:  
            # debug("End runCost")
        #grass.run_command(start_raster=startRaster,input=permRaster,max_cost=?,output=?,memory=5000)
        
    def addGroup(self):
        self.groupTable.insertRow(0)
        
    def updateGroupVectLayer(self,layer):
        self.groupVectFieldExpr.setLayer(layer)
        
    def selectEntities(self):
        debug("Start selectEntities")
        layer = self.groupVectMapLayer.currentLayer()
        fieldExpr = self.groupVectFieldExpr.expression()
        group = self.groupVectGroup.currentText()
        selection = layer.getFeatures(QgsFeatureRequest().setFilterExpression(fieldExpr))
        newLayer=QgsVectorLayer("Polygon?crs=epsg:2154", "Segment buffers", "memory")
        writeShapefile(layer,'D:\MChailloux\PNRHL_QGIS\\test.shp')
        debug("End selectEntities")
        
    def toXML(self):
        xmlStr = "<ModelConfig>\n"
        for k, m in self.models.items():
            xmlStr += m.toXML() + "\n"
        xmlStr += "</ModelConfig>\n"
        debug("Final xml : \n" + xmlStr)
        return xmlStr

    def saveModel(self):
        fname = self.saveModelPath.filePath()
        checkFileExists(fname)
        xmlStr = self.toXML()
        writeFile(fname,xmlStr)
        
    def loadModel(self):
        modelPath = self.loadModelPath.filePath()
        checkFileExists(modelPath)
        setConfigModels(self.models)
        parseConfig(modelPath)