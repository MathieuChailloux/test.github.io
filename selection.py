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
from qgis.core import QgsMapLayerProxyModel, QgsCoordinateTransform, QgsProject, QgsGeometry
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QHeaderView
from .abstract_model import AbstractGroupModel, AbstractGroupItem, DictItem, DictModel, AbstractConnector
from .utils import *
from .qgsUtils import *
import params
import classes
import groups
from .qgsTreatments import *
import progress
from osgeo import gdal
import numpy as np

selection_fields = ["in_layer","mode","mode_val","group"]


# near_str = QtCore.QCoreApplication.translate("Plus proche voisin")
# average_str = QtCore.QCoreApplication.translate("Moyenne")

# resampling_assoc = {near_str : "near",
                    # average_str : "average"}
resampling_assoc = {"Plus proche voisin" : "near",
                    "Moyenne" : "average"}
resampling_modes = ["near","average"]
                    
vfield = "VField"
vexpr = "VExpr"
rclasses = "RClasses"
rresample = "RResample"

# SelectionItem implements DictItem and contains below fields :
#   - 'in_layer' : input layer from which features are selected
#   - 'expr' : expression on which selection is performerd
#                (all features are selected if empty expression)
#   - 'class' : class assigned to selection item
#   - 'group' : group assigned to selection item
class SelectionItem(DictItem):

    def __init__(self,in_layer,mode,mode_val,group):#,class_descr="",group_descr="",code=None):
        dict = {"in_layer" : in_layer,
                "mode" : mode,
                "mode_val" : mode_val,
                "group" : group}
        utils.debug("dict = " + str(dict))
        self.is_vector = (mode == vfield) or (mode == vexpr)
        utils.debug("is_vector = " + str(self.is_vector))
        self.is_raster = (mode == rclasses) or (mode == rresample)
        utils.debug("is_raster = " + str(self.is_raster))
        super().__init__(dict)
        
    def checkItem(self):
        pass
        
    def applyItem(self):
        if self.is_vector:
            self.applyVectorItem()
            #self.applyRasterItem()
        elif self.is_raster:
            self.applyRasterItem()
        else:
            user_error("Unkown format for file '" + str(self.dict["in_layer"]))
            
    def applyRasterItem(self):
        utils.debug("applyRasterItem")
        params.checkInit()
        in_layer_path = params.getOrigPath(self.dict["in_layer"])
        checkFileExists(in_layer_path)
        group_name = self.dict["group"]
        group_item = groups.getGroupByName(group_name)
        #tmp_path = group_item.getRasterTmpPath()
        out_path = group_item.getRasterPath()
        out_tmp_path = utils.mkTmpPath(out_path)
        crs = params.params.crs
        resolution = params.getResolution()
        extent_path = params.getExtentLayer()
        mode = self.dict["mode"]
        if mode == rclasses:
            resampling_mode = "near"
            #in_layer = loadRasterLayer(in_layer_path)
            in_layer = gdal.Open(in_layer_path)
            band1 = in_layer.GetRasterBand(1)
            data_array = band1.ReadAsArray()
            unique_vals = set(np.unique(data_array))
            utils.debug("Unique values init : " + str(unique_vals))
            in_nodata_val = int(band1.GetNoDataValue())
            utils.debug("in_nodata_val = " + str(in_nodata_val))
            unique_vals.remove(in_nodata_val)
            utils.debug("Unique values : " + str(unique_vals))
            reclass_dict = group_item.getReclassDict()
            applyReclassGdalFromDict(in_layer_path,out_tmp_path,reclass_dict)
            applyWarpGdal(out_tmp_path,out_path,resampling_mode,crs,
                          resolution,extent_path,
                          load_flag=True,to_byte=True)
        else:
            applyWarpGdal(in_layer_path,out_path,resampling_mode,crs,
                          resolution,extent_path,
                          load_flag=True,to_byte=False)
        
    # Selection is performed in 3 steps :
    #   1) creates group layer (group_vector.shp) if not existing with below fields :
    #       - 'Origin' : source layer name
    #       - 'Class' : class assigned to this selection
    #       - 'Code' : code assigned to this class
    #   2) select features
    #   3) add features to group layer
    def applyVectorItem(self):
        utils.debug("classModel = " + str(classes.classModel))
        in_layer_path = params.getOrigPath(self.dict["in_layer"])
        checkFileExists(in_layer_path)
        in_layer = loadVectorLayer(in_layer_path)
        mode = self.dict["mode"]
        mode_val = self.dict["mode_val"]
        # class_name = self.dict["class"]
        # class_item = classes.getClassByName(class_name)
        # if not class_item:
            # utils.user_error("No class named '" + class_name + "'")
        group_name = self.dict["group"]
        group_item = groups.getGroupByName(group_name)
        if not group_item:
            utils.user_error("No group named '" + group_name + "'")
        out_vector_layer_path = group_item.getVectorPath()
        if os.path.isfile(out_vector_layer_path):
            out_vector_layer = group_item.vectorLayer
        else:
            # group layer creation
            out_vector_layer = createLayerFromExisting(in_layer,group_name + "_vector",
                                                       geomType=None,crs=params.params.getCrsStr())
            group_item.vectorLayer = out_vector_layer
            orig_field = QgsField("Origin", QVariant.String)
            class_field = QgsField("Class", QVariant.String)
            code_field = QgsField("Code", QVariant.Int)
            out_vector_layer.dataProvider().addAttributes([orig_field,class_field,code_field])
            out_vector_layer.updateFields()        
        if (mode == vexpr) and mode_val:
            feats = in_layer.getFeatures(QgsFeatureRequest().setFilterExpression(mode_val))
        else:
            feats = in_layer.getFeatures(QgsFeatureRequest())
        pr = out_vector_layer.dataProvider()
        in_crs = in_layer.sourceCrs()
        out_crs = out_vector_layer.sourceCrs()
        utils.debug("in_crs : " + str(in_crs.description()))
        utils.debug("out_crs : " + str(out_crs.description()))
        if in_crs.authid() == out_crs.authid():
            transform_flag = False
        else:
            transform_flag = True
            transformator = QgsCoordinateTransform(in_crs,out_crs,QgsProject.instance())
        fields = out_vector_layer.fields()
        tmp_cpt = 0
        for f in feats:
            tmp_cpt += 1
            geom = f.geometry()
            if transform_flag:
                transf_res = geom.transform(transformator)#,QgsCoordinateTransform.ForwardTransform)
                if transf_res != QgsGeometry.Success:
                    utils.internal_error("Could not transform geometry : " + str(trasf_res))
            if mode == vfield:
                if mode_val not in f.fields().names():
                    utils.debug("fields = " + str(f.fields().names()))
                    utils.internal_error("No field named " + str(mode_val))
                class_name = group_name + "_" + str(f[mode_val])
            else:
                class_name = group_name
            class_item = classes.getClassByName(class_name)
            if not class_item:
                utils.internal_error("No class " + str(class_name) + " found")
            new_f = QgsFeature(fields)
            #utils.debug("new_fields = " + str(new_f.fields().names()))
            new_f.setGeometry(geom)
            new_f["Origin"] = in_layer.name()
            new_f["Class"] = class_name
            new_f["Code"] = class_item.dict["code"]
            res = pr.addFeature(new_f)
            if not res:
                internal_error("addFeature failed")
            out_vector_layer.updateExtents()
        utils.debug("length(feats) = " + str(tmp_cpt))
        group_item.vectorLayer = out_vector_layer
        if tmp_cpt == 0:
            warn("No entity selected from '" + str(self) + "'")
        group_item.saveVectorLayer()
        
        
class SelectionModel(DictModel):
    
    def __init__(self):
        super().__init__(self,selection_fields)
        
    @staticmethod
    def mkItemFromDict(dict):
        #checkFields(selection_fields,dict.keys())
        if "expr" in dict:
            mode_val = dict["expr"]
            if mode_val == "Raster":
                mode = rresample
            else:
                mode = vexpr
        else:
            checkFields(selection_fields,dict.keys())
            mode = dict["mode"]
            mode_val = dict["mode_val"]
        item = SelectionItem(dict["in_layer"],mode,mode_val,dict["group"])
        return item

    # Selections are performed group by group.
    # Group vector layers are then rasterized (group_vector.shp to group_raster.tif)
    def applyItems(self,indexes):
        utils.debug("applyItems " + str(indexes))
        params.checkInit()
        selectionsByGroup = {}
        progress_section = progress.ProgressSection("Selection",len(indexes))
        progress_section.start_section()
        for n in indexes:
            i = self.items[n]
            grp = i.dict["group"]
            if grp in selectionsByGroup:
                selectionsByGroup[grp].append(i)
            else:
                selectionsByGroup[grp] = [i]
        for g, selections in selectionsByGroup.items():
            grp_item = groups.getGroupByName(g)
            if not grp_item:
                utils.user_error("Group '" + g + "' does not exist")
            grp_vector_path = grp_item.getVectorPath()
            if os.path.isfile(grp_vector_path):
                removeFile(grp_vector_path)
            from_raster = False
            for s in selections:
                s.applyItem()
                progress_section.next_step()
                if s.is_raster:
                    from_raster = True
                    if len(selections) > 1:
                        utils.user_error("Several selections in group '" + g +"'")
            if not from_raster:
                grp_item.applyRasterizationItem()
        progress_section.end_section()
        
class SelectionConnector(AbstractConnector):

    def __init__(self,dlg):
        self.dlg = dlg
        selectionModel = SelectionModel()
        self.onlySelection = False
        super().__init__(selectionModel,self.dlg.selectionView,
                        self.dlg.selectionAdd,self.dlg.selectionRemove)
                        
    def initGui(self):
        #_translate = QtCore.QCoreApplication.translate
        self.activateGroupDisplay()
        self.dlg.selectionInLayerCombo.setFilters(QgsMapLayerProxyModel.All)
        #self.dlg.selectionResampleCombo.addItem(_translate("BioDispersalDialogBase","Plus proche voisin"))
        #self.dlg.selectionResampleCombo.addItem(_translate("BioDispersalDialogBase","Moyenne"))
        #self.dlg.selectionResampleCombo.addItem("Bilinéaire")
        #self.dlg.selectionResampleCombo.addItem("Cubique")
        
    def connectComponents(self):
        super().connectComponents()
        # In layer
        self.dlg.selectionLayerFormatVector.stateChanged.connect(self.switchVectorMode)
        self.dlg.selectionLayerFormatRaster.stateChanged.connect(self.switchRasterMode)
        self.dlg.selectionInLayerCombo.layerChanged.connect(self.setInLayerFromCombo)
        self.dlg.selectionInLayer.fileChanged.connect(self.setInLayer)
        # Selection mode
        self.dlg.fieldSelectionMode.stateChanged.connect(self.switchFieldMode)
        self.dlg.exprSelectionMode.stateChanged.connect(self.switchExprMode)
        self.dlg.selectionCreateClasses.stateChanged.connect(self.switchRClassMode)
        # Class
        # self.dlg.selectionClassCombo.setModel(classes.classModel)
        # self.dlg.selectionClassCombo.currentTextChanged.connect(self.setClass)
        self.dlg.classDisplay.stateChanged.connect(self.switchClassDisplay)
        # Group
        self.dlg.selectionGroupCombo.setModel(groups.groupsModel)
        self.dlg.groupDisplay.stateChanged.connect(self.switchGroupDisplay)
        # Selections
        #self.dlg.selectionAdd.clicked.connect(self.addItems)
        self.dlg.selectionUp.clicked.connect(self.upgradeItem)
        self.dlg.selectionDown.clicked.connect(self.downgradeItem)
        self.dlg.selectionRunSelectionMode.stateChanged.connect(self.switchOnlySelection)
        self.dlg.selectionRun.clicked.connect(self.applyItems)
        #
        header = self.dlg.selectionView.horizontalHeader()     
        self.activateVectorMode()
        self.activateFieldMode()
        #header.setSectionResizeMode(1, QHeaderView.Stretch)
        
    def applyItems(self):
        if self.onlySelection:
            indexes = list(set([i.row() for i in self.view.selectedIndexes()]))
        else:
            indexes = range(0,len(self.model.items))
        utils.debug(str(indexes))
        self.model.applyItems(indexes)
        
    def switchOnlySelection(self):
        new_val = not self.onlySelection
        utils.debug("setting onlySelection to " + str(new_val))
        self.onlySelection = new_val
        
    def setClass(self,text):
        cls_item = classes.getClassByName(text)
        self.dlg.selectionClassName.setText(cls_item.dict["name"])
        self.dlg.selectionClassDescr.setText(cls_item.dict["descr"])
        
    def setGroup(self,text):
        grp_item = groups.getGroupByName(text)
        self.dlg.selectionGroupName.setText(grp_item.dict["name"])
        self.dlg.selectionGroupDescr.setText(grp_item.dict["descr"])
                        
    def setInLayerFromCombo(self,layer):
        debug("setInLayerFromCombo")
        debug(str(layer.__class__.__name__))
        if layer:
            path=pathOfLayer(layer)
            self.dlg.selectionExpr.setLayer(layer)
            self.dlg.selectionField.setLayer(layer)
        else:
            warn("Could not load selection in layer")
        
    def setInLayer(self,path):
        debug("setInLayer " + path)
        #loaded_layer = loadLayer(path,loadProject=True)
        if self.dlg.selectionLayerFormatVector.isChecked():
            loaded_layer = loadVectorLayer(path,loadProject=True)
            self.dlg.selectionExpr.setLayer(loaded_layer)
            self.dlg.selectionField.setLayer(loaded_layer)
            debug("selectionField layer : " + str(self.dlg.selectionField.layer().name()))
            debug(str(self.dlg.selectionField.layer().fields().names()))
        else:
            loaded_layer = loadRasterLayer(path,loadProject=True)
        self.dlg.selectionInLayerCombo.setLayer(loaded_layer)
            
        
    def setInLayerField(self,path):
        debug("[setInLayerField]")
        layer = QgsVectorLayer(path, "test", "ogr")
        self.dlg.selectionField.setLayer(layer)
                
    def getOrCreateGroup(self):
        utils.debug("getOrCreateGroup")
        group = self.dlg.selectionGroupCombo.currentText()
        utils.debug("group = " + str(group))
        if not group:
            user_error("No group selected")
        group_item = groups.getGroupByName(group)
        utils.debug("grp_item = " + str(group_item))
        if not group_item:
            group_descr = self.dlg.selectionGroupDescr.text()
            in_layer = self.dlg.selectionInLayerCombo.currentLayer()
            if self.dlg.selectionLayerFormatVector.isChecked():
                in_geom = getLayerSimpleGeomStr(in_layer)
            else:
                in_geom = "Raster"
            utils.debug("test1")
            group_item = groups.GroupItem(group,group_descr,in_geom)
            utils.debug("test2")
            groups.groupsModel.addItem(group_item)
            groups.groupsModel.layoutChanged.emit()
        return group_item
        
        
    def getOrCreateClass(self):
        utils.debug("getOrCreateClass")
        cls = self.dlg.selectionGroupCombo.currentText()
        utils.debug("cls = " + str(cls))
        if not cls:
            user_error("No class selected")
        class_item = classes.getClassByName(cls)
        utils.debug("class_item = " + str(class_item))
        if not class_item:
            class_descr = ""
            class_item = classes.ClassItem(cls,class_descr,None)
            classes.classModel.addItem(class_item)
            classes.classModel.layoutChanged.emit()
        return class_item
        
    def getClassesFromVals(self,group,vals):
        res = []
        for v in vals:
            class_name = group + "_" + str(v)
            class_descr = "Class " + str(v) + " of group " + group
            res.append((class_name,class_descr))
        return res
        
    def getRasterVals(self,layer_path):
        utils.debug("getRasterVals " + str(layer_path))
        orig_path = params.getOrigPath(layer_path)
        utils.debug("orig_path =  " + str(orig_path))
        in_layer = gdal.Open(orig_path)
        band1 = in_layer.GetRasterBand(1)
        data_array = band1.ReadAsArray()
        unique_vals = set(np.unique(data_array))
        utils.debug("Unique values init : " + str(unique_vals))
        in_nodata_val = int(band1.GetNoDataValue())
        utils.debug("in_nodata_val = " + str(in_nodata_val))
        unique_vals.remove(in_nodata_val)
        utils.debug("Unique values : " + str(unique_vals))
        return unique_vals
        
    def getVectorVals(self,layer,field_name):
        field_values = set()
        for f in layer.getFeatures():
            field_values.add(f[field_name])
        return field_values
        
    def mkItem(self):
        in_layer = self.dlg.selectionInLayerCombo.currentLayer()
        if not in_layer:
            utils.user_error("No layer selected")
        in_layer_path = params.normalizePath(pathOfLayer(in_layer))
        expr = self.dlg.selectionExpr.expression()
        grp_item = self.getOrCreateGroup()
        grp_name = grp_item.dict["name"]
        grp_descr = grp_item.dict["descr"]
        if self.dlg.selectionLayerFormatVector.isChecked():
            in_geom = getLayerSimpleGeomStr(in_layer)
            grp_item.checkGeom(in_geom)
            if self.dlg.fieldSelectionMode.isChecked():
                mode = vfield
                mode_val = self.dlg.selectionField.currentField()
                utils.debug("mode_val = " + str(mode_val))
                if not mode_val:
                    utils.user_error("No field selected")
                vals = self.getVectorVals(in_layer,mode_val)
                class_names = self.getClassesFromVals(grp_name,vals)
            elif self.dlg.exprSelectionMode.isChecked():
                mode = vexpr
                mode_val = self.dlg.selectionExpr.expression()
                class_names = [(grp_name, grp_descr)]
            else:
                assert False
        elif self.dlg.selectionLayerFormatRaster.isChecked():
            in_geom = "Raster"
            if self.dlg.selectionCreateClasses.isChecked():
                mode = rclasses
                vals = self.getRasterVals(in_layer_path)
                class_names = self.getClassesFromVals(grp_name,vals)
            else:
                mode = rresample
                class_names = [(grp_name, grp_descr)]
            resample_idx = self.dlg.selectionResampleCombo.currentIndex()
            mode_val = resampling_modes[resample_idx]
        else:
            assert False
        utils.debug("class_names = " + str(class_names))
        for (class_name, class_descr) in class_names:
            class_item = classes.ClassItem(class_name,class_descr,None,grp_name)
            classes.classModel.addItem(class_item)
            classes.classModel.layoutChanged.emit()
        item = SelectionItem(in_layer_path,mode,mode_val,grp_name)
        return item
        
        
    # def mkItemFromRaster(self):
        # utils.debug("mkItemFromRaster")
        # in_layer = self.dlg.selectionInLayerCombo.currentLayer()
        # in_layer_path = params.normalizePath(pathOfLayer(in_layer))
        # utils.debug("in_layer_path = " + str(in_layer_path))
        # if self.dlg.selectionCreateClasses.isChecked():
            # mode = rclasses
        # else:
            # mode = rresample
        # utils.debug("mode = " + str(mode))
        # mode_val = self.dlg.selectionResampleCombo.currentText()
        # utils.debug("mode_val = " + str(mode_val))
        # grp_item = self.getOrCreateGroup()
        # utils.debug("grp_item = " + str(grp_item))
        # utils.debug("avant")
        # grp_name = grp_item.dict["name"]
        # utils.debug("apres")
        # utils.debug("grp = " + str(grp_name))
        # if mode == rclasses:
            # resampling_mode = "near"
            # in_layer = gdal.Open(in_layer_path)
            # band1 = in_layer.GetRasterBand(1)
            # data_array = band1.ReadAsArray()
            # unique_vals = set(np.unique(data_array))
            # utils.debug("Unique values init : " + str(unique_vals))
            # in_nodata_val = int(band1.GetNoDataValue())
            # utils.debug("in_nodata_val = " + str(in_nodata_val))
            # unique_vals.remove(in_nodata_val)
            # utils.debug("Unique values : " + str(unique_vals))
            # for v in unique_vals:
                # class_name = group_name + "_" + str(v)
                # class_descr = "Class " + str(fv) + " of group " + group
                # class_item = classes.ClassItem(class_name,class_descr,None)
                # classes.classModel.addItem(class_item)
                # classes.classModel.layoutChanged.emit()
        # item = SelectionItem(in_layer_path,mode,mode_val,grp_name)#,class_descr,group_descr)
        # items.append(item)
        # return item
        
        
    # def mkItemFromExpr(self):
        # in_layer = self.dlg.selectionInLayerCombo.currentLayer()
        # in_layer_path = params.normalizePath(pathOfLayer(in_layer))
        # in_geom = getLayerSimpleGeomStr(in_layer)
        # expr = self.dlg.selectionExpr.expression()
        # grp_item = self.getOrCreateGroup()
        # grp_item.checkGeom(in_geom)
        # grp_name = grp_item.dict["name"]
        # class_item = self.getOrCreateClass()
        # cls_name = class_item.dict["name"]
        # selection = SelectionItem(in_layer_path,vexpr,expr,cls_name,grp_name)
        # return selection
        
        
    # def mkItemsFromField(self):
        # in_layer = self.dlg.selectionInLayerCombo.currentLayer()
        # in_layer_path = params.normalizePath(pathOfLayer(in_layer))
        # in_geom = getLayerSimpleGeomStr(in_layer)
        # field_name = self.dlg.selectionField.currentField()
        # if not field_name:
            # user_error("No field selected")
        # grp_item = self.getOrCreateGroup()
        # grp_item.checkGeom(in_geom)
        # group = grp_item.dict["name"]
        # if not group:
            # user_error("No group selected")
        # field_values = set()
        # for f in in_layer.getFeatures():
            # field_values.add(f[field_name])
        # debug(str(field_values))
        # items = []
        # for fv in field_values:
            # class_name = group + "_" + str(fv)
            # class_descr = "Class " + str(fv) + " of group " + group
            # class_item = classes.ClassItem(class_name,class_descr,None)
            # classes.classModel.addItem(class_item)
            # classes.classModel.layoutChanged.emit()
            # expr = "\"" + field_name + "\" = '" + str(fv) + "'"
            # item = SelectionItem(in_layer_path,vfield,expr,class_name,group)#,class_descr,group_descr)
            # items.append(item)
        # return items
        
    # def addItems(self):
        # debug("[addItemsFromField]")
        # if self.dlg.selectionLayerFormatVector.isChecked():
            # if self.dlg.fieldSelectionMode.isChecked():
                # items = self.mkItemsFromField()
            # elif self.dlg.exprSelectionMode.isChecked():
                # items = [self.mkItemFromExpr()]
            # else:
                # assert False
        # elif self.dlg.selectionLayerFormatRaster.isChecked():
            # items = [self.mkItemFromRaster()]
            # utils.debug("nb items = " + str(len(items)))
        # else:
            # assert False
        # for item in items:
            # self.model.addItem(item)
            # self.model.layoutChanged.emit()
            
    # Vector / raster modes
    
    def switchVectorMode(self,checked):
        if checked:
            self.activateVectorMode()
        else:
            self.activateRasterMode()
            
    def switchRasterMode(self,checked):
        if checked:
            self.activateRasterMode()
        else:
            self.activateVectorMode()
        
    def activateVectorMode(self):
        utils.debug("activateVectorMode")
        self.dlg.selectionLayerFormatRaster.setCheckState(0)
        self.dlg.selectionLayerFormatVector.setCheckState(2)
        self.dlg.selectionInLayerCombo.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.dlg.selectionInLayer.setFilter(getVectorFilters())
        self.dlg.stackSelectionMode.setCurrentWidget(self.dlg.stackSelectionModeVect)
        self.activateExprMode()
            
    def activateRasterMode(self):
        utils.debug("activateRasterMode")
        self.dlg.selectionLayerFormatVector.setCheckState(0)
        self.dlg.selectionLayerFormatRaster.setCheckState(2)
        self.dlg.selectionInLayerCombo.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.dlg.selectionInLayer.setFilter(getRasterFilters())
        self.dlg.stackSelectionMode.setCurrentWidget(self.dlg.stackSelectionModeRaster)
        self.dlg.stackSelectionExprField.setCurrentWidget(self.dlg.stackSelectionResampling)
        
            
    # Field / expression modes
            
    def switchFieldMode(self,checked):
        if checked:
            self.activateFieldMode()
        else:
            self.activateExprMode()
            
    def switchExprMode(self,checked):
        if checked:
            self.activateExprMode()
        else:
            self.activateFieldMode()
        
    def activateExprMode(self):
        utils.debug("activateExprMode")
        self.dlg.fieldSelectionMode.setCheckState(0)
        self.dlg.exprSelectionMode.setCheckState(2)
        self.dlg.stackSelectionExprField.setCurrentWidget(self.dlg.stackSelectionExpr)
        
    def activateFieldMode(self):
        utils.debug("activateFieldMode")
        self.dlg.exprSelectionMode.setCheckState(0)
        self.dlg.fieldSelectionMode.setCheckState(2)
        self.dlg.stackSelectionExprField.setCurrentWidget(self.dlg.stackSelectionField)
        
    # Class / Resample modes
    
    def switchRClassMode(self,checked):
        if checked:
            self.activateRClassMode()
        else:
            self.activateRResampleMode()
        
    def activateRClassMode(self):
        utils.debug("activateRClassMode")
        self.dlg.selectionResampleCombo.setCurrentIndex(0)
        self.dlg.selectionResampleCombo.setDisabled(True)
        
    def activateRResampleMode(self):
        utils.debug("activateRResampleMode")
        self.dlg.selectionResampleCombo.setEnabled(True)
        
        
    # Groups / class display
        
    def switchGroupDisplay(self,checked):
        if checked:
            self.activateGroupDisplay()
        else:
            self.activateClassDisplay()
            
    def switchClassDisplay(self,checked):
        if checked:
            self.activateClassDisplay()
        else:
            self.activateGroupDisplay()
            
    def activateGroupDisplay(self):
        self.dlg.classDisplay.setCheckState(0)
        self.dlg.groupDisplay.setCheckState(2)
        self.dlg.stackGroupClass.setCurrentWidget(self.dlg.stackGroup)
        # self.dlg.classFrame.hide()
        # self.dlg.groupFrame.show()
        
    def activateClassDisplay(self):
        self.dlg.groupDisplay.setCheckState(0)
        self.dlg.classDisplay.setCheckState(2)
        self.dlg.stackGroupClass.setCurrentWidget(self.dlg.stackClass)
        # self.dlg.groupFrame.hide()
        # self.dlg.classFrame.show()
        # self.dlg.classView.show()
    
