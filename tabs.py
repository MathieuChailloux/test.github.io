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

import utils
#import helps
from PyQt5.QtCore import QUrl, QFile, QIODevice, QTextStream
from PyQt5.QtGui import QTextDocument

class TabItem:

    def __init__(self,idx,name,helpFile):
        self.idx = idx
        self.name = name
        self.descr = "TODO"
        self.helpFile = os.path.join("help",helpFile + ".html")
        
    def setDescr(descr):
        self.descr = descr
        
paramsTabItem = TabItem(0,"Paramètres","paramsHelp")
stTabItem = TabItem(1,"Sous-trames","stHelp")
selectionTabItem = TabItem(2,"Sélection","selectionHelp")
fusionTabItem = TabItem(3,"Fusion","fusionHelp")
frictionTabItem = TabItem(4,"Friction","frictionHelp")
pondTabItem = TabItem(5,"Pondération","ponderationHelp")
dispersionTabItem = TabItem(6,"Dispersion","dispersionHelp")
logTabItem = TabItem(7,"Journal","logHelp")
        
class TabConnector:
    
    def __init__(self,dlg):
        self.tabs = [paramsTabItem,
                     stTabItem,
                     selectionTabItem,
                     fusionTabItem,
                     frictionTabItem,
                     pondTabItem,
                     dispersionTabItem,
                     logTabItem]
        self.dlg = dlg
        
    def initGui(self):
        self.dlg.textShortHelp.setOpenLinks(True)
        self.loadNTab(0)
        
    def loadNTab(self,n):
        utils.debug("[loadNTab] " + str(n))
        nb_tabs = len(self.tabs)
        if n >= nb_tabs:
            utils.internal_error("[loadNTab] loading " + str(n) + " tab but nb_tabs = " + str(nb_tabs))
        else:
            tabItem = self.tabs[n]
            curr_fname = os.path.dirname(__file__)
            utils.debug("curr_fname = " + str(curr_fname))
            fname = os.path.join(curr_fname,tabItem.helpFile)
            utils.debug("fname = " + str(fname))
            with open(fname) as f:
                msg = f.read()
            self.dlg.textShortHelp.setHtml(msg)
            #utils.debug("source : " + str(self.dlg.textShortHelp.source()))

            
    def connectComponents(self):
        self.dlg.mTabWidget.currentChanged.connect(self.loadNTab)
            